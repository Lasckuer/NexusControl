import pytest

@pytest.mark.asyncio
async def test_database_crud(temp_db):
    # 1. Сохранение монитора
    await temp_db.save_monitor(chat_id=123, message_id=456, container_name="test_c", last_text="Metrics 1")
    monitors = await temp_db.get_all_monitors()
    assert len(monitors) == 1
    assert monitors[0] == (123, 456, "test_c", "Metrics 1")

    # 2. Обновление текста
    await temp_db.update_monitor_text(chat_id=123, last_text="Metrics 2")
    monitors = await temp_db.get_all_monitors()
    assert monitors[0][3] == "Metrics 2"

    # 3. Удаление монитора
    await temp_db.delete_monitor(chat_id=123)
    monitors = await temp_db.get_all_monitors()
    assert len(monitors) == 0

@pytest.mark.asyncio
async def test_intentional_stops(temp_db):
    assert await temp_db.is_intentional_stop("my_container") is False

    await temp_db.add_intentional_stop("my_container")
    assert await temp_db.is_intentional_stop("my_container") is True

    await temp_db.remove_intentional_stop("my_container")
    assert await temp_db.is_intentional_stop("my_container") is False
