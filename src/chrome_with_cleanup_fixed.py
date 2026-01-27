import os
import signal
import time
from typing import List, Set

import psutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class ChromeWithProperCleanup:
    """
    Context manager for Chrome WebDriver with proper process cleanup.

    Key improvements over the original:
    1. Tracks ChromeDriver process separately
    2. Uses process tree killing to get all child processes
    3. Better timing and retry logic for cleanup
    4. More accurate PID tracking
    5. Configurable cleanup behavior
    """

    def __init__(self, headless: bool = True, cleanup_timeout: int = 5):
        """
        Initialize the Chrome cleanup context manager.

        Args:
            headless: Run Chrome in headless mode
            cleanup_timeout: Maximum seconds to wait for process cleanup
        """
        self.headless = headless
        self.cleanup_timeout = cleanup_timeout
        self.driver = None

        # Track all processes we spawn
        self.spawned_pids: Set[int] = set()
        # Track the main ChromeDriver PID separately
        self.chromedriver_pid: int | None = None

    def __enter__(self):
        """Enter the context manager and start Chrome."""
        # Get existing Chrome/Chromium/ChromeDriver PIDs before starting
        existing_pids = self._get_all_chrome_related_pids()

        # Setup Chrome options for better cleanup
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # Add arguments to reduce process spawning and improve cleanup
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        options.add_argument("--disable-component-update")

        # Create the driver
        self.driver = webdriver.Chrome(options=options)

        # Get the ChromeDriver service process
        try:
            # Selenium 4 stores the service in driver.service
            if hasattr(self.driver, "service") and self.driver.service:
                self.chromedriver_pid = self.driver.service.process.pid
                self.spawned_pids.add(self.chromedriver_pid)
        except (AttributeError, ProcessLookupError):
            pass

        # Wait a bit for Chrome processes to spawn, then track them
        time.sleep(0.5)

        # Get all Chrome-related processes that were spawned
        current_pids = self._get_all_chrome_related_pids()
        self.spawned_pids.update(current_pids - existing_pids)

        # If we couldn't get ChromeDriver PID directly, try to find it
        if not self.chromedriver_pid:
            self._find_and_track_chromedriver()

        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and clean up all processes."""
        cleanup_success = False

        try:
            # Step 1: Try graceful shutdown via Selenium
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass  # Driver might already be closed

            # Step 2: Wait for processes to terminate gracefully
            cleanup_success = self._wait_for_process_cleanup()

            # Step 3: If graceful cleanup failed, force kill
            if not cleanup_success:
                self._force_kill_process_tree()

            # Step 4: Final verification
            self._verify_cleanup()

        finally:
            # Ensure driver reference is cleared
            self.driver = None

        return False  # Don't suppress exceptions

    def _get_all_chrome_related_pids(self) -> Set[int]:
        """Get all PIDs related to Chrome/Chromium/ChromeDriver."""
        pids = set()

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = proc.info["name"] or ""
                cmdline = " ".join(proc.info["cmdline"] or [])

                # Check for various Chrome-related processes
                is_chrome = any(
                    keyword in name.lower() for keyword in ["chrome", "chromium"]
                )

                # Check for ChromeDriver (could be named differently)
                is_chromedriver = (
                    "chromedriver" in name.lower()
                    or "chromedriver" in cmdline.lower()
                    or "--port="
                    in cmdline  # ChromeDriver typically has a port argument
                )

                if is_chrome or is_chromedriver:
                    pids.add(proc.info["pid"])

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return pids

    def _find_and_track_chromedriver(self):
        """Find and track the ChromeDriver process if not already tracked."""
        for proc in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])

                # Look for ChromeDriver process
                if "chromedriver" in proc.info["name"].lower() or "--port=" in cmdline:
                    pid = proc.info["pid"]
                    self.chromedriver_pid = pid
                    self.spawned_pids.add(pid)
                    break

            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue

    def _get_process_tree(self, pid: int) -> List[int]:
        """Get all PIDs in the process tree starting from the given PID."""
        tree_pids = []

        try:
            # Get the process
            proc = psutil.Process(pid)

            # Add current process
            tree_pids.append(pid)

            # Recursively add all children
            for child in proc.children(recursive=True):
                tree_pids.append(child.pid)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return tree_pids

    def _kill_process_tree(self, pid: int, force: bool = False):
        """Kill a process and all its children."""
        try:
            # Get the entire process tree
            tree_pids = self._get_process_tree(pid)

            # Kill from leaves to root (children first, then parent)
            for tree_pid in reversed(tree_pids):
                try:
                    proc = psutil.Process(tree_pid)

                    if force:
                        proc.kill()  # SIGKILL
                    else:
                        proc.terminate()  # SIGTERM

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

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

    def _force_kill_process_tree(self):
        """Force kill all processes we spawned and their children."""
        # Create a copy of spawned PIDs since we'll be modifying the set
        pids_to_kill = set(self.spawned_pids)

        # Also include any Chrome-related processes that might have been missed
        all_chrome_pids = self._get_all_chrome_related_pids()
        pids_to_kill.update(all_chrome_pids)

        # Kill each process tree
        for pid in pids_to_kill:
            self._kill_process_tree(pid, force=True)

        # Wait a bit for kills to take effect
        time.sleep(1)

        # Clear spawned PIDs since we've killed everything
        self.spawned_pids.clear()

    def _verify_cleanup(self):
        """Verify that all Chrome-related processes are gone."""
        remaining_pids = self._get_all_chrome_related_pids()

        if remaining_pids:
            # Try one more time to kill any remaining processes
            for pid in remaining_pids:
                try:
                    psutil.Process(pid).kill()
                except:
                    pass

            # Wait a bit
            time.sleep(0.5)

            # Check again
            remaining_pids = self._get_all_chrome_related_pids()

            if remaining_pids:
                # Log warning but don't raise exception
                print(
                    f"Warning: {len(remaining_pids)} Chrome-related processes still running after cleanup"
                )
                for pid in remaining_pids:
                    try:
                        proc = psutil.Process(pid)
                        print(f"  PID {pid}: {proc.name()}")
                    except:
                        print(f"  PID {pid}: unknown")
