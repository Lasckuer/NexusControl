import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.exceptions import TelegramBadRequest
from app.handlers.scheduler import metrics_refresher, container_crash_monitor, system_resource_monitor, alert_state

@pytest.mark.asyncio
async def test_metrics_refresher_message_not_modified(temp_db, monkeypatch):
    """
    Проверяем исправление критического бага:
    TelegramBadRequest('message is not modified') НЕ должен удалять монитор из базы!
    """
    monkeypatch.setattr("app.handlers.scheduler.db", temp_db)

    await temp_db.save_monitor(chat_id=100, message_id=200, container_name="web", last_text="old_text")

    bot = AsyncMock()
    # Эмулируем ошибку Telegram: сообщение не изменилось
    bot.edit_message_text.side_effect = TelegramBadRequest(
        method="editMessageText",
        message="Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message"
    )

    async def fake_get_stats(name):
        return "new_text"

    monkeypatch.setattr("app.handlers.scheduler.docker_service.get_container_stats", fake_get_stats)

    # Запускаем одну итерацию metrics_refresher через отмену задачи
    task = asyncio.create_task(metrics_refresher(bot, interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # Монитор ДОЛЖЕН остаться в базе данных!
    monitors = await temp_db.get_all_monitors()
    assert len(monitors) == 1
    assert monitors[0][0] == 100

@pytest.mark.asyncio
async def test_metrics_refresher_message_deleted(temp_db, monkeypatch):
    """
    Если сообщение было удалено пользователем в Telegram (message to edit not found),
    монитор должен быть корректно удален из базы данных.
    """
    monkeypatch.setattr("app.handlers.scheduler.db", temp_db)

    await temp_db.save_monitor(chat_id=100, message_id=200, container_name="web", last_text="old_text")

    bot = AsyncMock()
    bot.edit_message_text.side_effect = TelegramBadRequest(
        method="editMessageText",
        message="Bad Request: message to edit not found"
    )

    async def fake_get_stats(name):
        return "new_text"

    monkeypatch.setattr("app.handlers.scheduler.docker_service.get_container_stats", fake_get_stats)

    task = asyncio.create_task(metrics_refresher(bot, interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # Монитор должен быть удален
    monitors = await temp_db.get_all_monitors()
    assert len(monitors) == 0

@pytest.mark.asyncio
async def test_container_crash_monitor_unexpected_crash(temp_db, monkeypatch):
    """Проверка алерта при неожиданном падении контейнера"""
    monkeypatch.setattr("app.handlers.scheduler.db", temp_db)
    monkeypatch.setattr("app.handlers.scheduler.config.admin_ids", {777})

    bot = AsyncMock()
    
    # 1-й цикл: контейнер запущен
    c1 = MagicMock(name="db_service", status="running")
    c1.name = "db_service"
    
    # 2-й цикл: контейнер упал
    c2 = MagicMock(name="db_service", status="exited")
    c2.name = "db_service"

    container_states = [[c1], [c2]]

    async def mock_list():
        if container_states:
            return container_states.pop(0)
        return [c2]

    monkeypatch.setattr("app.handlers.scheduler.docker_service.get_containers_list", mock_list)

    task = asyncio.create_task(container_crash_monitor(bot, interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # Должен быть отправлен алерт о падении
    bot.send_message.assert_awaited()
    assert "ПАДЕНИЕ КОНТЕЙНЕРА" in bot.send_message.call_args[1]["text"]

@pytest.mark.asyncio
async def test_container_crash_monitor_intentional_stop(temp_db, monkeypatch):
    """Проверка подавления алерта, если остановка была штатной через бота"""
    monkeypatch.setattr("app.handlers.scheduler.db", temp_db)
    monkeypatch.setattr("app.handlers.scheduler.config.admin_ids", {777})

    # Помечаем контейнер как намеренно остановленный
    await temp_db.add_intentional_stop("db_service")

    bot = AsyncMock()
    
    c1 = MagicMock(name="db_service", status="running")
    c1.name = "db_service"
    c2 = MagicMock(name="db_service", status="exited")
    c2.name = "db_service"

    container_states = [[c1], [c2]]

    async def mock_list():
        if container_states:
            return container_states.pop(0)
        return [c2]

    monkeypatch.setattr("app.handlers.scheduler.docker_service.get_containers_list", mock_list)

    task = asyncio.create_task(container_crash_monitor(bot, interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # Алерт НЕ должен быть отправлен!
    bot.send_message.assert_not_awaited()

@pytest.mark.asyncio
async def test_system_resource_monitor_alert_and_recovery(monkeypatch):
    """Проверка срабатывания алерта при высокой нагрузке CPU и восстановления с гистерезисом"""
    monkeypatch.setattr("app.handlers.scheduler.config.admin_ids", {777})
    monkeypatch.setattr("app.handlers.scheduler.config.cpu_threshold", 90.0)
    monkeypatch.setattr("app.handlers.scheduler.config.ram_threshold", 95.0)
    monkeypatch.setattr("app.handlers.scheduler.config.disk_threshold", 95.0)
    monkeypatch.setattr("app.handlers.scheduler.config.alert_cooldown", 0)

    # Сбрасываем alert_state
    alert_state["cpu"] = {"is_high": False, "last_alert": 0}
    alert_state["ram"] = {"is_high": False, "last_alert": 0}
    alert_state["disk"] = {"is_high": False, "last_alert": 0}

    bot = AsyncMock()

    # Сначала нагрузка 98% (критическая)
    stats_high = {"cpu_percent": 98.0, "ram_percent": 40.0, "disk_percent": 50.0}
    # Затем нагрузка 75% (ниже порога с гистерезисом 90 - 10 = 80%)
    stats_normal = {"cpu_percent": 75.0, "ram_percent": 40.0, "disk_percent": 50.0}

    stats_sequence = [stats_high, stats_normal]

    async def mock_get_stats():
        if stats_sequence:
            return stats_sequence.pop(0)
        return stats_normal

    monkeypatch.setattr("app.handlers.scheduler.system_service.get_stats_data", mock_get_stats)

    task = asyncio.create_task(system_resource_monitor(bot, interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # Должно быть 2 вызова: 1) Критическая нагрузка CPU, 2) Нормализация
    assert bot.send_message.await_count == 2
    assert "КРИТИЧЕСКАЯ НАГРУЗКА CPU" in bot.send_message.await_args_list[0][0][1]
    assert "нормализовалась" in bot.send_message.await_args_list[1][0][1]
