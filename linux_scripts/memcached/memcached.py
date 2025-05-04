import subprocess
import psutil
import time
import os
import csv
import socket
import shlex
import threading
import signal

LOG_DIR = "metrics"
os.makedirs(LOG_DIR, exist_ok=True)
DETAILED_LOG_FILE = os.path.join(LOG_DIR, "ubuntu_memcached_metrics.csv")
SUMMARY_LOG_FILE = os.path.join(LOG_DIR, "metrics_summary.csv")
TEED_LOG_FILE = os.path.join(LOG_DIR, "ubuntu_full_output.log")
CPU_LOG_FILE = os.path.join(LOG_DIR, "cpu_usage_ubuntu.log")

full_log_lines = []

def buffered_print(message):
    print(message)
    full_log_lines.append(message)

def tee_print_all():
    with open(TEED_LOG_FILE, "a") as f:
        for line in full_log_lines:
            f.write(line + "\n")

def port_in_use(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def disable_host_memcached():
    try:
        if port_in_use(11211):
            buffered_print("Port 11211 is in use, trying to stop host memcached")
            subprocess.run(["sudo", "systemctl", "stop", "memcached"], check=False)
            time.sleep(2)

            if port_in_use(11211):
                buffered_print("Trying to kill process using port 11211")
                result = subprocess.run(["sudo", "lsof", "-t", "-i:11211"], capture_output=True, text=True)
                pids = result.stdout.strip().splitlines()
                for pid in pids:
                    buffered_print(f"Killing by pid {pid}")
                    subprocess.run(["sudo", "kill", "-9", pid], check=False)
                    print("u aygjesua")
                time.sleep(1)

            if port_in_use(11211):
                buffered_print("11211 is still in use after all attempts")
                return False

            buffered_print("11211 now free.")
        else:
            buffered_print("11211 was free from the beginning")
        return True
    except Exception as e:
        buffered_print(f"Error stopping host Memcached: {e}")
        return False

def wait_for_memcached_ready(host="127.0.0.1", port=11211, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return time.time()
        except (OSError, ConnectionRefusedError):
            time.sleep(0.1)
    return None

def monitor_resource_usage_live(proc, usage_log, stop_event, interval=5):
    proc.cpu_percent(interval=None)
    log_lines = ["Time Elapsed,CPU (%),Memory (KB)\n"]
    while not stop_event.is_set() and proc.is_running():
        cpu = proc.cpu_percent(interval=interval)
        mem = proc.memory_info().rss // 1024
        elapsed = round(time.time() - start_time, 2)
        log_lines.append(f"{elapsed},{cpu},{mem}\n")
        usage_log.append([elapsed, cpu, mem, "running"])
    with open(CPU_LOG_FILE, "w") as cpu_log:
        cpu_log.writelines(log_lines)

def run_and_monitor_ubuntu_memcached():
    global start_time
    vm_proc = None
    startup_time = None
    usage_log = []
    stop_event = threading.Event()
    end_time = None

    def cleanup(signum=None, frame=None):
        nonlocal end_time
        buffered_print("Interrupt signal received, cleaning up")
        stop_event.set()
        if vm_proc:
            try:
                os.killpg(os.getpgid(vm_proc.pid), signal.SIGTERM)
            except Exception as e:
                buffered_print(f"Could not terminate QEMU process group: {e}")
            vm_proc.wait()
        end_time = time.time()

        with open(DETAILED_LOG_FILE, "a", newline='') as f:
            writer = csv.writer(f)
            if os.stat(DETAILED_LOG_FILE).st_size == 0:
                writer.writerow(["Time Elapsed", "CPU (%)", "Memory (KB)", "Event"])
            if startup_time and isinstance(startup_time, float):
                writer.writerow([startup_time, "", "", "memcached_started"])
            writer.writerows(usage_log)

        tee_print_all()
        duration = round(end_time - start_time, 3)
        buffered_print(f"QEMU duration: {duration}s")
        if usage_log:
            cpu_avg = round(sum(cpu for _, cpu, _, _ in usage_log) / len(usage_log), 2)
            mem_avg = round(sum(mem for _, _, mem, _ in usage_log) / len(usage_log), 2)
            buffered_print(f"Avg CPU: {cpu_avg}%")
            buffered_print(f"Avg Memory: {mem_avg} KB")
        exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        if not disable_host_memcached():
            buffered_print("Aborting due to port conflict.")
            return

        buffered_print("Starting Ubuntu QEMU VM with Memcached")

        start_time = time.time()
        vm_proc = subprocess.Popen(
            [
                "qemu-system-x86_64",
                "-m", "128M",
                "-smp", "cpus=1,threads=1,sockets=1",
                "-cpu", "host,+x2apic,-pmu",
                "-netdev", "user,id=net0,hostfwd=tcp::11211-:11211",
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

        buffered_print("Waiting for Memcached to accept connections")
        ready_time = wait_for_memcached_ready("127.0.0.1", 11211, timeout=30)

        if ready_time:
            startup_time = round(ready_time - start_time, 3)
            buffered_print(f"Memcached is ready at +{startup_time}s")
        else:
            buffered_print("Memcached did not start in time")
            startup_time = "timeout"

        time.sleep(1)
        qemu_proc = next((p for p in psutil.process_iter(['pid', 'name', 'cmdline']) if 'qemu-system-x86_64' in p.info['name']), None)
        if not qemu_proc:
            buffered_print("Couldn't find QEMU process")
        else:
            buffered_print(f"QEMU PID: {qemu_proc.pid}")
            monitor_thread = threading.Thread(
                target=monitor_resource_usage_live,
                args=(qemu_proc, usage_log, stop_event),
                daemon=True
            )
            monitor_thread.start()
            print("Memcached is running. Press ctrl+c to stop and exit.")
            vm_proc.wait()

    except Exception as e:
        buffered_print(f"Exception occurred: {e}")
        cleanup()

if __name__ == "__main__":
    run_and_monitor_ubuntu_memcached()