import platform
import time
from datetime import datetime

import psutil


def collect_diagnostics():
    """Coleta métricas e gera alertas sem alterar o sistema."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=1.0)

    uptime_hours = int(
        (time.time() - psutil.boot_time()) / 3600
    )

    alerts = []

    if cpu >= 90:
        alerts.append({
            "level": "warning",
            "message": f"Uso elevado de CPU: {cpu:.0f}%",
        })

    if memory.percent >= 90:
        alerts.append({
            "level": "warning",
            "message": (
                f"Memória quase cheia: {memory.percent:.0f}%"
            ),
        })

    if disk.percent >= 90:
        alerts.append({
            "level": "warning",
            "message": (
                f"Pouco espaço livre na raiz: "
                f"{disk.percent:.0f}% usado"
            ),
        })

    if not alerts:
        alerts.append({
            "level": "ok",
            "message": (
                "Nenhum alerta automático encontrado "
                "nas verificações básicas."
            ),
        })

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "system": {
            "os": platform.system(),
            "distribution": platform.platform(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        },
        "metrics": {
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_total_bytes": memory.total,
            "memory_available_bytes": memory.available,
            "root_disk_percent": disk.percent,
            "root_disk_total_bytes": disk.total,
            "root_disk_free_bytes": disk.free,
            "uptime_hours": uptime_hours,
        },
        "alerts": alerts,
    }

