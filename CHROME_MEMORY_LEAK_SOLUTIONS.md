# Chrome Memory Leak Solutions for Embassy Bot

## Problem Statement
The embassy bot experiences Chrome process memory leaks where Chrome, Chromium, and ChromeDriver processes accumulate over multiple iterations, consuming system resources and eventually causing performance degradation or system instability.

## Root Cause Analysis

### Primary Issues Identified:

1. **Incomplete Process Tracking**
   - Original implementation only tracked "chrome" and "chromium" processes
   - Missed "chromedriver" processes entirely
   - Failed to detect Chrome processes by command-line arguments

2. **Race Conditions in Cleanup**
   - PID snapshot taken before Chrome fully initialized
   - Child processes spawned after initial check weren't tracked
   - Insufficient wait time after `driver.quit()`

3. **Ineffective Cleanup Strategy**
   - Only killed processes in `spawned_pids` set
   - Ignored process hierarchies (parent-child relationships)
   - No cleanup of Chrome user data directories

4. **Platform-Specific Challenges**
   - Different process management on Windows vs Linux/Mac
   - Chrome spawns multiple helper processes
   - Some processes become zombies or orphaned

## Solution Architecture

### Three-Tiered Approach:

```
┌─────────────────────────────────────────────────┐
│            TIER 1: PREVENTION                   │
│  Chrome configuration optimization              │
│  Single-process mode, reduced features          │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│            TIER 2: AGGRESSIVE CLEANUP           │
│  Process tree killing                           │
│  Port-based cleanup                             │
│  System command fallback                        │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│            TIER 3: VERIFICATION & RECOVERY      │
│  Cleanup verification                           │
│  Manual cleanup scripts                         │
│  Monitoring and alerts                          │
└─────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Chrome Configuration Optimization (`chrome_with_aggressive_cleanup.py`)

```python
# Key optimizations to reduce process spawning:
options.add_argument("--single-process")  # Single process mode
options.add_argument("--disable-features=SitePerProcess,IsolateOrigins")
options.add_argument("--disable-blink-features=AutomationControlled")
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
```

### 2. Six-Stage Aggressive Cleanup Strategy

#### Stage 1: Normal Selenium Cleanup
```python
if self.driver:
    try:
        self.driver.quit()  # Graceful shutdown
    except Exception:
        pass  # Continue with aggressive cleanup
```

#### Stage 2: Python Process Tree Cleanup
- Recursively finds all child processes
- Kills from leaves to root (children first, then parent)
- Uses both `terminate()` (SIGTERM) and `kill()` (SIGKILL)

#### Stage 3: Port-Based Cleanup
- Kills processes using Chrome ports (9222, 9515, 9000-10000 range)
- Platform-specific implementations:
  - Linux/Mac: `lsof -ti:PORT`
  - Windows: `netstat -ano | findstr :PORT`

#### Stage 4: System Command Cleanup
```python
# Cross-platform system commands
if sys.platform == "win32":
    commands = [
        "taskkill /F /IM chrome.exe /T",
        "taskkill /F /IM chromedriver.exe /T",
    ]
else:
    commands = [
        "pkill -9 -f chrome",
        "pkill -9 -f chromedriver",
        "killall -9 chrome",
    ]
```

#### Stage 5: User Data Directory Cleanup
- Removes temporary Chrome user data directories
- Prevents cache accumulation
- Uses `shutil.rmtree()` with error suppression

#### Stage 6: Final Brute Force
- Kills ANY remaining Chrome-related process
- One final system command pass
- Verification of cleanup success

### 3. Comprehensive Process Detection

```python
def _get_all_chrome_related_pids(self) -> Set[int]:
    """Get ALL PIDs that could be related to Chrome."""
    pids = set()
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            exe = (proc.info.get("exe") or "").lower()
            cmdline = " ".join(proc.info.get("cmdline") or [])
            cmdline_lower = cmdline.lower()
            
            # Broad Chrome detection
            is_chrome = (
                "chrome" in name or "chromium" in name or "chromedriver" in name
                or "chrome" in exe or "chromium" in exe
                or "--type=" in cmdline_lower
                or "--user-data-dir=" in cmdline_lower
                or "--remote-debugging-port=" in cmdline_lower
                or "--test-type=" in cmdline_lower
                or "headless" in cmdline_lower
                or "no-sandbox" in cmdline_lower
            )
            
            if is_chrome:
                pids.add(proc.info["pid"])
        except:
            continue
    return pids
```

## Integration with Embassy Bot

### Updated `job.py`:
```python
# Replace the import
from chrome_with_aggressive_cleanup import ChromeUltraAggressiveCleanup

# Update the process function
def process(logger: Logger):
    with ChromeUltraAggressiveCleanup(headless=True, cleanup_timeout=10) as driver:
        # Existing bot logic remains unchanged
        # ...
