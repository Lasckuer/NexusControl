import os
import time
import platform
import asyncio
import psutil
from app.utils.formatters import format_bytes, format_progress_bar, format_uptime, safe_html

class SystemService:
    """Сервис для сбора метрик аппаратной части сервера (Host OS)"""

    @staticmethod
    def _collect_stats_sync() -> dict:
        """Синхронный сбор метрик через psutil (выполняется в отдельном потоке)"""
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True) or 1
        
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Кроссплатформенный корень диска
        root_path = os.path.abspath(os.sep)
        try:
            disk = psutil.disk_usage(root_path)
        except Exception:
            disk = psutil.disk_usage('/')

        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        try:
            net_io = psutil.net_io_counters()
            bytes_sent = net_io.bytes_sent
            bytes_recv = net_io.bytes_recv
        except Exception:
            bytes_sent = 0
            bytes_recv = 0

        return {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "ram_total": vm.total,
            "ram_used": vm.used,
            "ram_percent": vm.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_percent": disk.percent,
            "uptime_seconds": uptime_seconds,
            "bytes_sent": bytes_sent,
            "bytes_recv": bytes_recv,
            "os_info": f"{platform.system()} {platform.release()}",
        }

    async def get_stats_data(self) -> dict:
        """Неблокирующее получение данных о системе"""
        return await asyncio.to_thread(self._collect_stats_sync)

    async def get_server_stats_message(self) -> str:
        """Сформировать форматированное HTML-сообщение о статусе сервера"""
        stats = await self.get_stats_data()

        cpu_bar = format_progress_bar(stats["cpu_percent"])
        ram_bar = format_progress_bar(stats["ram_percent"])
        disk_bar = format_progress_bar(stats["disk_percent"])

        ram_used_str = format_bytes(stats["ram_used"])
        ram_total_str = format_bytes(stats["ram_total"])
        disk_used_str = format_bytes(stats["disk_used"])
        disk_total_str = format_bytes(stats["disk_total"])
        
        uptime_str = format_uptime(stats["uptime_seconds"])
        net_rx_str = format_bytes(stats["bytes_recv"])
        net_tx_str = format_bytes(stats["bytes_sent"])

        text = (
            f"📊 <b>Статус Сервера</b>\n\n"
            f"💻 <b>ОС:</b> <code>{safe_html(stats['os_info'])}</code>\n"
            f"⏱ <b>Uptime:</b> <code>{safe_html(uptime_str)}</code>\n\n"
            f"🔹 <b>CPU ({stats['cpu_count']} cores):</b> {stats['cpu_percent']}%\n"
            f"   <code>{cpu_bar}</code>\n\n"
            f"🔹 <b>RAM:</b> {stats['ram_percent']}% ({ram_used_str} / {ram_total_str})\n"
            f"   <code>{ram_bar}</code>\n\n"
            f"🔹 <b>Диск:</b> {stats['disk_percent']}% ({disk_used_str} / {disk_total_str})\n"
            f"   <code>{disk_bar}</code>\n\n"
            f"🌐 <b>Сеть:</b> ⬇️ {net_rx_str} | ⬆️ {net_tx_str}"
        )
        return text

system_service = SystemService()
