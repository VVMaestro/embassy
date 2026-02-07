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

    def __enter__(self):
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Windows count: %s", len(self.driver.window_handles))

        try:
            self.driver.close()
            self.driver.switch_to.window(self.original_window_handle)
        except:
            self.logger.error("Failed to close Chrome window")
