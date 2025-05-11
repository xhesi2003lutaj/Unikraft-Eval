import subprocess
import psutil
import time
import os
import csv
import socket
import threading
import signal
import sys

LOG_DIR = "metrics"
os.makedirs(LOG_DIR, exist_ok=True)
METRICS_FILE = os.path.join(LOG_DIR, "ubuntu_nginx_metrics.csv")
TEED_LOG_FILE = os.path.join(LOG_DIR, "ubuntu_full_output.log")
CPU_LOG_FILE = os.path.join(LOG_DIR, "cpu_usage_ubuntu.log")

start_time = None
full_log_lines = []

def buffered_print(message):
    print(message)
    full_log_lines.append(message)

def tee_print_all():
    with open(TEED_LOG_FILE, "a") as f:
        for line in full_log_lines:
            f.write(line + "\n")

def wait_for_nginx_ready(host="127.0.0.1", port=8080, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return time.time()
        except (OSError, ConnectionRefusedError):
            time.sleep(0.1)
    return None

def monitor_resource_usage_live(proc, usage_log, stop_event, interval=1):
    try:
        proc.cpu_percent(interval=None)
    except psutil.NoSuchProcess:
        buffered_print("aborted: QEMU exited before warm-up.")
        return

    log_lines = ["Time Elapsed,CPU (%),Memory (KB)\n"]
    while not stop_event.is_set():
        try:
            if not proc.is_running():
                break
            cpu = proc.cpu_percent(interval=interval)
            mem = proc.memory_info().rss // 1024
            elapsed = round(time.time() - start_time, 2)
            log_lines.append(f"{elapsed},{cpu},{mem}\n")
            usage_log.append((elapsed, cpu, mem))
        except psutil.NoSuchProcess:
            buffered_print("QEMU exited during monitoring.")
            break
        except Exception as e:
            buffered_print(f"Monitoring error: {e}")
            break

    try:
        with open(CPU_LOG_FILE, "w") as cpu_log:
            cpu_log.writelines(log_lines)
    except Exception as e:
        buffered_print(f"Failed to write CPU log: {e}")

def run_and_monitor_ubuntu_nginx():
    global start_time
    vm_proc = None
    qemu_proc = None
    qemu_start = None
    usage_log = []
    startup_time = None
    stop_event = threading.Event()
    monitor_thread = None
    end_time = None

    def cleanup(signum=None, frame=None):
        nonlocal end_time
        buffered_print("Interruptedddddddddddd-----")
        stop_event.set()

        if vm_proc and vm_proc.poll() is None:
            try:
                os.killpg(os.getpgid(vm_proc.pid), signal.SIGTERM)
                vm_proc.wait(timeout=10)
            except Exception as e:
                buffered_print(f"Could not terminate QEMU process group: {e}")

        if monitor_thread and monitor_thread.is_alive():
            buffered_print("Waiting for monitor thread to finish")
            monitor_thread.join(timeout=10)

        end_time = time.time()

        file_exists = os.path.exists(METRICS_FILE)
        with open(METRICS_FILE, "a", newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Time (s)", "CPU Usage (%)", "Memory Usage (KB)"])
            if isinstance(startup_time, float):
                for t, cpu, mem in usage_log:
                    writer.writerow([t, cpu, mem])

        tee_print_all()
        qemu_duration = round(end_time - qemu_start, 3) if qemu_start else 0
        total_duration = round(end_time - kraft_start, 3)
        buffered_print(f"QEMU total duration: {qemu_duration}s")
        buffered_print(f"Total runtime: {total_duration}s")
        if usage_log:
            cpu_avg = round(sum(cpu for _, cpu, _ in usage_log) / len(usage_log), 2)
            mem_avg = round(sum(mem for _, _, mem in usage_log) / len(usage_log), 2)
            buffered_print(f"Avg CPU: {cpu_avg}%")
            buffered_print(f"Avg Memory: {mem_avg} KB")

        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        buffered_print("Starting Ubuntu QEMU VM with Nginx")
        kraft_start = time.time()

        vm_proc = subprocess.Popen(
            [
                "qemu-system-x86_64",
                "-m", "128M",
                "-smp", "cpus=1,threads=1,sockets=1",
                "-cpu", "host,+x2apic,-pmu",
                "-netdev", "user,id=net0,hostfwd=tcp::8080-:80",
                "-device", "virtio-net-pci,netdev=net0",
                "-drive", "file=ubuntu.qcow2,format=qcow2",
                "-cdrom", "seed.iso",
                "-enable-kvm",
                "-nographic",
                "-serial", "mon:stdio"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )

        buffered_print("Waiting for QEMU process to appear")
        deadline = time.time() + 15
        while time.time() < deadline:
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if p.name().startswith('qemu-system') and "8080" in ' '.join(p.cmdline()):
                        qemu_proc = p
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if qemu_proc:
                break
            time.sleep(0.5)

        if not qemu_proc:
            buffered_print("Couldn't find QEMU process.")
            return

        qemu_start = time.time()
        start_time = time.time()
        buffered_print(f"QEMU started after +{round(qemu_start - kraft_start, 3)}s (PID: {qemu_proc.pid})")

        monitor_thread = threading.Thread(
            target=monitor_resource_usage_live,
            args=(qemu_proc, usage_log, stop_event),
            daemon=True
        )
        monitor_thread.start()

        buffered_print("Waiting for Nginx")
        ready_time = wait_for_nginx_ready("127.0.0.1", 8080)

        if ready_time:
            startup_time = round(ready_time - qemu_start, 3)
            buffered_print(f"Nginx is ready at +{startup_time}s")
        else:
            buffered_print("Nginx did not start in time.")
            startup_time = "timeout"

        print("Nginx is running. Press Ctrl+C to stop and exit.")
        while vm_proc.poll() is None:
            time.sleep(1)

    except Exception as e:
        buffered_print(f"Exception occurred: {e}")
        cleanup()

if __name__ == "__main__":
    run_and_monitor_ubuntu_nginx()
