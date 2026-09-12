import pytest
from app.services.system_service import SystemService

@pytest.mark.asyncio
async def test_system_service():
    service = SystemService()
    stats = await service.get_stats_data()

    assert "cpu_percent" in stats
    assert "ram_percent" in stats
    assert "disk_percent" in stats
    assert "uptime_seconds" in stats
    assert stats["cpu_count"] >= 1

    msg = await service.get_server_stats_message()
    assert "Статус Сервера" in msg
    assert "CPU" in msg
    assert "RAM" in msg
    assert "Диск" in msg
