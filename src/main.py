import logging
import os
from threading import Event, Thread

import schedule

import load_env
from bot_control import TelegramControlServer
from runtime_state import RuntimeStateStore, default_state_path
from scheduler_controller import SchedulerController

load_env.load()


def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("LOG_LEVEL") == "DEBUG" else logging.INFO,
        format="\n%(name)s → %(levelname)s: %(message)s\n",
    )


def run_scheduler(stop_event: Event):
    while not stop_event.is_set():
        schedule.run_pending()
        stop_event.wait(1)


def main():
    configure_logging()

    schedule_logger = logging.getLogger("schedule")
    state_store = RuntimeStateStore(
        os.getenv("BOT_STATE_PATH", default_state_path()),
        logging.getLogger("runtime_state"),
    )
    controller = SchedulerController(state_store, schedule_logger)
    control_server = TelegramControlServer(
        state_store=state_store,
        logger=logging.getLogger("telegram_control"),
    )

    period = int(os.getenv("SCHEDULER_PERIOD_IN_MINUTES", 1))
    schedule.every(period).minutes.do(controller.start_run_process)

    stop_event = Event()
    scheduler_thread = Thread(
        target=run_scheduler,
        args=(stop_event,),
        daemon=True,
        name="scheduler",
    )
    scheduler_thread.start()

    try:
        control_server.run()
    finally:
        stop_event.set()
        controller.shutdown()
        scheduler_thread.join(timeout=5)


if __name__ == "__main__":
    main()
