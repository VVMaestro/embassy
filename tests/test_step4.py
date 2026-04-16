import logging
import unittest
from unittest.mock import MagicMock, patch

from src.job import make_fourth_step, process
from src.run_outcome import RunOutcome


class FakeElement:
    def __init__(self, *, attributes=None):
        self.attributes = attributes or {}

    def get_attribute(self, name):
        return self.attributes.get(name)


class Step4Tests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test.step4")

    def test_make_fourth_step_returns_manual_handoff(self):
        driver = MagicMock()
        final_form = FakeElement(attributes={"id": "mfa-form4"})

        def fake_wait(*args, **kwargs):
            del args, kwargs

            class _Wait:
                def until(self, condition):
                    del condition
                    return final_form

            return _Wait()

        with patch("src.job.WebDriverWait", side_effect=fake_wait), patch(
            "src.job.make_screenshot"
        ) as screenshot_mock, patch("src.job.asyncio.run") as run_mock, patch(
            "src.job.notify_bot_with_message", new=MagicMock(return_value=None)
        ) as notify_mock:
            outcome = make_fourth_step(driver, self.logger)

        self.assertEqual(outcome, RunOutcome.AWAITING_MANUAL_SUBMIT)
        screenshot_mock.assert_called_once_with(
            driver,
            self.logger,
            caption="Step 4 ready for manual submit",
        )
        run_mock.assert_called_once()
        notify_mock.assert_called_once()
        self.assertIn(
            "The bot did not touch the final form",
            notify_mock.call_args.args[0],
        )

    def test_process_preserves_current_window_when_step4_is_ready(self):
        driver = MagicMock()
        driver.title = "Mission appointment management system"

        cleanup_instance = MagicMock()
        cleanup_instance.keep_current_window = False
        cleanup_instance.__enter__.return_value = driver
        cleanup_instance.__exit__.return_value = None

        with patch("src.job.ChromeWithFullCleanup", return_value=cleanup_instance), patch(
            "src.job.make_first_step"
        ), patch("src.job.make_second_step"), patch(
            "src.job.make_third_step", return_value=True
        ), patch(
            "src.job.make_fourth_step",
            return_value=RunOutcome.AWAITING_MANUAL_SUBMIT,
        ):
            outcome = process(self.logger, driver)

        self.assertEqual(outcome, RunOutcome.AWAITING_MANUAL_SUBMIT)
        self.assertTrue(cleanup_instance.keep_current_window)


if __name__ == "__main__":
    unittest.main()
