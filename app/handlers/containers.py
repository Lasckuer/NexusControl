import os
from aiogram import Router, F
from aiogram.types import CallbackQuery
from dotenv import load_dotenv
from app.services.docker_service import docker_service
from app.keyboards.reply import get_container_actions_keyboard, get_containers_keyboard, get_stop_monitor_keyboard, prettify_name
from app.database.db import db

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

router = Router()

@router.callback_query(F.data == "refresh_list", F.from_user.id == ADMIN_ID)
async def refresh_containers_list(callback: CallbackQuery):
    db.delete_monitor(callback.message.chat.id)
    containers = docker_service.get_containers_list()
    await callback.message.edit_text("Выберите контейнер для управления:", reply_markup=get_containers_keyboard(containers))
    await callback.answer()

@router.callback_query(F.data.startswith("manage:"), F.from_user.id == ADMIN_ID)
async def manage_container(callback: CallbackQuery):
    db.delete_monitor(callback.message.chat.id)
    c_name = callback.data.split(":")[1]
    
    nice_name = prettify_name(c_name)
    
    await callback.message.edit_text(f"Управление контейнером: **{nice_name}**", parse_mode="Markdown", reply_markup=get_container_actions_keyboard(c_name))
    await callback.answer()

@router.callback_query(F.data.startswith("action:"), F.from_user.id == ADMIN_ID)
async def action_container(callback: CallbackQuery):
    _, action, name = callback.data.split(":")
    await callback.message.edit_text(f"⏳ Выполняется действие '{action}' для {name}...")
    
    success = docker_service.control_container(name, action)
    
    status_text = "успешно выполнено" if success else "ошибка при выполнении"
    await callback.message.edit_text(
        f"Действие '{action}' для **{name}**: {status_text}.",
        parse_mode="Markdown",
        reply_markup=get_container_actions_keyboard(name)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("logs:"), F.from_user.id == ADMIN_ID)
async def view_container_logs(callback: CallbackQuery):
    name = callback.data.split(":")[1]
    logs = docker_service.get_logs(name)
    
    if len(logs) > 4000:
        logs = logs[-4000:]
        
    await callback.message.answer(f"📋 **Логи {name}:**\n```text\n{logs}\n```", parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("monitor_c:"), F.from_user.id == ADMIN_ID)
async def start_container_monitor(callback: CallbackQuery):
    name = callback.data.split(":")[1]
    stats = docker_service.get_container_stats(name)
    await callback.message.edit_text(stats, parse_mode="Markdown", reply_markup=get_stop_monitor_keyboard())
    db.save_monitor(callback.message.chat.id, callback.message.message_id, name)
    await callback.answer()

@router.callback_query(F.data == "stop_monitoring", F.from_user.id == ADMIN_ID)
async def stop_monitoring_action(callback: CallbackQuery):
    db.delete_monitor(callback.message.chat.id)
    await callback.message.edit_text("📈 Обновление метрик остановлено.")
    await callback.answer()