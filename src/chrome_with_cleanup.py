import os
import signal
import time
from logging import Logger

import psutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class ChromeWithFullCleanup:
    def __init__(self, logger: Logger, headless=True, cleanup_timeout=10):
        self.headless = headless
        self.logger = logger
        self.driver = None
        self.cleanup_timeout = cleanup_timeout
        self.chrome_pids = set()  # Track Chrome PIDs

    def __enter__(self):
        # Get existing Chrome PIDs before starting
        self.chrome_pids = self._get_chrome_pids()

        # Setup Chrome options
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # Add these to help with cleanup
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")

        # Create driver
        self.driver = webdriver.Chrome(options=options)

        # Get new PIDs created by this instance
        current_pids = self._get_chrome_pids()
        self.spawned_pids = current_pids - self.chrome_pids

        print(f"Spawned {len(self.spawned_pids)} Chrome processes")
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        cleanup_success = False

        # Step 1: Normal Selenium cleanup
        if self.driver:
            try:
                self.driver.quit()  # Graceful shutdown
            except:
                self.logger.error("Failed to gracefully shutdown Chrome")

        # Step 2: Wait a bit for processes to terminate
        cleanup_success = self._wait_for_process_cleanup()

        if not cleanup_success:
            self.logger.info("Some Chrome processes still running")

        return False  # Don't suppress exceptions

    def _get_chrome_pids(self):
        """Get all Chrome/Chromium process IDs"""
        pids = set()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info["name"] or ""
                if "chrome" in name.lower() or "chromium" in name.lower():
                    pids.add(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids

    def _wait_for_process_cleanup(self) -> bool:
        """Wait for all spawned processes to terminate."""
        start_time = time.time()

        while time.time() - start_time < self.cleanup_timeout:
            # Check if any spawned processes are still running
            running_pids = []

            for pid in self.spawned_pids:
                try:
                    psutil.Process(pid)
                    running_pids.append(pid)
                except psutil.NoSuchProcess:
                    pass  # Process is already dead

            # If no processes are running, cleanup is complete
            if not running_pids:
                return True

            # Wait a bit before checking again
            time.sleep(0.2)

        # Timeout reached, some processes still running
        return False
