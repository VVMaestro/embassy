import logging
import os
import tempfile
import unittest

from src.run_outcome import RunOutcome
from src.runtime_state import RuntimeStateStore
from src.scheduler_controller import SchedulerController


class FakeDriver:
    def __init__(self):
        self.urls = []
        self.quit_called = False

    def get(self, url: str):
        self.urls.append(url)

    def quit(self):
        self.quit_called = True


class SchedulerControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.state_path = os.path.join(self.temp_dir.name, "runtime_state.json")
        self.store = RuntimeStateStore(self.state_path, logging.getLogger("test.state"))
        self.logger = logging.getLogger("test.scheduler")

    def test_disabled_state_skips_scheduled_run(self):
        self.store.disable("manual_disable")
        driver_created = {"count": 0}

        def driver_factory(headless=True):
            del headless
            driver_created["count"] += 1
            return FakeDriver()

        controller = SchedulerController(
            state_store=self.store,
            logger=self.logger,
            driver_factory=driver_factory,
            job_runner=lambda logger, driver: RunOutcome.NO_SLOT,
        )

        started = controller.start_run_process()

        self.assertFalse(started)
        self.assertEqual(driver_created["count"], 0)

    def test_approved_outcome_auto_disables_bot(self):
        controller = SchedulerController(
            state_store=self.store,
            logger=self.logger,
            driver_factory=lambda headless=True: FakeDriver(),
            job_runner=lambda logger, driver: RunOutcome.APPROVED,
        )

        controller.init_shared_driver()
        controller.worker_thread(1)

        state = self.store.get_state()
        self.assertFalse(state.enabled)
        self.assertEqual(
            state.disabled_reason,
            "auto_disabled_after_step4_success",
        )
        self.assertIsNotNone(state.last_success_at)

    def test_non_success_outcome_keeps_bot_enabled(self):
        controller = SchedulerController(
            state_store=self.store,
            logger=self.logger,
            driver_factory=lambda headless=True: FakeDriver(),
            job_runner=lambda logger, driver: RunOutcome.NO_SLOT,
        )

        controller.init_shared_driver()
        controller.worker_thread(1)

        state = self.store.get_state()
        self.assertTrue(state.enabled)

    def test_captcha_failed_outcome_keeps_bot_enabled(self):
        controller = SchedulerController(
            state_store=self.store,
            logger=self.logger,
            driver_factory=lambda headless=True: FakeDriver(),
            job_runner=lambda logger, driver: RunOutcome.CAPTCHA_FAILED,
        )

        controller.init_shared_driver()
        controller.worker_thread(1)

        state = self.store.get_state()
        self.assertTrue(state.enabled)

    def test_manual_submit_outcome_auto_disables_bot(self):
        controller = SchedulerController(
            state_store=self.store,
            logger=self.logger,
            driver_factory=lambda headless=True: FakeDriver(),
            job_runner=lambda logger, driver: RunOutcome.AWAITING_MANUAL_SUBMIT,
        )

        controller.init_shared_driver()
        controller.worker_thread(1)

        state = self.store.get_state()
        self.assertFalse(state.enabled)
        self.assertEqual(state.disabled_reason, "awaiting_manual_submit")
        self.assertTrue(controller.driver_reset_required)

    def test_init_shared_driver_uses_visible_browser(self):
        driver_options = []

        def driver_factory(headless=True):
            driver_options.append(headless)
            return FakeDriver()

        controller = SchedulerController(
            state_store=self.store,
            logger=self.logger,
            driver_factory=driver_factory,
            job_runner=lambda logger, driver: RunOutcome.NO_SLOT,
        )

        controller.init_shared_driver()

        self.assertEqual(driver_options, [False])

    def test_init_shared_driver_recreates_browser_after_manual_submit(self):
        created_drivers = []

        def driver_factory(headless=True):
            del headless
            driver = FakeDriver()
            created_drivers.append(driver)
            return driver

        controller = SchedulerController(
            state_store=self.store,
            logger=self.logger,
            driver_factory=driver_factory,
            job_runner=lambda logger, driver: RunOutcome.NO_SLOT,
        )

        controller.init_shared_driver()
        first_driver = controller.shared_driver
        controller.driver_reset_required = True

        controller.init_shared_driver()

        self.assertIsNotNone(first_driver)
        self.assertTrue(first_driver.quit_called)
        self.assertEqual(len(created_drivers), 2)
        self.assertIs(controller.shared_driver, created_drivers[1])


if __name__ == "__main__":
    unittest.main()
