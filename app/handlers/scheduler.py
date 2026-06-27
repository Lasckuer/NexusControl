import asyncio
import psutil
import time
from aiogram import Bot
from app.database.db import db
from app.services.docker_service import docker_service
from app.keyboards.reply import get_stop_monitor_keyboard, prettify_name
from logger import logger

async def metrics_refresher(bot: Bot, interval: int = 4):
    while True:
        await asyncio.sleep(interval)
        monitors = db.get_all_monitors()
        for chat_id, message_id, container_name in monitors:
            try:
                if container_name:
                    text = docker_service.get_container_stats(container_name)
                else:
                    text = docker_service.get_server_stats()
                
                await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode="Markdown",
                    reply_markup=get_stop_monitor_keyboard()
                )
            except Exception as e:
                logger.error(f"Ошибка обновления сообщения {message_id} в чате {chat_id}: {e}")
                db.delete_monitor(chat_id)

async def container_crash_monitor(bot: Bot, admin_id: int, interval: int = 5):
    known_states = {}
    while True:
        try:
            containers = docker_service.get_containers_list()
            current_states = {c.name: c.status for c in containers}

            if not known_states:
                known_states = current_states
                await asyncio.sleep(interval)
                continue

            for name, status in current_states.items():
                prev_status = known_states.get(name)
                
                if prev_status == 'running' and status in ['exited', 'dead']:
                    nice_name = prettify_name(name)
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"⚠️ **Внимание!** Контейнер **{nice_name}** упал!\nОригинальное имя: `{name}`",
                        parse_mode="Markdown"
                    )

            known_states = current_states
        except Exception as e:
            logger.error(f"Ошибка мониторинга падений: {e}")
        
        await asyncio.sleep(interval)
        
alert_state = {
    "cpu": {"is_high": False, "last_alert": 0},
    "ram": {"is_high": False, "last_alert": 0},
    "disk": {"is_high": False, "last_alert": 0},
}

THRESHOLD_CPU = 90.0
THRESHOLD_RAM = 90.0
THRESHOLD_DISK = 95.0

REPEAT_ALERT_COOLDOWN = 3600 

async def system_resource_monitor(bot: Bot, admin_id: int, interval: int = 30):
    """Фоновый мониторинг железа сервера"""
    while True:
        try:
            current_time = time.time()
            
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            if cpu > THRESHOLD_CPU:
                if not alert_state["cpu"]["is_high"] or (current_time - alert_state["cpu"]["last_alert"] > REPEAT_ALERT_COOLDOWN):
                    await bot.send_message(admin_id, f"🔥 **КРИТИЧЕСКАЯ НАГРУЗКА CPU!**\nТекущее значение: `{cpu}%`", parse_mode="Markdown")
                    alert_state["cpu"]["is_high"] = True
                    alert_state["cpu"]["last_alert"] = current_time
            elif alert_state["cpu"]["is_high"] and cpu < (THRESHOLD_CPU - 10): # Гистерезис 10%, чтобы не моргало
                await bot.send_message(admin_id, f"✅ **Нагрузка CPU нормализовалась.**\nТекущее значение: `{cpu}%`", parse_mode="Markdown")
                alert_state["cpu"]["is_high"] = False

            if ram > THRESHOLD_RAM:
                if not alert_state["ram"]["is_high"] or (current_time - alert_state["ram"]["last_alert"] > REPEAT_ALERT_COOLDOWN):
                    await bot.send_message(admin_id, f"🧠 **НЕХВАТКА ОПЕРАТИВНОЙ ПАМЯТИ!**\nИспользуется: `{ram}%`", parse_mode="Markdown")
                    alert_state["ram"]["is_high"] = True
                    alert_state["ram"]["last_alert"] = current_time
            elif alert_state["ram"]["is_high"] and ram < (THRESHOLD_RAM - 5):
                await bot.send_message(admin_id, f"✅ **Оперативная память освободилась.**\nИспользуется: `{ram}%`", parse_mode="Markdown")
                alert_state["ram"]["is_high"] = False

            if disk > THRESHOLD_DISK:
                if not alert_state["disk"]["is_high"] or (current_time - alert_state["disk"]["last_alert"] > REPEAT_ALERT_COOLDOWN):
                    await bot.send_message(admin_id, f"💾 **ЗАКАНЧИВАЕТСЯ МЕСТО НА ДИСКЕ!**\nЗанято: `{disk}%`\nСрочно используйте очистку Docker!", parse_mode="Markdown")
                    alert_state["disk"]["is_high"] = True
                    alert_state["disk"]["last_alert"] = current_time
            elif alert_state["disk"]["is_high"] and disk < (THRESHOLD_DISK - 2):
                await bot.send_message(admin_id, f"✅ **Место на диске освобождено.**\nЗанято: `{disk}%`", parse_mode="Markdown")
                alert_state["disk"]["is_high"] = False

        except Exception as e:
            logger.error(f"Ошибка мониторинга железа: {e}")
        
        await asyncio.sleep(interval)