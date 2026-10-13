import time

import psutil


def collect_top_processes(limit=10):
    """Retorna os processos com maior uso recente de CPU."""
    processes = []

    for proc in psutil.process_iter(
        ["pid", "name", "username", "memory_percent"]
    ):
        try:
            # Primeira amostra: inicializa o contador de CPU.
            proc.cpu_percent(interval=None)

            processes.append({
                "process": proc,
                "pid": proc.info["pid"],
                "name": proc.info["name"] or "Unknown",
                "username": proc.info["username"] or "Unknown",
                "memory_percent": (
                    proc.info["memory_percent"] or 0.0
                ),
            })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    # Intervalo menor para uma atualização mais rápida.
    time.sleep(0.5)

    results = []

    for item in processes:
        try:
            cpu_percent = item["process"].cpu_percent(
                interval=None
            )

            results.append({
                "pid": item["pid"],
                "name": item["name"],
                "username": item["username"],
                "memory_percent": item["memory_percent"],
                "cpu_percent": cpu_percent,
            })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    results.sort(
        key=lambda process: process["cpu_percent"],
        reverse=True,
    )

    return results[:limit]

