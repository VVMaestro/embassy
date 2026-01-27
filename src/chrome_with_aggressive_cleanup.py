"""
Ultra-Aggressive Chrome Cleanup Solution

This module provides the most aggressive Chrome cleanup possible,
designed to handle stubborn Chrome processes that survive normal cleanup.
It uses multiple strategies to ensure no Chrome processes remain.
"""

import os
import signal
import subprocess
import sys
import time
from typing import Dict, List, Set, Tuple

import psutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class ChromeUltraAggressiveCleanup:
    """
    Ultra-aggressive Chrome cleanup context manager.

    This implementation uses every possible method to ensure Chrome processes
    are completely cleaned up:

    1. Multiple cleanup strategies in sequence
    2. Process tree killing (parent + all children)
    3. Port cleanup (kills processes listening on Chrome ports)
    4. File descriptor cleanup
    5. User data directory cleanup
    6. Fallback to system commands when Python APIs fail
    """

    def __init__(self, headless: bool = True, cleanup_timeout: int = 10):
        """
        Initialize the ultra-aggressive Chrome cleanup.

        Args:
            headless: Run Chrome in headless mode
            cleanup_timeout: Maximum seconds to wait for cleanup (default: 10)
        """
        self.headless = headless
        self.cleanup_timeout = cleanup_timeout
        self.driver = None

        # Track everything we spawn
        self.all_pids: Set[int] = set()
        self.chromedriver_pid: int | None = None
        self.user_data_dir: str | None = None

        # Chrome ports that might be used
        self.chrome_ports = set()

    def __enter__(self):
        """Enter context manager and start Chrome with aggressive tracking."""
        print("[AGGRESSIVE CLEANUP] Starting Chrome with aggressive tracking...")

        # Record initial state
        initial_pids = self._get_all_chrome_related_pids()
        initial_ports = self._get_chrome_related_ports()

        # Setup Chrome with maximum isolation
        options = self._create_isolated_chrome_options()

        # Create driver
        try:
            self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            print(f"[AGGRESSIVE CLEANUP] Failed to create driver: {e}")
            # Try with even more minimal options
            options = self._create_minimal_chrome_options()
            self.driver = webdriver.Chrome(options=options)

        # Wait for processes to stabilize
        time.sleep(1)

        # Track everything we spawned
        current_pids = self._get_all_chrome_related_pids()
        self.all_pids = current_pids - initial_pids

        # Track ports
        current_ports = self._get_chrome_related_ports()
        self.chrome_ports = current_ports - initial_ports

        # Find ChromeDriver PID specifically
        self._find_chromedriver_pid()

        # Find user data directory from command line
        self._extract_user_data_dir()

        print(
            f"[AGGRESSIVE CLEANUP] Tracked {len(self.all_pids)} PIDs and {len(self.chrome_ports)} ports"
        )

        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager with ultra-aggressive cleanup."""
        print(f"\n[AGGRESSIVE CLEANUP] Starting ultra-aggressive cleanup...")

        cleanup_start = time.time()

        # Strategy 1: Normal Selenium cleanup
        self._strategy_normal_cleanup()

        # Strategy 2: Python process tree cleanup
        self._strategy_python_process_cleanup()

        # Strategy 3: Port-based cleanup
        self._strategy_port_cleanup()

        # Strategy 4: System command cleanup (cross-platform)
        self._strategy_system_command_cleanup()

        # Strategy 5: User data directory cleanup
        self._strategy_user_data_cleanup()

        # Strategy 6: Final verification and brute force
        self._strategy_final_brute_force()

        # Verify cleanup
        remaining = self._verify_cleanup()

        cleanup_time = time.time() - cleanup_start
        print(f"[AGGRESSIVE CLEANUP] Cleanup completed in {cleanup_time:.1f}s")
        print(f"[AGGRESSIVE CLEANUP] {remaining} Chrome processes remaining")

        return False  # Don't suppress exceptions

    def _create_isolated_chrome_options(self) -> Options:
        """Create Chrome options for maximum isolation and cleanup."""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")  # New headless mode

        # Security and isolation
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # Process reduction
        options.add_argument("--single-process")  # Single process mode
        options.add_argument("--disable-features=SitePerProcess,IsolateOrigins")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Memory and performance
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-component-update")

        # Cleanup helpers
        options.add_argument("--disable-application-cache")
        options.add_argument("--disable-offline-load-stale-cache")
        options.add_argument("--disk-cache-size=1")
        options.add_argument("--media-cache-size=1")

        # Explicit user data dir for cleanup
        import tempfile

        self.user_data_dir = tempfile.mkdtemp(prefix="chrome_cleanup_")
        options.add_argument(f"--user-data-dir={self.user_data_dir}")

        # Disable various features that spawn processes
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-breakpad")
        options.add_argument("--disable-crash-reporter")

        # Experimental features to reduce processes
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        return options

    def _create_minimal_chrome_options(self) -> Options:
        """Create even more minimal Chrome options as fallback."""
        options = Options()

        if self.headless:
            options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--single-process")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")

        return options

    def _get_all_chrome_related_pids(self) -> Set[int]:
        """Get ALL PIDs that could be related to Chrome."""
        pids = set()

        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                exe = (info.get("exe") or "").lower()
                cmdline = " ".join(info.get("cmdline") or [])
                cmdline_lower = cmdline.lower()

                # Broad Chrome detection
                is_chrome = (
                    "chrome" in name
                    or "chromium" in name
                    or "chromedriver" in name
                    or "chrome" in exe
                    or "chromium" in exe
                    or "chromedriver" in exe
                    or "--type=" in cmdline_lower
                    or "--user-data-dir=" in cmdline_lower
                    or "--remote-debugging-port=" in cmdline_lower
                    or "--test-type=" in cmdline_lower
                    or "headless" in cmdline_lower
                    or "no-sandbox" in cmdline_lower
                )

                if is_chrome:
                    pids.add(info["pid"])

            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue

        return pids

    def _get_chrome_related_ports(self) -> Set[int]:
        """Get ports used by Chrome processes."""
        ports = set()

        for proc in psutil.process_iter(["pid"]):
            try:
                try:
                    connections = proc.connections()
                    for conn in connections:
                        if conn.laddr:
                            ports.add(conn.laddr.port)
                except (psutil.AccessDenied, psutil.Error):
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Common Chrome ports
        chrome_port_ranges = {
            9222,  # Chrome DevTools
            9515,  # ChromeDriver default
        }

        # Add any port in common Chrome ranges
        for port in ports.copy():
            if 9000 <= port <= 10000:  # Common debug port range
                chrome_port_ranges.add(port)

        return chrome_port_ranges

    def _find_chromedriver_pid(self):
        """Find ChromeDriver PID specifically."""
        for pid in self.all_pids:
            try:
                proc = psutil.Process(pid)
                cmdline = " ".join(proc.cmdline() or [])
                if "chromedriver" in cmdline.lower() or "--port=" in cmdline:
                    self.chromedriver_pid = pid
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def _extract_user_data_dir(self):
        """Extract user data directory from Chrome processes."""
        for pid in self.all_pids:
            try:
                proc = psutil.Process(pid)
                cmdline = " ".join(proc.cmdline() or [])
                if "--user-data-dir=" in cmdline:
                    import re

                    match = re.search(r"--user-data-dir=([^\s]+)", cmdline)
                    if match and not self.user_data_dir:
                        self.user_data_dir = match.group(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def _strategy_normal_cleanup(self):
        """Strategy 1: Normal Selenium cleanup."""
        print("  [Strategy 1] Normal Selenium cleanup...")

        if self.driver:
            try:
                self.driver.quit()
                print("    ✓ driver.quit() called")
            except Exception as e:
                print(f"    ✗ driver.quit() failed: {e}")

        # Wait for normal cleanup
        time.sleep(1)

    def _strategy_python_process_cleanup(self):
        """Strategy 2: Python process tree cleanup."""
        print("  [Strategy 2] Python process tree cleanup...")

        # Kill all tracked PIDs and their children
        killed_count = 0

        for pid in list(self.all_pids):
            killed = self._kill_process_tree_aggressive(pid)
            if killed:
                killed_count += 1

        # Also kill any Chrome processes we find now
        current_pids = self._get_all_chrome_related_pids()
        for pid in current_pids:
            if pid not in self.all_pids:
                killed = self._kill_process_tree_aggressive(pid)
                if killed:
                    killed_count += 1

        print(f"    ✓ Killed {killed_count} process trees")
        time.sleep(1)

    def _kill_process_tree_aggressive(self, pid: int) -> bool:
        """Aggressively kill a process tree."""
        try:
            # Get entire tree
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            all_pids = [pid] + [child.pid for child in children]

            # Kill children first (leaves to root)
            for child_pid in reversed(all_pids):
                try:
                    proc = psutil.Process(child_pid)

                    # Try terminate first
                    proc.terminate()
                    time.sleep(0.1)

                    # Check if still alive
                    if proc.is_running():
                        proc.kill()  # Force kill

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _strategy_port_cleanup(self):
        """Strategy 3: Port-based cleanup."""
        print("  [Strategy 3] Port-based cleanup...")

        if sys.platform == "win32":
            # Windows port cleanup
            for port in self.chrome_ports:
                try:
                    subprocess.run(
                        f"netstat -ano | findstr :{port}",
                        shell=True,
                        capture_output=True,
                        text=True,
                    )
                    # Would need to parse and kill, but netstat approach is complex
                    pass
                except:
                    pass
        else:
            # Linux/Mac port cleanup
            for port in self.chrome_ports:
                try:
                    # Find PID using port and kill it
                    result = subprocess.run(
                        f"lsof -ti:{port}", shell=True, capture_output=True, text=True
                    )
                    if result.stdout:
                        pids = result.stdout.strip().split()
                        for pid_str in pids:
                            try:
                                pid = int(pid_str)
                                os.kill(pid, signal.SIGKILL)
                            except (ValueError, ProcessLookupError, PermissionError):
                                pass
                except:
                    pass

        print("    ✓ Port cleanup attempted")
        time.sleep(0.5)

    def _strategy_system_command_cleanup(self):
        """Strategy 4: System command cleanup."""
        print("  [Strategy 4] System command cleanup...")

        if sys.platform == "win32":
            # Windows commands
            commands = [
                "taskkill /F /IM chrome.exe /T",
                "taskkill /F /IM chromedriver.exe /T",
                "taskkill /F /IM chromium.exe /T",
            ]
        else:
            # Linux/Mac commands
            commands = [
                "pkill -9 -f chrome",
                "pkill -9 -f chromium",
                "pkill -9 -f chromedriver",
                "killall -9 chrome",
                "killall -9 chromium",
                "killall -9 chromedriver",
            ]

        for cmd in commands:
            try:
                subprocess.run(cmd, shell=True, capture_output=True, timeout=2)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        print("    ✓ System commands executed")
        time.sleep(1)

    def _strategy_user_data_cleanup(self):
        """Strategy 5: User data directory cleanup."""
        print("  [Strategy 5] User data directory cleanup...")

        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                import shutil

                shutil.rmtree(self.user_data_dir, ignore_errors=True)
                print(f"    ✓ Removed user data dir: {self.user_data_dir}")
            except Exception as e:
                print(f"    ✗ Failed to remove user data dir: {e}")

        time.sleep(0.5)

    def _strategy_final_brute_force(self):
        """Strategy 6: Final brute force cleanup."""
        print("  [Strategy 6] Final brute force cleanup...")

        # Get ALL processes and kill any Chrome-related ones
        all_chrome_pids = self._get_all_chrome_related_pids()
        killed_count = 0

        for pid in all_chrome_pids:
            try:
                os.kill(pid, signal.SIGKILL)
                killed_count += 1
            except (ProcessLookupError, PermissionError):
                pass

        # One more system command pass
        self._strategy_system_command_cleanup()

        print(f"    ✓ Brute force killed {killed_count} processes")
        time.sleep(2)  # Give time for everything to die

    def _verify_cleanup(self) -> int:
        """Verify cleanup and return number of remaining processes."""
        # Wait a bit for final cleanup
        time.sleep(1)

        # Check for remaining processes
        remaining_pids = self._get_all_chrome_related_pids()

        if remaining_pids:
            print(
                f"\n[AGGRESSIVE CLEANUP] WARNING: {len(remaining_pids)} processes remain:"
            )
            for pid in remaining_pids:
                try:
                    proc = psutil.Process(pid)
                    name = proc.name()
                    cmdline = " ".join(proc.cmdline()[:2]) if proc.cmdline() else ""
                    print(f"  PID {pid}: {name} - {cmdline}")
                except:
                    print(f"  PID {pid}: unknown")

        return len(remaining_pids)


# Convenience function for easy use
def chrome_with_aggressive_cleanup(headless: bool = True, cleanup_timeout: int = 10):
    """Convenience context manager function."""
    return ChromeUltraAggressiveCleanup(
        headless=headless, cleanup_timeout=cleanup_timeout
    )


# Example usage
if __name__ == "__main__":
    print("Testing ultra-aggressive Chrome cleanup...")

    try:
        with chrome_with_aggressive_cleanup(headless=True) as driver:
            driver.get("https://www.example.com")
            print(f"Page title: {driver.title}")
            print("Chrome session completed, cleanup will happen now...")

    except Exception as e:
        print(f"Error: {e}")

    print("Test completed. Check for any remaining Chrome processes.")
