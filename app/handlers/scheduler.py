import asyncio
import time
import os
import psutil
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramForbiddenError
from app.database.db import db
from app.services.docker_service import docker_service
from app.services.system_service import system_service
from app.keyboards.reply import get_stop_monitor_keyboard
from app.utils.aliases import prettify_name
from app.utils.formatters import safe_html
from app.config import config
from logger import logger

async def metrics_refresher(bot: Bot, interval: int = 4):
    """
    Фоновый процесс автообновления сообщений мониторинга в чатах.
    Оптимизирован для предотвращения лишних запросов к Telegram API
    и корректной обработки ошибок без сброса монитора.
    """
    logger.info("Запущен сервис обновления метрик (metrics_refresher)")
    while True:
        try:
            await asyncio.sleep(interval)
            monitors = await db.get_all_monitors()
            
            for chat_id, message_id, container_name, last_text in monitors:
                try:
                    if container_name:
                        new_text = await docker_service.get_container_stats(container_name)
                        kb = get_stop_monitor_keyboard(container_name=container_name)
                    else:
                        new_text = await system_service.get_server_stats_message()
                        kb = get_stop_monitor_keyboard()

                    # Проверяем, изменился ли текст, чтобы не дергать Telegram API понапрасну
                    if new_text == last_text:
                        continue

                    await bot.edit_message_text(
                        text=new_text,
                        chat_id=chat_id,
                        message_id=message_id,
                        parse_mode="HTML",
                        reply_markup=kb
                    )
                    await db.update_monitor_text(chat_id, new_text)

                except TelegramRetryAfter as e:
                    logger.warning(f"Telegram flood limit: сон на {e.retry_after} сек.")
                    await asyncio.sleep(e.retry_after)
                except TelegramBadRequest as e:
                    err_msg = str(e).lower()
                    if "message is not modified" in err_msg:
                        # Текст не изменился, просто обновляем кэш и продолжаем работу
                        await db.update_monitor_text(chat_id, new_text)
                    elif "message to edit not found" in err_msg or "message can't be edited" in err_msg:
                        logger.info(f"Сообщение {message_id} в чате {chat_id} удалено. Удаляем монитор.")
                        await db.delete_monitor(chat_id)
                    else:
                        logger.warning(f"Ошибка редактирования сообщения в чате {chat_id}: {e}")
                except TelegramForbiddenError:
                    logger.info(f"Бот заблокирован пользователем {chat_id}. Удаляем монитор.")
                    await db.delete_monitor(chat_id)
                except Exception as e:
                    logger.error(f"Непредвиденная ошибка обновления монитора в чате {chat_id}: {e}")

        except asyncio.CancelledError:
            logger.info("Сервис metrics_refresher остановлен.")
            break
        except Exception as e:
            logger.error(f"Ошибка в основном цикле metrics_refresher: {e}")
            await asyncio.sleep(interval)