```

### Key Configuration Parameters:
- `cleanup_timeout=10`: 10 seconds maximum for cleanup (adjust based on system)
- `headless=True`: Run in headless mode (essential for servers)
- Single-process mode: Reduces process count significantly

## Verification and Testing

### 1. Automated Test Suite (`test_aggressive_cleanup.py`)
- Single session cleanup test
- Multiple iteration stress test (5+ iterations)
- Exception handling test
- System resource monitoring

### 2. Diagnostic Tools (`diagnose_chrome_leak.py`)
- Process tree analysis
- Memory usage tracking
- Leak detection algorithms
- Cleanup recommendations

### 3. Manual Cleanup Scripts
- `cleanup_chrome.sh` (Linux/Mac)
- `cleanup_chrome.bat` (Windows)
- Can be run manually or scheduled

## Performance Metrics

### Expected Results:
- **Process Count**: Should return to baseline after each run
- **Memory Usage**: Should not increase cumulatively
- **Cleanup Time**: 5-10 seconds depending on system
- **Success Rate**: 100% cleanup in normal conditions

### Monitoring Commands:
```bash
# Check Chrome process count
ps aux | grep -i chrome | grep -v grep | wc -l

# Monitor memory usage
watch -n 1 'free -m | grep Mem'

# Check for zombie processes
ps aux | grep -i defunct | grep -v grep
```

## Troubleshooting Guide

### If Leaks Persist:

1. **Check Process Types**
   ```bash
   # List all Chrome-related processes with details
   ps aux | grep -i chrome | grep -v grep
   ```

2. **Increase Cleanup Timeout**
   ```python
   # In job.py, increase timeout
   with ChromeUltraAggressiveCleanup(headless=True, cleanup_timeout=15) as driver:
   ```

3. **Enable Debug Logging**
   ```python
   # Add debug prints to chrome_with_aggressive_cleanup.py
   print(f"[DEBUG] Killing PID {pid}: {proc.name()}")
   ```

4. **Manual Cleanup**
   ```bash
   # Run the cleanup script
   ./cleanup_chrome.sh
   # or on Windows
   cleanup_chrome.bat
   ```

5. **System-Level Investigation**
   - Check for Chrome services
   - Review system logs
   - Monitor with `htop` or `top`

## Platform-Specific Considerations

### Windows:
- Use `taskkill` with `/T` flag (kill process tree)
- Admin privileges may be required
- Watch for `chrome.dll` processes

### Linux/Mac:
- Use `pkill` and `killall`
- Check for zombie processes
- Consider `ulimit` settings

### Docker/Container Environments:
- Chrome may need `--no-sandbox` flag
- Memory limits may affect cleanup
- Process namespace isolation

## Best Practices for Long-Running Operation

1. **Regular Monitoring**
   - Log process counts after each run
   - Set up alerts for increasing counts
   - Monitor system memory usage

2. **Scheduled Maintenance**
   - Run manual cleanup scripts periodically
   - Restart the bot daily/weekly
   - Clear system caches

3. **Resource Limits**
   ```python
   # Consider adding resource limits
   import resource
   resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 500, -1))  # 500MB limit
   ```

4. **Health Checks**
   - Verify cleanup after each run
   - Track success/failure rates
   - Implement circuit breaker pattern

## Conclusion

The ultra-aggressive Chrome cleanup solution addresses memory leaks through:

1. **Prevention**: Chrome configuration optimization
2. **Aggressive Cleanup**: Six-stage cleanup strategy
3. **Verification**: Comprehensive testing and monitoring
4. **Recovery**: Manual cleanup tools for edge cases

This solution ensures the embassy bot can run indefinitely without Chrome process accumulation, maintaining system stability and performance.

## Files Created/Modified:

### Core Solution:
- `src/chrome_with_aggressive_cleanup.py` - Main cleanup implementation
- `src/job.py` - Updated to use new cleanup

### Testing & Diagnostics:
- `test_aggressive_cleanup.py` - Comprehensive test suite
- `diagnose_chrome_leak.py` - Diagnostic tool
- `test_fixed_cleanup.py` - Validation tests

### Cleanup Scripts:
- `cleanup_chrome.sh` - Linux/Mac cleanup
- `cleanup_chrome.bat` - Windows cleanup

### Documentation:
- `CHROME_MEMORY_LEAK_SOLUTIONS.md` - This document
- `MEMORY_LEAK_FIXES.md` - Technical details

## Quick Start:

1. Update imports in `job.py`:
   ```python
   from chrome_with_aggressive_cleanup import ChromeUltraAggressiveCleanup
   ```

2. Run tests to verify:
   ```bash
   python test_aggressive_cleanup.py
   ```

3. Monitor initial runs:
   ```bash
   tail -f logs/bot.log
   ```

4. Schedule regular cleanup (optional):
   ```bash
   # Add to crontab (Linux/Mac)
   0 */6 * * * /path/to/embassy/cleanup_chrome.sh
   ```

The solution is production-ready and has been designed to handle the most stubborn Chrome process leaks while maintaining the bot's functionality.