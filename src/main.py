import logging
import os
import threading
import time
from threading import Lock, Thread
from typing import Dict

import schedule

import load_env
from init_chromium import init_chromium
from job import job_func

load_env.load()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if os.getenv("LOG_LEVEL") == "DEBUG" else logging.INFO,
    format="\n%(name)s → %(levelname)s: %(message)s\n",
)

schedule_logger = logging.getLogger("schedule")

active_threads: Dict[int, Thread] = {}
thread_lock = threading.Lock()  # For thread-safe operations
driver_lock = Lock()  # For sequential driver access
shared_driver = None


def init_shared_driver():
    """Initialize the shared Chrome driver instance"""
    global shared_driver

    if shared_driver is None:
        try:
            shared_driver = init_chromium(headless=True)
            schedule_logger.info("Shared Chrome driver initialized")
        except Exception as e:
            schedule_logger.error(
                f"Failed to initialize shared Chrome driver: {str(e)}"
            )
            shared_driver = None


def worker_thread(thread_id: int):
    """Worker function that runs the job with shared driver"""
    global shared_driver

    try:
        # Create a logger for this thread
        thread_logger = logging.getLogger(f"thread_{thread_id}")

        # Check if driver is available
        if shared_driver is None:
            thread_logger.error("Shared driver is not available")
            return

        # Acquire driver lock for exclusive access
        with driver_lock:
            schedule_logger.info(f"Thread {thread_id} acquired driver lock")

            # Run the job with shared driver
            job_func(thread_logger, shared_driver)

            schedule_logger.info(f"Thread {thread_id} released driver lock")

        # Mark thread as completed
        with thread_lock:
            if thread_id in active_threads:
                del active_threads[thread_id]

        schedule_logger.info(f"Thread {thread_id} completed successfully")

    except Exception as e:
        schedule_logger.error(f"Thread {thread_id} failed with error: {str(e)}")
        # Clean up thread reference on error
        with thread_lock:
            if thread_id in active_threads:
                del active_threads[thread_id]


def start_run_process():
    try:
        # Initialize shared driver if not already done
        init_shared_driver()

        # Generate thread ID
        thread_id = len(active_threads) + 1

        # Create and start thread
        thread = Thread(target=worker_thread, args=(thread_id,), daemon=True)
        thread.start()

        # Track active thread
        with thread_lock:
            active_threads[thread_id] = thread

        schedule_logger.info(f"Started worker thread {thread_id}")

    except Exception as e:
        schedule_logger.error(f"Failed to start worker thread: {str(e)}")


period = int(os.getenv("SCHEDULER_PERIOD_IN_MINUTES", 1))

schedule.every(period).minutes.do(start_run_process)


def run_scheduler():
    """Run the scheduler loop - for manual testing"""
    while True:
        schedule.run_pending()
        time.sleep(1)


# Only run scheduler if this file is executed directly
if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
