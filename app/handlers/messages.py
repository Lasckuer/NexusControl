import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from app.keyboards.reply import get_main_keyboard, get_containers_keyboard
from app.services.docker_service import docker_service
from app.database.db import db

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

router = Router()

@router.message(CommandStart(), F.from_user.id == ADMIN_ID)
async def cmd_start(message: Message):
    db.delete_monitor(message.chat.id)
    await message.answer("👋 Добро пожаловать в NexusControl! Система управления сервером готова.", reply_markup=get_main_keyboard())

@router.message(F.text == "📊 Мониторинг Сервера", F.from_user.id == ADMIN_ID)
async def server_monitoring(message: Message):
    db.delete_monitor(message.chat.id)
    from app.keyboards.reply import get_stop_monitor_keyboard
    stats = docker_service.get_server_stats()
    msg = await message.answer(stats, parse_mode="Markdown", reply_markup=get_stop_monitor_keyboard())
    db.save_monitor(message.chat.id, msg.message_id)

@router.message(F.text == "📦 Контейнеры", F.from_user.id == ADMIN_ID)
async def list_containers_msg(message: Message):
    db.delete_monitor(message.chat.id)
    containers = docker_service.get_containers_list()
    if not containers:
        await message.answer("Контейнеры не найдены или Docker недоступен.")
        return
    await message.answer("Выберите контейнер для управления:", reply_markup=get_containers_keyboard(containers))

@router.message(F.text == "♻️ Очистка Docker-системы", F.from_user.id == ADMIN_ID)
async def prune_system_msg(message: Message):
    db.delete_monitor(message.chat.id)
    waiting_msg = await message.answer("⏳ Запуск очистки Docker (prune)... Это может занять время.")
    result = docker_service.prune_system()
    await waiting_msg.edit_text(result, parse_mode="Markdown")