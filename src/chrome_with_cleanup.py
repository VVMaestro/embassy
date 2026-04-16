from logging import Logger

from selenium.webdriver.chrome.webdriver import WebDriver


class ChromeWithFullCleanup:
    def __init__(
        self,
        logger: Logger,
        driver: WebDriver,
    ):
        self.logger = logger
        self.driver = driver
        self.original_window_handle = self.driver.current_window_handle
        self.keep_current_window = False

    def __enter__(self):
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.logger.info("Windows count: %s", len(self.driver.window_handles))

            if self.keep_current_window:
                self.logger.info("Keeping current Chrome window open for manual finish")
                return

            self.driver.close()
            self.driver.switch_to.window(self.original_window_handle)
        except Exception as error:
            self.logger.error("Failed to close Chrome window: %s", error)
