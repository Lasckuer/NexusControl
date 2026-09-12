from unittest.mock import MagicMock
from app.keyboards.inline import (
    get_containers_keyboard,
    get_container_actions_keyboard,
    get_logs_options_keyboard,
    get_confirm_keyboard,
    get_prune_confirm_keyboard,
)

def make_dummy_container(name: str, status: str = "running"):
    c = MagicMock()
    c.name = name
    c.status = status
    return c

def test_containers_keyboard_pagination():
    containers = [make_dummy_container(f"container-{i}") for i in range(15)]
    
    # 1-я страница (0..5)
    kb_page0 = get_containers_keyboard(containers, page=0, per_page=6)
    # 1 строка фильтров + 6 контейнеров + 1 строка навигации + 1 строка обновить
    assert len(kb_page0.inline_keyboard) == 9
    
    # Проверяем кнопку навигации вперед
    nav_row = kb_page0.inline_keyboard[7]
    assert nav_row[1].text == "1/3"
    assert nav_row[2].callback_data == "page:1"

def test_containers_keyboard_filters():
    c_running = make_dummy_container("c-run", "running")
    c_stopped = make_dummy_container("c-stop", "exited")
    containers = [c_running, c_stopped]

    # Фильтр только работающие
    kb_running = get_containers_keyboard(containers, status_filter="running")
    # Должен остаться только c-run
    container_buttons = [row[0] for row in kb_running.inline_keyboard[1:-1]]
    assert len(container_buttons) == 1
    assert container_buttons[0].callback_data == "manage:c-run"

def test_container_actions_keyboard():
    # Для работающего
    kb_run = get_container_actions_keyboard("app", is_running=True)
    all_callbacks = [btn.callback_data for row in kb_run.inline_keyboard for btn in row]
    assert "action:stop:app" in all_callbacks
    assert "action:pause:app" in all_callbacks
    assert "confirm_req:kill:app" in all_callbacks

    # Для остановленного
    kb_stop = get_container_actions_keyboard("app", is_running=False)
    all_callbacks_stop = [btn.callback_data for row in kb_stop.inline_keyboard for btn in row]
    assert "action:start:app" in all_callbacks_stop

def test_confirm_keyboards():
    confirm_kb = get_confirm_keyboard("kill", "web")
    assert confirm_kb.inline_keyboard[0][0].callback_data == "confirm:kill:web"
    assert confirm_kb.inline_keyboard[0][1].callback_data == "cancel_action:web"

    prune_kb = get_prune_confirm_keyboard()
    assert len(prune_kb.inline_keyboard) == 3
