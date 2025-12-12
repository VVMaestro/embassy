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

schedule.every(30).seconds.do(lambda: job_func(schedule_logger))

while True:
    schedule.run_pending()
    time.sleep(1)
