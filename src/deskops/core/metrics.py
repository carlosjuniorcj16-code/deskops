import platform
import time
from datetime import datetime

import psutil


# Limites heurísticos para avaliação dos recursos.
THRESHOLDS = {
    "cpu_percent": (70, 90),
    "memory_percent": (75, 90),
    "root_disk_percent": (75, 90),
    "cpu_temperature_c": (80, 90),
}


def classify_metric(value, warning, critical):
    """Classifica uma métrica usando limites compartilhados."""
    if value is None:
        return "unavailable"
    if value >= critical:
        return "critical"
    if value >= warning:
        return "warning"
    return "normal"


def collect_diagnostics():
    """Coleta métricas e gera alertas sem alterar o sistema."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=1.0)
    temperature = read_cpu_temperature()

    uptime_hours = int(
        (time.time() - psutil.boot_time()) / 3600
    )

    metrics = {
        "cpu_percent": cpu,
        "memory_percent": memory.percent,
        "memory_total_bytes": memory.total,
        "memory_available_bytes": memory.available,
        "root_disk_percent": disk.percent,
        "root_disk_total_bytes": disk.total,
        "root_disk_free_bytes": disk.free,
        "uptime_hours": uptime_hours,
        **temperature,
    }

    labels = {
        "cpu_percent": ("CPU", "%", "Uso de CPU"),
        "memory_percent": ("RAM", "%", "Uso de memória"),
        "root_disk_percent": ("Disco raiz", "%", "Uso do disco raiz"),
        "cpu_temperature_c": (
            "Temperatura da CPU", "°C", "Temperatura da CPU"
        ),
    }

    alerts = []

    for key, (warning, critical) in THRESHOLDS.items():
        value = metrics.get(key)
        level = classify_metric(value, warning, critical)

        if level not in ("warning", "critical"):
            continue

        label, unit, description = labels[key]
        alerts.append({
            "level": level,
            "message": (
                f"{description}: {value:.0f}{unit}"
                if level == "critical"
                else f"{label} elevada: {value:.0f}{unit}"
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
        "metrics": metrics,
        "alerts": alerts,
    }


def read_cpu_temperature():
    """Lê sensores térmicos expostos pelo kernel Linux."""
    from pathlib import Path

    hwmon_root = Path("/sys/class/hwmon")
    readings = []

    try:
        devices = list(hwmon_root.glob("hwmon*"))
    except OSError:
        devices = []

    # Preferir o driver Intel coretemp.
    for device in devices:
        try:
            name = (device / "name").read_text().strip()
        except (OSError, ValueError):
            continue

        if name != "coretemp":
            continue

        for sensor in device.glob("temp*_input"):
            try:
                value = int(sensor.read_text().strip()) / 1000.0
            except (OSError, ValueError):
                continue

            if -10 <= value <= 130:
                readings.append(value)

    if readings:
        return {
            "cpu_temperature_c": max(readings),
            "temperature_sensor": "coretemp",
        }

    # Alternativa quando coretemp não estiver disponível.
    thermal_root = Path("/sys/class/thermal")
    try:
        zones = list(thermal_root.glob("thermal_zone*"))
    except OSError:
        zones = []

    for zone in zones:
        try:
            value = int((zone / "temp").read_text().strip()) / 1000.0
            sensor_type = (zone / "type").read_text().strip()
        except (OSError, ValueError):
            continue

        normalized_type = sensor_type.lower()
        is_cpu_sensor = any(
            token in normalized_type
            for token in ("cpu", "core", "package", "soc")
        )

        if is_cpu_sensor and -10 <= value <= 130:
            return {
                "cpu_temperature_c": value,
                "temperature_sensor": sensor_type,
            }

    return {
        "cpu_temperature_c": None,
        "temperature_sensor": None,
    }


def collect_metrics():
    """Coleta métricas rápidas para o monitoramento contínuo."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=None)
    temperature = read_cpu_temperature()

    return {
        "cpu_percent": cpu,
        "memory_percent": memory.percent,
        "root_disk_percent": disk.percent,
        **temperature,
    }
