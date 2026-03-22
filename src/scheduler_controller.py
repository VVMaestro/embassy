import asyncio
import logging
from threading import Lock, Thread
from typing import Callable

from run_outcome import RunOutcome
from runtime_state import RuntimeStateStore


class SchedulerController:
    def __init__(
        self,
        state_store: RuntimeStateStore,
        logger: logging.Logger,
        driver_factory: Callable | None = None,
        job_runner: Callable | None = None,
    ):
        self.state_store = state_store
        self.logger = logger
        self.driver_factory = driver_factory or self._default_driver_factory
        self.job_runner = job_runner or self._default_job_runner

        self.active_threads: dict[int, Thread] = {}
        self.thread_lock = Lock()
        self.driver_lock = Lock()
        self.shared_driver = None
        self.next_thread_id = 1

    def init_shared_driver(self):
        if self.shared_driver is not None:
            return

        try:
            self.shared_driver = self.driver_factory(headless=True)
            self.shared_driver.get("https://google.com")
            self.logger.info("Shared Chrome driver initialized")
        except Exception as error:
            self.logger.error("Failed to initialize shared Chrome driver: %s", error)
            self.shared_driver = None

    def start_run_process(self) -> bool:
        state = self.state_store.get_state()
        if not state.enabled:
            self.logger.info(
                "Skipping scheduled run because bot is disabled: %s",
                state.disabled_reason or "disabled",
            )
            return False

        self.init_shared_driver()
        if self.shared_driver is None:
            return False

        with self.thread_lock:
            thread_id = self.next_thread_id
            self.next_thread_id += 1

            thread = Thread(target=self.worker_thread, args=(thread_id,), daemon=True)
            self.active_threads[thread_id] = thread

        thread.start()
        self.logger.info("Started worker thread %s", thread_id)
        return True

    def worker_thread(self, thread_id: int):
        thread_logger = logging.getLogger(f"thread_{thread_id}")

        try:
            state = self.state_store.get_state()
            if not state.enabled:
                thread_logger.info("Skipping run because bot is disabled before lock")
                return

            if self.shared_driver is None:
                thread_logger.error("Shared driver is not available")
                return

            with self.driver_lock:
                state = self.state_store.get_state()
                if not state.enabled:
                    thread_logger.info(
                        "Skipping run because bot was disabled before execution"
                    )
                    return

                self.logger.info("Thread %s acquired driver lock", thread_id)
                outcome = self.job_runner(thread_logger, self.shared_driver)
                self.logger.info("Thread %s released driver lock", thread_id)

            self.handle_outcome(outcome, thread_logger)
            self.logger.info("Thread %s completed with outcome %s", thread_id, outcome)
        except Exception as error:
            self.logger.error("Thread %s failed with error: %s", thread_id, error)
        finally:
            with self.thread_lock:
                self.active_threads.pop(thread_id, None)

    def handle_outcome(self, outcome: RunOutcome, logger: logging.Logger):
        if outcome != RunOutcome.APPROVED:
            return

        state = self.state_store.mark_approved_and_disable()
        logger.info("Bot auto-disabled after successful fourth-step approval")

        try:
            from job import notify_bot_with_message

            asyncio.run(
                notify_bot_with_message(
                    "Fourth step approval succeeded. Bot disabled automatically.\n\n"
                    f"Updated at: {state.updated_at}",
                    logger,
                )
            )
        except Exception as error:
            logger.error("Failed to send auto-disable notification: %s", error)

    @staticmethod
    def _default_job_runner(logger: logging.Logger, driver):
        from job import job_func

        return job_func(logger, driver)

    @staticmethod
    def _default_driver_factory(headless=True):
        from init_chromium import init_chromium

        return init_chromium(headless=headless)

    def shutdown(self):
        if self.shared_driver is None:
            return

        try:
            self.shared_driver.quit()
        except Exception as error:
            self.logger.error("Failed to shut down shared driver: %s", error)
        finally:
            self.shared_driver = None
