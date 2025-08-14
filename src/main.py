import time
import logging
import schedule
from job import job_func

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="\n%(name)s → %(levelname)s: %(message)s\n"
)

schedule_logger = logging.getLogger('schedule')
FileOutputHandler = logging.FileHandler('/app/logs/bot.log')
schedule_logger.addHandler(FileOutputHandler)

schedule.every(30).seconds.do(lambda : job_func(schedule_logger))

while True:
    schedule.run_pending()
    time.sleep(1)
