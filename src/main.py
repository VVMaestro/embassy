import logging
import os
import time

import schedule

import load_env
from job import job_func

load_env.load()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if os.getenv("LOG_LEVEL") == "DEBUG" else logging.INFO,
    format="\n%(name)s → %(levelname)s: %(message)s\n",
)

schedule_logger = logging.getLogger("schedule")

period = int(os.getenv("SCHEDULER_PERIOD_IN_MINUTES", 1))

schedule.every(period).minutes.do(lambda: job_func(schedule_logger))

while True:
    schedule.run_pending()

    time.sleep(1)
