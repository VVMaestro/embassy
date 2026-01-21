import logging
import os

import load_env
from job import job_func

load_env.load()

logging.basicConfig(
    level=logging.DEBUG if os.getenv("LOG_LEVEL") == "DEBUG" else logging.INFO,
    format="\n%(name)s → %(levelname)s: %(message)s\n",
)

run_logger = logging.getLogger("run")

job_func(run_logger)
