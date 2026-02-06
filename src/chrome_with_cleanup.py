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

    def __enter__(self):
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Normal Selenium cleanup
        if self.driver:
            try:
                self.driver.close()
            except:
                self.logger.error("Failed to close Chrome window")
