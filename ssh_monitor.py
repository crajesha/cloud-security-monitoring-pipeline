#!/usr/bin/env python3
import os
import re
import time
import sys

# Standard paths to search for failed logins on AWS EC2 or local mock environments
LOG_PATHS = [
    "/var/log/auth.log",      # Debian/Ubuntu
    "/var/log/secure",        # RHEL/CentOS/Amazon Linux/Fedora
    "./mock_auth.log"         # Local fallback mock file for non-Linux or testing environments
]

# Write metrics path - typically mapped to the node_exporter's textfile collector directory
PROM_FILE_PATH = os.getenv("PROM_FILE_PATH", "/var/lib/node_exporter/ssh_failures.prom")

# Regular expression to catch failed login patterns
FAILED_SSH_PATTERNS = [
    re.compile(r"Failed password for invalid user (.+) from (.+) port"),
    re.compile(r"Failed password for (.+) from (.+) port"),
    re.compile(r"Connection closed by authenticating user (.+) (.+) port"),
    # General match fallback
    re.compile(r"Failed password")
]

def get_active_log_path():
    """Locates the system log or sets up a mock log if none exists."""
    for path in LOG_PATHS:
        if os.path.exists(path):
            return path
    
    # Fallback to local mock file for non-linux systems (like Windows or Mac development environment)
    mock_path = "./mock_auth.log"
    if not os.path.exists(mock_path):
        with open(mock_path, "w") as f:
            f.write("System log mock initialized. Log simulation active.\n")
    return mock_path

def count_failed_logins(log_path):
    """Parses log file to count failed login attempts."""
    count = 0
    try:
        with open(log_path, "r", errors="ignore") as f:
            for line in f:
                if any(pattern.search(line) for pattern in FAILED_SSH_PATTERNS):
                    count += 1
    except PermissionError:
        print(f"[ERROR] Permission Denied: Cannot read {log_path}. Sudo privileges required.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Reading {log_path}: {e}", file=sys.stderr)
        return None
    return count

def write_prometheus_metric(count):
    """Writes the metrics to the prometheus textfile collector format safely using an atomic temp file rename."""
    if count is None:
        return
    try:
        dir_name = os.path.dirname(PROM_FILE_PATH)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        temp_file = PROM_FILE_PATH + ".tmp"
        with open(temp_file, "w") as f:
            f.write("# HELP node_failed_ssh_logins_total Total failed SSH login attempts recorded on host.\n")
            f.write("# TYPE node_failed_ssh_logins_total counter\n")
            f.write(f"node_failed_ssh_logins_total {count}\n")
            
        # Atomic exchange to prevent scraper reading partially written file
        os.replace(temp_file, PROM_FILE_PATH)
    except Exception as e:
        print(f"[ERROR] Writing metrics: {e}", file=sys.stderr)

def main():
    log_path = get_active_log_path()
    print(f"[*] Started SSH Failures Monitor Daemon.")
    print(f"[*] Target Log: {log_path}")
    print(f"[*] Target Prometheus File: {PROM_FILE_PATH}")
    
    is_mock = (log_path == "./mock_auth.log")
    if is_mock:
        print("[!] Running in mock mode. Will append mock failures to trigger metrics.")
        
    last_count = -1
    mock_timer = time.time()
    
    while True:
        # If in mock mode, append a mock login failure every 12 seconds
        if is_mock and (time.time() - mock_timer) > 12:
            try:
                with open(log_path, "a") as f:
                    f.write(f"Jun  5 14:10:22 debian sshd[4012]: Failed password for invalid user admin from 198.51.100.12 port 38472 ssh2\n")
                mock_timer = time.time()
            except Exception as e:
                print(f"[ERROR] Mock write: {e}")

        current_count = count_failed_logins(log_path)
        if current_count is not None and current_count != last_count:
            write_prometheus_metric(current_count)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exposing failed login count: {current_count}")
            last_count = current_count
            
        time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] SSH Monitor stopped.")
        sys.exit(0)
