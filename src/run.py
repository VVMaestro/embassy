import logging

import load_env
from job import job_func

logging.basicConfig(
    level=logging.INFO, format="\n%(name)s → %(levelname)s: %(message)s\n"
)

load_env.load()

run_logger = logging.getLogger("run")

job_func(run_logger)
