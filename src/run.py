from job import job_func
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s → %(levelname)s: %(message)s"
)

run_logger = logging.getLogger('run')

job_func(run_logger)
