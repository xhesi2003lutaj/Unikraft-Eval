import subprocess
import psutil
import time
import os
import csv
import socket
import threading
import signal

LOG_DIR = "metrics"
os.makedirs(LOG_DIR, exist_ok=True)
METRICS_FILE = os.path.join(LOG_DIR, "unikraft_nginx_metrics.csv")
TEED_LOG_FILE = os.path.join(LOG_DIR, "nginx_full_output.log")
CPU_LOG_FILE = os.path.join(LOG_DIR, "cpu_usage_unikraft.log")

start_time = None
full_log_lines = []

def buffered_print(message):
    print(message)
    full_log_lines.append(message)

def tee_print_all():
    with open(TEED_LOG_FILE, "a") as f:
        for line in full_log_lines:
            f.write(line + "\n")

def find_qemu_proc(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.name().startswith("qemu-system") and "8080" in ' '.join(proc.cmdline()):
                    print("QEMU process found")
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        time.sleep(0.2)
    return None

def wait_for_nginx_ready(host="localhost", port=8080, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return time.time()
        except (OSError, ConnectionRefusedError):
            time.sleep(0.1)
    return None

def monitor_resource_usage_live(proc, usage_log, stop_event, interval=1):
    proc.cpu_percent(interval=None)  # warm-up call
    log_lines = ["Time Elapsed,CPU (%),Memory (KB)\n"]
    while not stop_event.is_set() and proc.is_running():
        cpu = proc.cpu_percent(interval=interval)
        mem = proc.memory_info().rss // 1024
        elapsed = round(time.time() - start_time, 2)
        log_lines.append(f"{elapsed},{cpu},{mem}\n")
        usage_log.append((elapsed, cpu, mem))
    try:
        with open(CPU_LOG_FILE, "w") as cpu_log:
            cpu_log.writelines(log_lines)
    except Exception as e:
        print(f"Failed to write CPU log: {e}")

def run_and_monitor_nginx():
    global start_time
    kraft_proc = None
    qemu_proc = None
    usage_log = []
    startup_time = None
    stop_event = threading.Event()
    monitor_thread = None
    end_time = None

    def cleanup(signum=None, frame=None):
        nonlocal end_time
        buffered_print("Interrupt signal received, cleaning up")
        stop_event.set()

        if kraft_proc:
            try:
                kraft_proc.terminate()
                kraft_proc.wait(timeout=5)
            except Exception:
                pass

        if monitor_thread and monitor_thread.is_alive():
            buffered_print("Waiting for monitor thread to finish")
            monitor_thread.join(timeout=10)

        end_time = time.time()

        file_exists = os.path.exists(METRICS_FILE)
        with open(METRICS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Time (s)", "CPU Usage (%)", "Memory Usage (KB)"])
            if startup_time is not None and isinstance(startup_time, float):
                for t, cpu, mem in usage_log:
                    writer.writerow([t, cpu, mem])

        tee_print_all()
        qemu_duration = round(end_time - qemu_start, 3) if qemu_proc else 0
        total_duration = round(end_time - kraft_start, 3)
        buffered_print(f"QEMU total duration: {qemu_duration}s")
        buffered_print(f"Total runtime: {total_duration}s")
        if usage_log:
            cpu_avg = round(sum(cpu for _, cpu, _ in usage_log) / len(usage_log), 2)
            mem_avg = round(sum(mem for _, _, mem in usage_log) / len(usage_log), 2)
            buffered_print(f"Avg CPU: {cpu_avg}%")
            buffered_print(f"Avg Memory: {mem_avg} KB")
        exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        print("Starting Unikraft unikernel for Nginx...")
        kraft_start = time.time()
        kraft_proc = subprocess.Popen(
            ["kraft", "run", "--log-level", "debug", "--log-type", "basic", "-p", "8080:80", "--plat", "qemu", "--arch", "x86_64", "."],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1
        )

        print("Waiting for QEMU")
        qemu_proc = find_qemu_proc()
        if not qemu_proc:
            buffered_print("QEMU not found.")
            kraft_proc.kill()
            return

        qemu_start = time.time()
        qemu_pid = qemu_proc.pid
        buffered_print(f"QEMU started after +{round(qemu_start - kraft_start, 3)}s (PID: {qemu_pid})")

        start_time = time.time()
        monitor_thread = threading.Thread(
            target=monitor_resource_usage_live,
            args=(qemu_proc, usage_log, stop_event),
            daemon=True
        )
        monitor_thread.start()
        buffered_print("Started resource monitoring immediately after QEMU detection.")

        print("Waiting for Nginx")
        nginx_ready = wait_for_nginx_ready("localhost", 8080)
        if not nginx_ready:
            buffered_print("Nginx did not start in time.")
            startup_time = "timeout"
        else:
            startup_time = round(nginx_ready - qemu_start, 3)
            print(f"Nginx ready after +{startup_time}s")
            buffered_print(f"Nginx startup time {startup_time}s")

        print("Nginx is running. Press ctrl+c to stop the unikernel and exit.")

        while kraft_proc.poll() is None:
            time.sleep(1)

    except Exception as e:
        buffered_print(f"Exception occurred: {e}")
        cleanup()

if __name__ == "__main__":
    run_and_monitor_nginx()