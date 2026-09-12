import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, CallbackQuery, User
from app.middlewares.auth import AdminAuthMiddleware
from app.config import Config

@pytest.mark.asyncio
async def test_admin_middleware_allowed(monkeypatch):
    monkeypatch.setattr("app.middlewares.auth.config.admin_ids", {12345})

    middleware = AdminAuthMiddleware()
    handler = AsyncMock(return_value="OK")

    user = User(id=12345, is_bot=False, first_name="Admin", username="admin_user")
    event = MagicMock(spec=Message)
    data = {"event_from_user": user}

    result = await middleware(handler, event, data)
    assert result == "OK"
    handler.assert_awaited_once()

@pytest.mark.asyncio
async def test_admin_middleware_blocked_message(monkeypatch):
    monkeypatch.setattr("app.middlewares.auth.config.admin_ids", {12345})

    middleware = AdminAuthMiddleware()
    handler = AsyncMock()

    user = User(id=99999, is_bot=False, first_name="Hacker", username="bad_actor")
    event = MagicMock(spec=Message)
    event.answer = AsyncMock()
    data = {"event_from_user": user}

    result = await middleware(handler, event, data)
    assert result is None
    handler.assert_not_awaited()
    event.answer.assert_awaited_once()
    assert "Доступ запрещен" in event.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_admin_middleware_blocked_callback(monkeypatch):
    monkeypatch.setattr("app.middlewares.auth.config.admin_ids", {12345})

    middleware = AdminAuthMiddleware()
    handler = AsyncMock()

    user = User(id=99999, is_bot=False, first_name="Hacker", username="bad_actor")
    event = MagicMock(spec=CallbackQuery)
    event.answer = AsyncMock()
    data = {"event_from_user": user}

    result = await middleware(handler, event, data)
    assert result is None
    handler.assert_not_awaited()
    event.answer.assert_awaited_once_with("⛔ Доступ запрещен: вы не администратор.", show_alert=True)
