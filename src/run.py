import logging
import os

import load_env
from job import job_func
from src.init_chromium import init_chromium

load_env.load()

logging.basicConfig(
    level=logging.DEBUG if os.getenv("LOG_LEVEL") == "DEBUG" else logging.INFO,
    format="\n%(name)s → %(levelname)s: %(message)s\n",
)

run_logger = logging.getLogger("run")

driver = init_chromium(headless=True)

job_func(run_logger, driver)
