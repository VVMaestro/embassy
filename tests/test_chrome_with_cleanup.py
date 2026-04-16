import logging
import unittest

from src.chrome_with_cleanup import ChromeWithFullCleanup


class FakeSwitchTo:
    def __init__(self):
        self.window_calls = []

    def window(self, handle):
        self.window_calls.append(handle)


class FakeDriver:
    def __init__(self):
        self.current_window_handle = "original"
        self.window_handles = ["original", "job"]
        self.switch_to = FakeSwitchTo()
        self.close_called = 0

    def close(self):
        self.close_called += 1


class ChromeWithCleanupTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test.chrome_cleanup")

    def test_exit_closes_current_window_by_default(self):
        driver = FakeDriver()
        cleanup = ChromeWithFullCleanup(self.logger, driver)

        cleanup.__exit__(None, None, None)

        self.assertEqual(driver.close_called, 1)
        self.assertEqual(driver.switch_to.window_calls, ["original"])

    def test_exit_keeps_current_window_open_when_requested(self):
        driver = FakeDriver()
        cleanup = ChromeWithFullCleanup(self.logger, driver)
        cleanup.keep_current_window = True

        cleanup.__exit__(None, None, None)

        self.assertEqual(driver.close_called, 0)
        self.assertEqual(driver.switch_to.window_calls, [])


if __name__ == "__main__":
    unittest.main()