async def container_crash_monitor(bot: Bot, interval: int = 5):
    """
    Мониторинг аварийных падений контейнеров.
    Игнорирует намеренные остановки, выполненные администратором через интерфейс бота.
    """
    logger.info("Запущен сервис отслеживания падений контейнеров (container_crash_monitor)")
    known_states: dict[str, str] = {}

    while True:
        try:
            await asyncio.sleep(interval)
            containers = await docker_service.get_containers_list()
            current_states = {c.name: c.status for c in containers}

            if not known_states:
                known_states = current_states
                continue

            for name, status in current_states.items():
                prev_status = known_states.get(name)

                # Контейнер упал или неожиданно завершился
                if prev_status == "running" and status in ["exited", "dead"]:
                    # Проверяем, не была ли остановка инициирована администратором
                    if await db.is_intentional_stop(name):
                        logger.info(f"Контейнер {name} был штатно остановлен администратором. Алерт пропущен.")
                        continue

                    nice_name = prettify_name(name)
                    alert_msg = (
                        f"🚨 <b>ВНИМАНИЕ! ПАДЕНИЕ КОНТЕЙНЕРА!</b>\n\n"
                        f"📦 <b>Контейнер:</b> {safe_html(nice_name)}\n"
                        f"🏷 <b>Системное имя:</b> <code>{safe_html(name)}</code>\n"
                        f"Статус: <b>{status.upper()}</b>"
                    )

                    for admin_id in config.admin_ids:
                        try:
                            await bot.send_message(chat_id=admin_id, text=alert_msg, parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Не удалось отправить уведомление о падении админу {admin_id}: {e}")

            known_states = current_states

        except asyncio.CancelledError:
            logger.info("Сервис container_crash_monitor остановлен.")
            break
        except Exception as e:
            logger.error(f"Ошибка мониторинга падений: {e}")
            await asyncio.sleep(interval)


alert_state = {
    "cpu": {"is_high": False, "last_alert": 0},
    "ram": {"is_high": False, "last_alert": 0},
    "disk": {"is_high": False, "last_alert": 0},
}

async def system_resource_monitor(bot: Bot, interval: int = 30):
    """
    Фоновый мониторинг аппаратных ресурсов сервера (CPU, RAM, Диск).
    Оповещает при превышении пороговых значений и при их нормализации.
    """
    logger.info("Запущен сервис мониторинга аппаратных ресурсов (system_resource_monitor)")
    while True:
        try:
            await asyncio.sleep(interval)
            current_time = time.time()

            stats = await system_service.get_stats_data()
            cpu = stats["cpu_percent"]
            ram = stats["ram_percent"]
            disk = stats["disk_percent"]

            # 1. Проверка CPU
            if cpu > config.cpu_threshold:
                if not alert_state["cpu"]["is_high"] or (current_time - alert_state["cpu"]["last_alert"] > config.alert_cooldown):
                    msg = f"🔥 <b>КРИТИЧЕСКАЯ НАГРУЗКА CPU!</b>\nТекущее значение: <code>{cpu}%</code> (порог: {config.cpu_threshold}%)"
                    for admin_id in config.admin_ids:
                        try:
                            await bot.send_message(admin_id, msg, parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Ошибка отправки алерта CPU админу {admin_id}: {e}")
                    alert_state["cpu"]["is_high"] = True
                    alert_state["cpu"]["last_alert"] = current_time
            elif alert_state["cpu"]["is_high"] and cpu < (config.cpu_threshold - 10.0):
                msg = f"✅ <b>Нагрузка CPU нормализовалась.</b>\nТекущее значение: <code>{cpu}%</code>"
                for admin_id in config.admin_ids:
                    try:
                        await bot.send_message(admin_id, msg, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления CPU админу {admin_id}: {e}")
                alert_state["cpu"]["is_high"] = False

            # 2. Проверка RAM
            if ram > config.ram_threshold:
                if not alert_state["ram"]["is_high"] or (current_time - alert_state["ram"]["last_alert"] > config.alert_cooldown):
                    msg = f"🧠 <b>НЕХВАТКА ОПЕРАТИВНОЙ ПАМЯТИ!</b>\nИспользуется: <code>{ram}%</code> (порог: {config.ram_threshold}%)"
                    for admin_id in config.admin_ids:
                        try:
                            await bot.send_message(admin_id, msg, parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Ошибка отправки алерта RAM админу {admin_id}: {e}")
                    alert_state["ram"]["is_high"] = True
                    alert_state["ram"]["last_alert"] = current_time
            elif alert_state["ram"]["is_high"] and ram < (config.ram_threshold - 5.0):
                msg = f"✅ <b>Оперативная память освободилась.</b>\nИспользуется: <code>{ram}%</code>"
                for admin_id in config.admin_ids:
                    try:
                        await bot.send_message(admin_id, msg, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления RAM админу {admin_id}: {e}")
                alert_state["ram"]["is_high"] = False

            # 3. Проверка Диска
            if disk > config.disk_threshold:
                if not alert_state["disk"]["is_high"] or (current_time - alert_state["disk"]["last_alert"] > config.alert_cooldown):
                    msg = (
                        f"💾 <b>ЗАКАНЧИВАЕТСЯ МЕСТО НА ДИСКЕ!</b>\n"
                        f"Занято: <code>{disk}%</code> (порог: {config.disk_threshold}%)\n"
                        f"Рекомендуется очистить Docker (команда /prune)!"
                    )
                    for admin_id in config.admin_ids:
                        try:
                            await bot.send_message(admin_id, msg, parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Ошибка отправки алерта Disk админу {admin_id}: {e}")
                    alert_state["disk"]["is_high"] = True
                    alert_state["disk"]["last_alert"] = current_time
            elif alert_state["disk"]["is_high"] and disk < (config.disk_threshold - 2.0):
                msg = f"✅ <b>Место на диске освобождено.</b>\nЗанято: <code>{disk}%</code>"
                for admin_id in config.admin_ids:
                    try:
                        await bot.send_message(admin_id, msg, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления Disk админу {admin_id}: {e}")
                alert_state["disk"]["is_high"] = False

        except asyncio.CancelledError:
            logger.info("Сервис system_resource_monitor остановлен.")
            break
        except Exception as e:
            logger.error(f"Ошибка мониторинга ресурсов: {e}")
            await asyncio.sleep(interval)