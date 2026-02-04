import logging
import os
import subprocess
import sys
import time
from typing import Dict

import schedule

import load_env

load_env.load()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if os.getenv("LOG_LEVEL") == "DEBUG" else logging.INFO,
    format="\n%(name)s → %(levelname)s: %(message)s\n",
)

schedule_logger = logging.getLogger("schedule")

active_processes: Dict[int, subprocess.Popen] = {}


def start_run_process():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        run_script = os.path.join(script_dir, "run.py")

        process = subprocess.Popen([sys.executable, run_script])
        active_processes[process.pid] = process

        schedule_logger.info(f"Started run process with PID {process.pid}")

    except Exception as e:
        schedule_logger.error(f"Failed to start run process: {str(e)}")


def monitor_processes():
    completed_pids = []
    for pid, process in active_processes.items():
        if process.poll() is not None:
            completed_pids.append(pid)
            schedule_logger.info(
                f"Process with PID {pid} completed with return code {process.returncode}"
            )

    for pid in completed_pids:
        del active_processes[pid]


period = int(os.getenv("SCHEDULER_PERIOD_IN_MINUTES", 1))

schedule.every(period).minutes.do(start_run_process)

while True:
    schedule.run_pending()

    monitor_processes()

    time.sleep(1)
