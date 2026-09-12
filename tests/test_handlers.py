import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, CallbackQuery, Chat, User
from app.handlers import common, containers, messages

def make_mock_message(text: str = "/start", user_id: int = 12345):
    msg = AsyncMock(spec=Message)
    msg.text = text
    msg.chat = Chat(id=1001, type="private")
    msg.from_user = User(id=user_id, is_bot=False, first_name="Admin")
    msg.message_id = 42
    msg.answer = AsyncMock()
    return msg

def make_mock_callback(data: str, user_id: int = 12345):
    cb = AsyncMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = User(id=user_id, is_bot=False, first_name="Admin")
    cb.message = AsyncMock(spec=Message)
    cb.message.chat = Chat(id=1001, type="private")
    cb.message.message_id = 42
    cb.message.edit_text = AsyncMock()
    cb.message.edit_reply_markup = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.message.answer_document = AsyncMock()
    cb.answer = AsyncMock()
    return cb

@pytest.mark.asyncio
async def test_cmd_start(temp_db, monkeypatch):
    monkeypatch.setattr("app.handlers.common.db", temp_db)
    msg = make_mock_message("/start")
    
    await common.cmd_start(msg)
    msg.answer.assert_awaited_once()
    assert "Добро пожаловать в NexusControl" in msg.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_help():
    msg = make_mock_message("/help")
    await common.cmd_help(msg)
    msg.answer.assert_awaited_once()
    assert "Справка по NexusControl" in msg.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_refresh_containers_list(temp_db, monkeypatch, mock_docker_container):
    monkeypatch.setattr("app.handlers.containers.db", temp_db)
    
    async def fake_list():
        return [mock_docker_container]

    monkeypatch.setattr("app.handlers.containers.docker_service.get_containers_list", fake_list)

    cb = make_mock_callback("refresh_list")
    await containers.refresh_containers_list(cb)

    cb.message.edit_text.assert_awaited_once()
    assert "Выберите контейнер" in cb.message.edit_text.call_args[0][0]
    cb.answer.assert_awaited_once()

@pytest.mark.asyncio
async def test_manage_container(temp_db, monkeypatch, mock_docker_container):
    monkeypatch.setattr("app.handlers.containers.db", temp_db)

    async def fake_list():
        return [mock_docker_container]

    monkeypatch.setattr("app.handlers.containers.docker_service.get_containers_list", fake_list)

    cb = make_mock_callback("manage:web-service-1234567890ab")
    await containers.manage_container(cb)

    cb.message.edit_text.assert_awaited_once()
    assert "Управление контейнером" in cb.message.edit_text.call_args[0][0]

@pytest.mark.asyncio
async def test_action_container(temp_db, monkeypatch, mock_docker_container):
    monkeypatch.setattr("app.handlers.containers.db", temp_db)

    async def fake_control(name, action):
        return True, "OK"

    async def fake_list():
        return [mock_docker_container]

    monkeypatch.setattr("app.handlers.containers.docker_service.control_container", fake_control)
    monkeypatch.setattr("app.handlers.containers.docker_service.get_containers_list", fake_list)

    # Тестируем остановку: должна записать intentional_stop
    cb = make_mock_callback("action:stop:web-service-1234567890ab")
    await containers.action_container(cb)

    assert await temp_db.is_intentional_stop("web-service-1234567890ab") is True
    assert cb.message.edit_text.await_count == 2
    cb.answer.assert_awaited_once()

@pytest.mark.asyncio
async def test_logs_handlers(monkeypatch):
    async def fake_logs(name, tail=100):
        return "Log output line 1\nLog output line 2"

    monkeypatch.setattr("app.handlers.containers.docker_service.get_logs", fake_logs)

    # 1. Меню логов
    cb_menu = make_mock_callback("logs_menu:web")
    await containers.logs_menu(cb_menu)
    assert "Логи контейнера" in cb_menu.message.edit_text.call_args[0][0]

    # 2. Получение текста логов
    cb_logs = make_mock_callback("get_logs:web:50")
    await containers.get_logs_text(cb_logs)
    cb_logs.message.answer.assert_awaited_once()
    assert "Log output line 1" in cb_logs.message.answer.call_args[0][0]

    # 3. Скачивание файлом
    cb_file = make_mock_callback("get_logs_file:web")
    await containers.get_logs_file(cb_file)
    cb_file.message.answer_document.assert_awaited_once()

@pytest.mark.asyncio
async def test_monitoring_start_and_stop(temp_db, monkeypatch):
    monkeypatch.setattr("app.handlers.containers.db", temp_db)

    async def fake_stats(name):
        return "Stats text for container"

    monkeypatch.setattr("app.handlers.containers.docker_service.get_container_stats", fake_stats)

    # Старт мониторинга
    cb_start = make_mock_callback("monitor_c:web")
    await containers.start_container_monitor(cb_start)
    assert "Stats text for container" in cb_start.message.edit_text.call_args[0][0]

    monitors = await temp_db.get_all_monitors()
    assert len(monitors) == 1
    assert monitors[0][2] == "web"

    # Стоп мониторинга
    cb_stop = make_mock_callback("stop_monitoring")
    await containers.stop_monitoring_action(cb_stop)
    assert "Обновление метрик остановлено" in cb_stop.message.edit_text.call_args[0][0]

    monitors_after = await temp_db.get_all_monitors()
    assert len(monitors_after) == 0
