#!/bin/bash

# Chrome Process Cleanup Script
# This script aggressively cleans up Chrome, Chromium, and ChromeDriver processes
# that might be left running after bot execution.

set -e

echo "========================================="
echo "Chrome Process Cleanup Script"
echo "========================================="
echo "Started at: $(date)"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo "=== $1 ==="
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to kill processes by name
kill_by_name() {
    local name=$1
    local signal=${2:-9}

    print_section "Killing $name processes"

    # Try different methods based on platform
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        # Linux/Mac
        echo "Using pkill for $name..."
        if pkill -$signal -f "$name" 2>/dev/null; then
            echo "✓ pkill successful for $name"
        else
            echo "  No $name processes found with pkill"
        fi

        echo "Using killall for $name..."
        if killall -$signal "$name" 2>/dev/null; then
            echo "✓ killall successful for $name"
        else
            echo "  No $name processes found with killall"
        fi

    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows (Git Bash/Cygwin)
        echo "Using taskkill for $name..."
        if taskkill //F //IM "$name" //T 2>/dev/null; then
            echo "✓ taskkill successful for $name"
        else
            echo "  No $name processes found with taskkill"
        fi
    fi
}

# Function to kill processes by port
kill_by_port() {
    local port=$1

    print_section "Killing processes on port $port"

    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        # Linux/Mac
        if command_exists lsof; then
            echo "Using lsof to find processes on port $port..."
            PIDS=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$PIDS" ]; then
                echo "Found PIDs: $PIDS"
                for PID in $PIDS; do
                    echo "  Killing PID $PID..."
                    kill -9 $PID 2>/dev/null && echo "    ✓ Killed" || echo "    ✗ Failed"
                done
            else
                echo "  No processes found on port $port"
            fi
        else
            echo "  lsof not available, skipping port check"
        fi
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        echo "Checking port $port on Windows..."
        netstat -ano | grep ":$port" | awk '{print $5}' | while read PID; do
            if [ -n "$PID" ]; then
                echo "  Killing PID $PID..."
                taskkill //F //PID $PID 2>/dev/null && echo "    ✓ Killed" || echo "    ✗ Failed"
            fi
        done
    fi
}

# Function to list remaining Chrome processes
list_chrome_processes() {
    print_section "Listing Chrome-related processes"

    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        # Linux/Mac
        echo "Processes containing 'chrome':"
        ps aux | grep -i chrome | grep -v grep || echo "  None found"

        echo ""
        echo "Processes containing 'chromium':"
        ps aux | grep -i chromium | grep -v grep || echo "  None found"

        echo ""
        echo "Processes containing 'chromedriver':"
        ps aux | grep -i chromedriver | grep -v grep || echo "  None found"

    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        echo "Chrome processes:"
        tasklist //FI "IMAGENAME eq chrome.exe" 2>/dev/null || echo "  None found"

        echo ""
        echo "Chromium processes:"
        tasklist //FI "IMAGENAME eq chromium.exe" 2>/dev/null || echo "  None found"

        echo ""
        echo "ChromeDriver processes:"
        tasklist //FI "IMAGENAME eq chromedriver.exe" 2>/dev/null || echo "  None found"
    fi
}

# Function to clean up Chrome user data directories
clean_user_data_dirs() {
    print_section "Cleaning Chrome user data directories"

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "Cleaning Linux Chrome cache directories..."
        rm -rf /tmp/.com.google.Chrome.* 2>/dev/null && echo "✓ Cleaned /tmp/.com.google.Chrome.*" || echo "  No /tmp Chrome cache found"
        rm -rf /tmp/.org.chromium.Chromium.* 2>/dev/null && echo "✓ Cleaned /tmp/.org.chromium.Chromium.*" || echo "  No /tmp Chromium cache found"

    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Mac
        echo "Cleaning Mac Chrome cache directories..."
        rm -rf /tmp/.com.google.Chrome.* 2>/dev/null && echo "✓ Cleaned /tmp/.com.google.Chrome.*" || echo "  No /tmp Chrome cache found"
        rm -rf /tmp/.org.chromium.Chromium.* 2>/dev/null && echo "✓ Cleaned /tmp/.org.chromium.Chromium.*" || echo "  No /tmp Chromium cache found"

    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        echo "Note: Windows Chrome cache cleanup requires admin privileges"
        echo "Skipping Windows cache cleanup for safety"
    fi

    # Clean up any temporary directories created by our bot
    echo "Cleaning bot temporary directories..."
    find /tmp -name "chrome_cleanup_*" -type d -exec rm -rf {} \; 2>/dev/null && echo "✓ Cleaned bot temp dirs" || echo "  No bot temp dirs found"
}

# Main cleanup sequence
main() {
    echo "Starting aggressive Chrome cleanup..."
    echo "Platform: $OSTYPE"
    echo ""

    # List processes before cleanup
    list_chrome_processes

    # Kill processes by name
    kill_by_name "chrome"
    kill_by_name "chromium"
    kill_by_name "chromedriver"

    # Kill processes on common Chrome ports
    kill_by_port 9222  # Chrome DevTools
    kill_by_port 9515  # ChromeDriver default

    # Additional Chrome-related process names
    print_section "Killing additional Chrome-related processes"

    # Try to kill any process with chrome in command line
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Killing any process with '--user-data-dir' in command line..."
        ps aux | grep -i "user-data-dir" | grep -v grep | awk '{print $2}' | while read PID; do
            echo "  Killing PID $PID..."
            kill -9 $PID 2>/dev/null && echo "    ✓ Killed" || echo "    ✗ Failed"
        done

        echo "Killing any process with '--remote-debugging-port' in command line..."
        ps aux | grep -i "remote-debugging-port" | grep -v grep | awk '{print $2}' | while read PID; do
            echo "  Killing PID $PID..."
            kill -9 $PID 2>/dev/null && echo "    ✓ Killed" || echo "    ✗ Failed"
        done
    fi

    # Clean up user data directories
    clean_user_data_dirs

    # Wait a bit for processes to die
    print_section "Finalizing cleanup"
    echo "Waiting 2 seconds for processes to terminate..."
    sleep 2

    # List processes after cleanup
    list_chrome_processes

    # Final check
    print_section "Cleanup Summary"
    echo "Cleanup completed at: $(date)"
    echo ""
    echo "If Chrome processes are still running, you may need to:"
    echo "1. Run this script as administrator/root"
    echo "2. Manually check for zombie processes"
    echo "3. Reboot your system if problems persist"
    echo ""
    echo "For the embassy bot, ensure you're using ChromeUltraAggressiveCleanup"
    echo "in your Python code for automatic cleanup."
}

# Run main function
main

exit 0
