import os
import math
import time
import psutil


def collect_top_processes(limit=10):
    """Coleta processos e métricas sem interromper a interface."""
    processes = []

    for proc in psutil.process_iter(
        ["pid", "name", "username", "memory_percent"]
    ):
        try:
            proc.cpu_percent(interval=None)
            processes.append({
                "process": proc,
                "pid": proc.info["pid"],
                "name": proc.info["name"] or "Unknown",
                "username": proc.info["username"] or "Unknown",
                "memory_percent": proc.info["memory_percent"] or 0.0,
                "create_time": proc.create_time(),
            })
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    time.sleep(0.5)
    results = []

    for item in processes:
        try:
            results.append({
                "pid": item["pid"],
                "name": item["name"],
                "username": item["username"],
                "memory_percent": item["memory_percent"],
                "cpu_percent": item["process"].cpu_percent(interval=None),
                "create_time": item["create_time"],
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
    return results if limit is None else results[:limit]


def terminate_process(pid, expected_create_time, force=False):
    """Encerra processo do usuário após validar sua identidade."""
    pid = int(pid)

    if pid <= 1 or pid == os.getpid():
        raise PermissionError(
            "Este processo é protegido contra encerramento pelo DeskOps."
        )

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise PermissionError(
            "Execute o DeskOps como usuário normal, não como root."
        )

    proc = psutil.Process(pid)

    # Protege o DeskOps e os processos ancestrais que o iniciaram.
    current = psutil.Process(os.getpid())
    protected_pids = {current.pid}

    while current.ppid() > 1:
        parent_pid = current.ppid()
        protected_pids.add(parent_pid)
        try:
            current = psutil.Process(parent_pid)
        except psutil.Error:
            break

    if pid in protected_pids:
        raise PermissionError(
            "O processo é o DeskOps ou um de seus ancestrais."
        )

    # A identidade original é obrigatória: nunca agir apenas pelo PID.
    if expected_create_time is None:
        raise RuntimeError(
            "Não foi possível confirmar a identidade do processo. "
            "Atualize a lista e selecione-o novamente."
        )

    try:
        expected_create_time = float(expected_create_time)
    except (TypeError, ValueError):
        raise RuntimeError(
            "A identidade do processo é inválida. Atualize a lista."
        ) from None

    if not math.isfinite(expected_create_time):
        raise RuntimeError(
            "A identidade do processo é inválida. Atualize a lista."
        )

    # Evita agir sobre outro processo caso o PID tenha sido reutilizado.
    if abs(proc.create_time() - expected_create_time) > 0.01:
        raise RuntimeError(
            "O processo mudou desde a seleção. Atualize a lista."
        )

    current_user = psutil.Process(os.getpid()).username()
    if proc.username() != current_user:
        raise PermissionError(
            "Só é permitido encerrar processos do usuário atual."
        )

    if force:
        proc.kill()
    else:
        proc.terminate()

    proc.wait(timeout=3)
