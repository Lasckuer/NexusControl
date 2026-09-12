import pytest
from unittest.mock import MagicMock
from app.services.docker_service import DockerService
from docker.errors import NotFound

@pytest.mark.asyncio
async def test_docker_service_list_containers(mock_docker_container):
    service = DockerService()
    mock_client = MagicMock()
    mock_client.containers.list.return_value = [mock_docker_container]
    service._client = mock_client

    containers = await service.get_containers_list()
    assert len(containers) == 1
    assert containers[0].name == "web-service-1234567890ab"

@pytest.mark.asyncio
async def test_docker_service_get_stats_running(mock_docker_container):
    service = DockerService()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_docker_container
    service._client = mock_client

    stats_msg = await service.get_container_stats("web-service-1234567890ab")
    assert "web-service-1234567890ab" in stats_msg
    assert "CPU:" in stats_msg
    assert "RAM:" in stats_msg
    assert "Сеть:" in stats_msg

@pytest.mark.asyncio
async def test_docker_service_get_stats_stopped():
    service = DockerService()
    mock_client = MagicMock()
    c = MagicMock()
    c.status = "exited"
    c.name = "stopped-container"
    mock_client.containers.get.return_value = c
    service._client = mock_client

    stats_msg = await service.get_container_stats("stopped-container")
    assert "Контейнер остановлен" in stats_msg

@pytest.mark.asyncio
async def test_docker_service_inspect(mock_docker_container):
    service = DockerService()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_docker_container
    service._client = mock_client

    inspect_msg = await service.inspect_container("web-service-1234567890ab")
    assert "Детали контейнера" in inspect_msg
    assert "172.17.0.2" in inspect_msg
    assert "8080" in inspect_msg
    assert "80/tcp" in inspect_msg

@pytest.mark.asyncio
async def test_docker_service_control(mock_docker_container):
    service = DockerService()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_docker_container
    service._client = mock_client

    ok, msg = await service.control_container("web-service-1234567890ab", "restart")
    assert ok is True
    mock_docker_container.restart.assert_called_once()

    ok, msg = await service.control_container("web-service-1234567890ab", "stop")
    assert ok is True
    mock_docker_container.stop.assert_called_once()

    ok, msg = await service.control_container("web-service-1234567890ab", "kill")
    assert ok is True
    mock_docker_container.kill.assert_called_once()

@pytest.mark.asyncio
async def test_docker_service_logs(mock_docker_container):
    service = DockerService()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_docker_container
    service._client = mock_client

    logs = await service.get_logs("web-service-1234567890ab", tail=50)
    assert "Server started" in logs

@pytest.mark.asyncio
async def test_docker_service_not_found():
    service = DockerService()
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = NotFound("Not found")
    service._client = mock_client

    stats = await service.get_container_stats("ghost")
    assert "не найден" in stats

    ok, msg = await service.control_container("ghost", "restart")
    assert ok is False
    assert "не найден" in msg

@pytest.mark.asyncio
async def test_docker_service_prune():
    service = DockerService()
    mock_client = MagicMock()
    mock_client.containers.prune.return_value = {"SpaceReclaimed": 1048576, "ContainersDeleted": ["c1"]}
    mock_client.images.prune.return_value = {"SpaceReclaimed": 2097152, "ImagesDeleted": ["i1", "i2"]}
    mock_client.networks.prune.return_value = {"NetworksDeleted": ["n1"]}
    mock_client.volumes.prune.return_value = {"SpaceReclaimed": 0, "VolumesDeleted": []}
    service._client = mock_client

    result = await service.prune_system(prune_volumes=False)
    assert "Очистка Docker завершена" in result
    assert "3.0 MB" in result
