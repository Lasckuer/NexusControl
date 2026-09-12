import pytest
import pytest_asyncio
import os
import tempfile
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.config import Config
from app.database.db import Database

@pytest.fixture
def mock_config():
    """Тестовая конфигурация"""
    return Config(
        bot_token="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ",
        admin_ids={111222, 333444},
        cpu_threshold=90.0,
        ram_threshold=90.0,
        disk_threshold=95.0,
        alert_cooldown=3600,
        refresh_interval=4,
        crash_monitor_interval=5,
        resource_monitor_interval=30,
    )

@pytest_asyncio.fixture
async def temp_db():
    """Изолированная временная база данных для тестов"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(db_path=path)
    await db.init_db()
    yield db
    await db.close()
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def mock_docker_container():
    """Мок Docker-контейнера"""
    container = MagicMock()
    container.name = "web-service-1234567890ab"
    container.status = "running"
    container.image.tags = ["nginx:alpine"]
    container.image.short_id = "sha256:abc1234"
    container.attrs = {
        "State": {
            "Status": "running",
            "Health": {"Status": "healthy"},
            "StartedAt": "2026-09-12T10:00:00.000000000Z",
        },
        "Created": "2026-09-12T09:00:00.000000000Z",
        "RestartCount": 1,
        "NetworkSettings": {
            "IPAddress": "172.17.0.2",
            "Ports": {
                "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]
            }
        }
    }
    container.stats.return_value = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 200000000, "percpu_usage": [100000000, 100000000]},
            "system_cpu_usage": 2000000000,
            "online_cpus": 2
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 100000000},
            "system_cpu_usage": 1000000000
        },
        "memory_stats": {
            "usage": 104857600, # 100 MB
            "limit": 1073741824, # 1 GB
            "stats": {
                "total_inactive_file": 20971520 # 20 MB cache
            }
        },
        "networks": {
            "eth0": {
                "rx_bytes": 1024000,
                "tx_bytes": 2048000
            }
        }
    }
    container.logs.return_value = b"2026-09-12 10:00:01 [info] Server started\n2026-09-12 10:00:02 [info] Ready to accept connections\n"
    return container
