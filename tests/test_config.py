import pytest
from app.config import Config

def test_config_admin_ids_parsing(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "111, 222, 333 ,invalid, 444")
    monkeypatch.delenv("ADMIN_ID", raising=False)
    
    cfg = Config()
    assert cfg.admin_ids == {111, 222, 333, 444}
    assert cfg.is_admin(111) is True
    assert cfg.is_admin(222) is True
    assert cfg.is_admin(999) is False
    assert cfg.is_admin(None) is False

def test_config_admin_id_legacy_fallback(monkeypatch):
    monkeypatch.delenv("ADMIN_IDS", raising=False)
    monkeypatch.setenv("ADMIN_ID", "55555")
    
    cfg = Config()
    assert cfg.admin_ids == {55555}
    assert cfg.is_admin(55555) is True

def test_config_validation():
    cfg = Config(bot_token="")
    with pytest.raises(ValueError, match="BOT_TOKEN не задан"):
        cfg.validate()

    valid_cfg = Config(bot_token="test_token")
    valid_cfg.validate() # Не должно выбрасывать исключений
