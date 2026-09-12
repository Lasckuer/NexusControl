import asyncio
import datetime
from typing import Any
import docker
from docker.errors import DockerException, NotFound, APIError
from logger import logger
from app.utils.formatters import (
    format_bytes,
    format_progress_bar,
    format_status_badge,
    format_health_badge,
    safe_html,
)
from app.utils.aliases import prettify_name

class DockerService:
    """Асинхронный сервис для взаимодействия с Docker API"""

    def __init__(self):
        self._client: docker.DockerClient | None = None
        self._init_client()

    def _init_client(self) -> None:
        """Попытка инициализировать клиент Docker"""
        try:
            self._client = docker.from_env()
            self._client.ping()
            logger.info("Успешное подключение к Docker демону.")
        except Exception as e:
            self._client = None
            logger.warning(f"Не удалось подключиться к Docker демону: {e}")

    def ensure_client(self) -> docker.DockerClient | None:
        """Получить клиент Docker с автоматическим переподключением"""
        if self._client is None:
            self._init_client()
        else:
            try:
                self._client.ping()
            except Exception:
                logger.warning("Связь с Docker потеряна. Попытка переподключения...")
                self._init_client()
        return self._client

    # ------------------ Синхронные методы (для to_thread) ------------------

    def _get_containers_list_sync(self, status_filter: str | None = None) -> list[Any]:
        client = self.ensure_client()
        if not client:
            return []
        try:
            if status_filter:
                return client.containers.list(all=True, filters={"status": status_filter})
            return client.containers.list(all=True)
        except Exception as e:
            logger.error(f"Ошибка получения списка контейнеров: {e}")
            return []

    def _get_container_stats_sync(self, name: str) -> str:
        client = self.ensure_client()
        if not client:
            return "❌ Ошибка подключения к Docker демону."
        try:
            container = client.containers.get(name)
            status = container.status.lower()
            nice_name = prettify_name(name)
            status_badge = format_status_badge(status)

            if status != "running":
                return (
                    f"📦 <b>Контейнер:</b> {safe_html(nice_name)} (<code>{safe_html(name)}</code>)\n"
                    f"Статус: {status_badge}\n"
                    f"<i>Контейнер остановлен. Метрики реального времени недоступны.</i>"
                )

            # Получаем метрики в реальном времени (stream=False)
            stats = container.stats(stream=False)
            
            # Расчет CPU%
            cpu_percent = 0.0
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})
            
            cpu_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            precpu_usage = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            cpu_delta = cpu_usage - precpu_usage

            system_cpu_usage = cpu_stats.get("system_cpu_usage", 0)
            system_precpu_usage = precpu_stats.get("system_cpu_usage", 0)
            system_delta = system_cpu_usage - system_precpu_usage

            online_cpus = cpu_stats.get("online_cpus") or len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [])) or 1

            if cpu_delta > 0 and system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

            # Расчет RAM
            mem_stats = stats.get("memory_stats", {})
            mem_used_raw = mem_stats.get("usage", 0)
            mem_limit = mem_stats.get("limit", 1)

            # Вычитаем неактивный кэш страниц, если доступен (как в docker stats)
            mem_details = mem_stats.get("stats", {})
            cache = mem_details.get("total_inactive_file") or mem_details.get("inactive_file") or 0
            mem_used = max(0, mem_used_raw - cache)
            mem_percent = (mem_used / mem_limit * 100.0) if mem_limit > 0 else 0.0

            # Сетевая статистика
            rx_bytes = 0
            tx_bytes = 0
            networks = stats.get("networks", {})
            for net in networks.values():
                rx_bytes += net.get("rx_bytes", 0)
                tx_bytes += net.get("tx_bytes", 0)

            cpu_bar = format_progress_bar(cpu_percent)
            mem_bar = format_progress_bar(mem_percent)

            return (
                f"📦 <b>Контейнер:</b> {safe_html(nice_name)} (<code>{safe_html(name)}</code>)\n"
                f"Статус: {status_badge}\n\n"
                f"🔹 <b>CPU:</b> {round(cpu_percent, 2)}%\n"
                f"   <code>{cpu_bar}</code>\n\n"
                f"🔹 <b>RAM:</b> {round(mem_percent, 2)}% ({format_bytes(mem_used)} / {format_bytes(mem_limit)})\n"
                f"   <code>{mem_bar}</code>\n\n"
                f"🌐 <b>Сеть:</b> ⬇️ {format_bytes(rx_bytes)} | ⬆️ {format_bytes(tx_bytes)}"
            )

        except NotFound:
            return f"❌ Контейнер <code>{safe_html(name)}</code> не найден."
        except Exception as e:
            logger.error(f"Ошибка получения метрик для {name}: {e}")
            return f"❌ Ошибка получения метрик для <code>{safe_html(name)}</code>: {safe_html(str(e))}"

    def _inspect_container_sync(self, name: str) -> str:
        client = self.ensure_client()
        if not client:
            return "❌ Ошибка подключения к Docker демону."
        try:
            container = client.containers.get(name)
            attrs = container.attrs
            nice_name = prettify_name(name)

            state = attrs.get("State", {})
            status = state.get("Status", "unknown")
            status_badge = format_status_badge(status)

            health = state.get("Health", {}).get("Status")
            health_badge = format_health_badge(health)

            image = container.image.tags[0] if container.image.tags else container.image.short_id
            created = attrs.get("Created", "")[:19].replace("T", " ")
            started_at = state.get("StartedAt", "")[:19].replace("T", " ")
            restart_count = attrs.get("RestartCount", 0)

            # Сети и IP
            net_settings = attrs.get("NetworkSettings", {})
            ip_address = net_settings.get("IPAddress")
            if not ip_address:
                networks = net_settings.get("Networks", {})
                ips = [v.get("IPAddress") for v in networks.values() if v.get("IPAddress")]
                ip_address = ", ".join(ips) if ips else "Host / None"

            # Порты
            ports = net_settings.get("Ports", {})
            ports_list = []
            for container_port, host_bindings in ports.items():
                if host_bindings:
                    for b in host_bindings:
                        host_ip = b.get("HostIp", "0.0.0.0")
                        host_port = b.get("HostPort", "")
                        ports_list.append(f"{host_ip}:{host_port}->{container_port}")
                else:
                    ports_list.append(f"{container_port}")
            ports_str = ", ".join(ports_list) if ports_list else "Нет проброшенных портов"

            text = (
                f"ℹ️ <b>Детали контейнера</b>\n\n"
                f"🏷 <b>Имя:</b> <code>{safe_html(name)}</code> ({safe_html(nice_name)})\n"
                f"🔹 <b>Статус:</b> {status_badge}\n"
                f"🔹 <b>Здоровье:</b> {health_badge}\n"
                f"🔹 <b>Образ:</b> <code>{safe_html(image)}</code>\n"
                f"🔹 <b>Создан:</b> <code>{safe_html(created)}</code>\n"
                f"🔹 <b>Запущен:</b> <code>{safe_html(started_at)}</code>\n"
                f"🔹 <b>Рестартов:</b> {restart_count}\n"
                f"🔹 <b>IP:</b> <code>{safe_html(ip_address)}</code>\n"
                f"🔹 <b>Порты:</b> <code>{safe_html(ports_str)}</code>"
            )
            return text
        except NotFound:
            return f"❌ Контейнер <code>{safe_html(name)}</code> не найден."
        except Exception as e:
            logger.error(f"Ошибка инспекции контейнера {name}: {e}")
            return f"❌ Ошибка инспекции: {safe_html(str(e))}"

    def _control_container_sync(self, name: str, action: str) -> tuple[bool, str]:
        client = self.ensure_client()
        if not client:
            return False, "Docker недоступен."
        try:
            container = client.containers.get(name)
            if action == "restart":
                container.restart(timeout=10)
            elif action == "start":
                container.start()
            elif action == "stop":
                container.stop(timeout=10)
            elif action == "pause":
                container.pause()
            elif action == "unpause":
                container.unpause()
            elif action == "kill":
                container.kill()
            else:
                return False, f"Неизвестное действие: {action}"
            return True, "Успешно выполнено"
        except NotFound:
            return False, "Контейнер не найден"
        except Exception as e:
            logger.error(f"Ошибка выполнения {action} для {name}: {e}")
            return False, str(e)

    def _get_logs_sync(self, name: str, tail: int = 100) -> str:
        client = self.ensure_client()
        if not client:
            return "Ошибка подключения к Docker."
        try:
            container = client.containers.get(name)
            raw_logs = container.logs(tail=tail, timestamps=True)
            logs = raw_logs.decode("utf-8", errors="replace")
            return logs if logs.strip() else "Логи пусты."
        except NotFound:
            return f"Контейнер {name} не найден."
        except Exception as e:
            logger.error(f"Ошибка чтения логов {name}: {e}")
            return f"Ошибка чтения логов: {str(e)}"

    def _get_docker_system_info_sync(self) -> str:
        client = self.ensure_client()
        if not client:
            return "❌ Docker демон недоступен."
        try:
            version_info = client.version()
            docker_version = version_info.get("Version", "Unknown")
            api_version = version_info.get("ApiVersion", "Unknown")
            os_type = version_info.get("Os", "Unknown")

            containers = client.containers.list(all=True)
            running = sum(1 for c in containers if c.status == "running")
            paused = sum(1 for c in containers if c.status == "paused")
            stopped = sum(1 for c in containers if c.status in ["exited", "stopped", "dead"])

            images = client.images.list()

            text = (
                f"🐳 <b>Информация о Docker</b>\n\n"
                f"🔹 <b>Версия Docker:</b> <code>{safe_html(docker_version)}</code> (API: {safe_html(api_version)})\n"
                f"🔹 <b>ОС движка:</b> <code>{safe_html(os_type)}</code>\n\n"
                f"📦 <b>Контейнеры:</b> Всего {len(containers)}\n"
                f"   🟢 Работают: {running}\n"
                f"   ⏸ На паузе: {paused}\n"
                f"   🔴 Остановлены: {stopped}\n\n"
                f"🖼 <b>Образов:</b> {len(images)}"
            )
            return text
        except Exception as e:
            logger.error(f"Ошибка получения информации о Docker: {e}")
            return f"❌ Ошибка Docker: {safe_html(str(e))}"

    def _prune_system_sync(self, prune_volumes: bool = False) -> str:
        client = self.ensure_client()
        if not client:
            return "❌ Docker демон недоступен."
        try:
            c_res = client.containers.prune()
            i_res = client.images.prune()
            n_res = client.networks.prune()
            v_res = client.volumes.prune() if prune_volumes else {"SpaceReclaimed": 0}

            reclaimed = (
                c_res.get("SpaceReclaimed", 0) +
                i_res.get("SpaceReclaimed", 0) +
                v_res.get("SpaceReclaimed", 0)
            )

            del_containers = len(c_res.get("ContainersDeleted") or [])
            del_images = len(i_res.get("ImagesDeleted") or [])
            del_networks = len(n_res.get("NetworksDeleted") or [])

            text = (
                f"♻️ <b>Очистка Docker завершена!</b>\n\n"
                f"🔹 <b>Освобождено места:</b> {format_bytes(reclaimed)}\n"
                f"🔹 Удалено остановленных контейнеров: {del_containers}\n"
                f"🔹 Удалено неиспользуемых образов: {del_images}\n"
                f"🔹 Удалено неиспользуемых сетей: {del_networks}\n"
            )
            if prune_volumes:
                del_volumes = len(v_res.get("VolumesDeleted") or [])
                text += f"🔹 Удалено неиспользуемых томов (Volumes): {del_volumes}\n"

            return text
        except Exception as e:
            logger.error(f"Ошибка prune Docker: {e}")
            return f"❌ Ошибка очистки Docker: {safe_html(str(e))}"

    # ------------------ Асинхронные интерфейсы ------------------

    async def get_containers_list(self, status_filter: str | None = None) -> list[Any]:
        return await asyncio.to_thread(self._get_containers_list_sync, status_filter)

    async def get_container_stats(self, name: str) -> str:
        return await asyncio.to_thread(self._get_container_stats_sync, name)

    async def inspect_container(self, name: str) -> str:
        return await asyncio.to_thread(self._inspect_container_sync, name)

    async def control_container(self, name: str, action: str) -> tuple[bool, str]:
        return await asyncio.to_thread(self._control_container_sync, name, action)

    async def get_logs(self, name: str, tail: int = 100) -> str:
        return await asyncio.to_thread(self._get_logs_sync, name, tail)

    async def get_docker_system_info(self) -> str:
        return await asyncio.to_thread(self._get_docker_system_info_sync)

    async def prune_system(self, prune_volumes: bool = False) -> str:
        return await asyncio.to_thread(self._prune_system_sync, prune_volumes)

docker_service = DockerService()