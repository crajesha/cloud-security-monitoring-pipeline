#!/usr/bin/env python3
import threading
import time
import urllib.request
import urllib.parse
import json
import sys
import hashlib
import os

# Target configuration
TARGET_HOST = os.getenv("TARGET_HOST", "http://localhost:5000")
STOP_EVENT = threading.Event()

def http_flood_worker():
    """Worker that rapidly generates HTTP GET requests to simulate a DoS attack on the API."""
    url = f"{TARGET_HOST}/api/v1/resource"
    headers = {"User-Agent": "SecurityPipelineTest-DoS-Simulator/1.0"}
    
    print(f"[*] HTTP Flood Worker started pointing to: {url}")
    
    while not STOP_EVENT.is_set():
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=2) as response:
                response.read() # Read response body to release connection
        except Exception:
            # Silence connection errors during heavy flooding to prevent terminal spam
            pass
        time.sleep(0.001)  # Minimal sleep to allow resource yielding

def auth_brute_force_worker():
    """Worker that simulates credential stuffing/brute force on the auth endpoint."""
    url = f"{TARGET_HOST}/api/v1/auth"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SecurityPipelineTest-BruteForce-Simulator/1.0"
    }
    
    print(f"[*] SSH/App Brute Force Worker started pointing to: {url}")
    
    while not STOP_EVENT.is_set():
        data = json.dumps({"username": "admin", "password": f"password_{time.time()}"}).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=2) as response:
                response.read()
        except urllib.error.HTTPError as e:
            # 401 Unauthorized is expected, which is what we want to record!
            pass
        except Exception:
            pass
        time.sleep(0.1)  # Rate of brute force attempts

def cpu_stress_worker():
    """Worker that spikes CPU utilization to >80% by performing intensive cryptographic computations."""
    print("[*] Host CPU Stress worker started.")
    while not STOP_EVENT.is_set():
        # High CPU density block
        for _ in range(50000):
            hashlib.sha256(b"security_telemetry_monitoring_pipeline_stress_test").hexdigest()
        # Tiny sleep to allow context switching
        time.sleep(0.01)

def run_simulation(duration, attacks):
    """Orchestrates the selected simulations for a set duration."""
    threads = []
    
    print("="*60)
    print("   AUTOMATED SECURITY PIPELINE TELEMETRY SIMULATOR   ")
    print("="*60)
    print(f"Target system: {TARGET_HOST}")
    print(f"Test duration: {duration} seconds")
    print(f"Active stress targets: {', '.join(attacks)}")
    print("="*60)
    
    # Launch workers
    if "dos" in attacks:
        # Spawn multiple HTTP threads for flood
        for i in range(8):
            t = threading.Thread(target=http_flood_worker, name=f"HTTPFlood-{i}")
            t.daemon = True
            t.start()
            threads.append(t)
            
    if "brute" in attacks:
        for i in range(3):
            t = threading.Thread(target=auth_brute_force_worker, name=f"BruteForce-{i}")
            t.daemon = True
            t.start()
            threads.append(t)
            
    if "cpu" in attacks:
        # Spawn CPU stress threads equal to half of cores or minimum of 4
        num_cpu_threads = max(4, os.cpu_count() or 4)
        for i in range(num_cpu_threads):
            t = threading.Thread(target=cpu_stress_worker, name=f"CPUStress-{i}")
            t.daemon = True
            t.start()
            threads.append(t)

    # Count down timer
    try:
        for remaining in range(duration, 0, -1):
            sys.stdout.write(f"\rSimulation running... {remaining}s remaining. Press Ctrl+C to terminate.")
            sys.stdout.flush()
            time.sleep(1)
        print("\n\n[*] Simulation duration completed.")
    except KeyboardInterrupt:
        print("\n\n[!] Simulation interrupted by user.")
    finally:
        STOP_EVENT.set()
        print("[*] Stopping all simulation worker threads...")
        # Give threads time to close
        time.sleep(2)
        print("[*] Cleanup complete. Simulation stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="InfoSec Monitoring Telemetry Simulator")
    parser.add_argument("--host", default=TARGET_HOST, help="Target Flask API Host url")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--attack", choices=["dos", "brute", "cpu", "all"], default="all",
                        help="Choose specific attack scenario to test alerts")
                        
    args = parser.parse_args()
    TARGET_HOST = args.host
    
    if args.attack == "all":
        scenarios = ["dos", "brute", "cpu"]
    else:
        scenarios = [args.attack]
        
    run_simulation(args.duration, scenarios)
