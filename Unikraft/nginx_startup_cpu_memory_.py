import subprocess
import psutil
import time
import os
import signal
import csv
import socket

LOG_DIR = "metrics"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "unikraft_nginx_metrics.csv")
TEED_LOG_FILE = os.path.join(LOG_DIR, "unikraft_full_output.log")
full_log_lines = []

def buffered_print(message):
    print(message)
    full_log_lines.append(message)

def tee_print(message):
    print(message)
    with open(TEED_LOG_FILE, "a") as f:
        f.write(message + "\n")

def find_qemu_proc_by_port(port="8080"):
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.name().startswith("qemu-system") and any(f"hostfwd=tcp::{port}-" in arg for arg in proc.cmdline()):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def wait_for_nginx_ready(host="127.0.0.1", port=8080, timeout=30):
    """waiting for NGinx to become ready by checking port 8080."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1) as sock:
                sock.send(b"HEAD / HTTP/1.1\r\nHost: localhost\r\n\r\n")
                response = sock.recv(1024).decode('utf-8')
                if "HTTP/1.1 200 OK" in response:
                    return time.time() - start
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.1)
    raise TimeoutError("NGINX did not become ready in time.")

def find_qemu_proc(timeout=10):
    qemu_proc = None
    deadline = time.time() + timeout
    while time.time() < deadline: 
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']): 
            try:
                if 'qemu-system-x86_64' in proc.info['name']:
                    if any('unikraft' in arg or '.img' in arg for arg in proc.info['cmdline']):
                        return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        time.sleep(0.5)
    raise RuntimeError("QEMU process not found within timeout.")

def monitor_process(proc, start_time, nginx_ready_trigger="interface is up"):
    """Monitoring the QEMU process and looking for nginx logs"""
    log_lines = []
    csv_rows = []
    nginx_started = None
    nginx_stopped = None

    try:
        for line in iter(proc.stdout.readline, b''):
            decoded = line.decode("utf-8", errors="ignore").strip()
            log_lines.append(decoded)
            now = time.time()
            elapsed = round(now - start_time, 3)

            if nginx_ready_trigger.lower() in decoded.lower() and nginx_started is None:
                nginx_started = now
                buffered_print(f"NGINX Started at +{elapsed:.2f}s: {decoded}")
                csv_rows.append([elapsed, "", "", "nginx_started"])

            if proc.poll() is None:
                try:
                    stats = proc_qemu.cpu_percent(interval=0.1), proc_qemu.memory_info().rss // 1024
                    csv_rows.append([elapsed, stats[0], stats[1], "running"])
                except Exception:
                    pass

    except KeyboardInterrupt:
        nginx_stopped = time.time()
        elapsed = round(nginx_stopped - start_time, 3)
        buffered_print(f"NGINX Stopped via Ctrl+C at +{elapsed:.2f}s")
        csv_rows.append([elapsed, "", "", "nginx_stopped"])

    finally:
        proc.stdout.close()

    return csv_rows, nginx_started, nginx_stopped

def run_and_monitor_nginx():
    buffered_print("Starting the Unikraft unikernel")
    start_time = time.time()

    kraft_proc = subprocess.Popen(
        ["kraft", "run", "--log-level", "debug", "--log-type", "basic", "-p", "8080:80", "--plat", "qemu", "--arch", "x86_64", "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    buffered_print("Waiting for QEMU to start...")
    time.sleep(3)  # giving QEMU time to spawn

    qemu_proc = find_qemu_proc_by_port("8080")
    if not qemu_proc:
        print("Could not find the QEMU process.")
        kraft_proc.kill()
        return

    buffered_print(f"QEMU PID: {qemu_proc.pid}")
    # print_process_tree(kraft_proc.pid)

    global proc_qemu
    proc_qemu = qemu_proc
    print("CMD:", ' '.join(qemu_proc.cmdline()))    

    # Monitor the process and collect metrics
    try:
        nginx_ready_time = wait_for_nginx_ready(host="127.0.0.1", port=8080, timeout=30)
        buffered_print(f"NGINX ready in {nginx_ready_time:.3f} seconds")
    except TimeoutError as e:
        buffered_print(f"Error: {e}")

    # Monitoring the kraft process
    csv_rows, nginx_start, nginx_end = monitor_process(kraft_proc, start_time)

    kraft_proc.wait()
    end_time = time.time()

    with open(LOG_FILE, "a", newline='') as log_file:
        csv_writer = csv.writer(log_file)
        csv_writer.writerow(["Time Elapsed", "CPU (%)", "Memory (KB)", "Event"])
        csv_writer.writerows(csv_rows)

    buffered_print("QEMU ended")
    buffered_print(f"Boot Time: {round(nginx_start - start_time, 3) if nginx_start else 'N/A'}s")
    buffered_print(f"Total Runtime: {round(end_time - start_time, 3)}s")

    if nginx_end:
        buffered_print(f"NGINX lifetime: {round(nginx_end - nginx_start, 3)}s")

    with open(TEED_LOG_FILE, "a") as log_file:
        for line in full_log_lines:
            log_file.write(line + "\n")

if __name__ == "__main__":
    run_and_monitor_nginx()
