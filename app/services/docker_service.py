import docker
import psutil

class DockerService:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception:
            self.client = None

    def get_server_stats(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        text = (
            f"📊 **Статус Сервера**\n\n"
            f"🔹 **CPU:** {cpu}%\n"
            f"🔹 **RAM:** {ram.percent}% ({round(ram.used / (1024**3), 2)} / {round(ram.total / (1024**3), 2)} GB)\n"
            f"🔹 **Диск:** {disk.percent}% ({round(disk.used / (1024**3), 2)} / {round(disk.total / (1024**3), 2)} GB)\n"
        )
        return text

    def get_containers_list(self):
        if not self.client:
            return []
        return self.client.containers.list(all=True)

    def get_container_stats(self, name):
        if not self.client:
            return "Ошибка подключения к Docker."
        try:
            container = self.client.containers.get(name)
            status = container.status.upper()
            
            if status == "RUNNING":
                stats = container.stats(stream=False)
                
                cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
                num_cpus = stats["cpu_stats"].get("online_cpus", 1)
                
                cpu_percent = 0.0
                if cpu_delta > 0.0 and system_delta > 0.0:
                    cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

                mem_used = stats["memory_stats"]["usage"]
                mem_limit = stats["memory_stats"]["limit"]
                mem_percent = (mem_used / mem_limit) * 100.0
                
                return (
                    f"📦 **Контейнер:** {name}\n"
                    f"🟢 **Статус:** {status}\n\n"
                    f"🔹 **CPU:** {round(cpu_percent, 2)}%\n"
                    f"🔹 **RAM:** {round(mem_percent, 2)}% ({round(mem_used / (1024**2), 2)} / {round(mem_limit / (1024**2), 2)} MB)"
                )
            else:
                return f"📦 **Контейнер:** {name}\n🔴 **Статус:** {status}"
        except Exception:
            return f"❌ Контейнер {name} не найден или недоступен."

    def control_container(self, name, action):
        if not self.client:
            return False
        try:
            container = self.client.containers.get(name)
            if action == "restart":
                container.restart()
            elif action == "start":
                container.start()
            elif action == "stop":
                container.stop()
            return True
        except Exception as e:
            print(f"Ошибка управления {name}: {e}")
            return False

    def get_logs(self, name):
        if not self.client:
            return "Ошибка Docker."
        try:
            container = self.client.containers.get(name)
            logs = container.logs(tail=50).decode("utf-8")
            return logs if logs else "Логи пусты."
        except Exception as e:
            return str(e)

    def prune_system(self):
        if not self.client:
            return "Ошибка Docker."
        try:
            containers = self.client.containers.prune()
            images = self.client.images.prune()
            networks = self.client.networks.prune()
            volumes = self.client.volumes.prune()
            
            space_saved = (
                containers.get("SpaceReclaimed", 0) + 
                images.get("SpaceReclaimed", 0) + 
                volumes.get("SpaceReclaimed", 0)
            )
            return f"♻️ **Очистка завершена!**\nОсвобождено: {round(space_saved / (1024**2), 2)} MB"
        except Exception as e:
            return f"❌ Ошибка очистки: {str(e)}"

docker_service = DockerService()