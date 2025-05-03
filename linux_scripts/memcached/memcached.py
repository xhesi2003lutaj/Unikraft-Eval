import subprocess
import psutil
import time
import os
import csv
import socket
import signal

LOG_DIR = "metrics"
os.makedirs(LOG_DIR, exist_ok=True)
DETAILED_LOG_FILE = os.path.join(LOG_DIR, "ubuntu_memcached_metrics.csv")
SUMMARY_LOG_FILE = os.path.join(LOG_DIR, "metrics_summary.csv")
TEED_LOG_FILE = os.path.join(LOG_DIR, "ubuntu_full_output.log")

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
            buffered_print("️oort 11211 is in usee, trying to stop host memcached")
            subprocess.run(["sudo", "systemctl", "stop", "memcached"], check=False)
            time.sleep(2)

            if port_in_use(11211):
                buffered_print("trying to kill process using port 11211...")
                result = subprocess.run(["sudo", "lsof", "-t", "-i:11211"], capture_output=True, text=True)
                pids = result.stdout.strip().splitlines()
                for pid in pids:
                    buffered_print(f"Killing by pid {pid}")
                    subprocess.run(["sudo", "kill", "-9", pid], check=False)
                time.sleep(1)

            if port_in_use(11211):
                buffered_print("11211 is still in use after all attempts")
                return False

            buffered_print("11211 now free.")
        else:
            buffered_print("11211 was free from the begginig")
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

def monitor_resource_usage(proc, start_time):
    csv_rows = []
    cpu_samples = []
    proc.cpu_percent(interval=None)
    while psutil.pid_exists(proc.pid):
        now = time.time()
        elapsed = round(now - start_time, 3)
        try:
            cpu = proc.cpu_percent(interval=0)
            mem = proc.memory_info().rss // 1024
            cpu_samples.append(cpu)
            csv_rows.append([elapsed, cpu, mem, "running"])
        except Exception:
            break
        time.sleep(0.2)
    avg_cpu = round(sum(cpu_samples) / len(cpu_samples), 2) if cpu_samples else 0.0
    return csv_rows, avg_cpu

def run_and_monitor_ubuntu_memcached():
    vm_proc = None
    startup_time = None
    end_time = None

    def cleanup(signum=None, frame=None):
        nonlocal end_time
        buffered_print("interrupt signal, cleaning")
        if vm_proc:
            try:
                os.killpg(os.getpgid(vm_proc.pid), signal.SIGTERM)
            except Exception as e:
                buffered_print(f"could not terminate qemu process group: {e}")
            vm_proc.wait()
        end_time = time.time()
        tee_print_all()
        if end_time and startup_time:
            with open(SUMMARY_LOG_FILE, "a", newline='') as f:
                writer = csv.writer(f)
                if f.tell() == 0:
                    writer.writerow([
                        "QEMU Start (s)", "Memcached Ready (s)", "QEMU End (s)",
                        "Startup Time (s)", "Total Time (s)", "Avg CPU (%)", "Status", "QEMU Command"
                    ])
                duration = round(end_time - start_time, 3)
                writer.writerow([
                    0.0,
                    round(startup_time, 3) if isinstance(startup_time, float) else startup_time,
                    duration,
                    startup_time,
                    duration,
                    avg_cpu_usage if 'avg_cpu_usage' in locals() else 0.0,
                    "Y" if isinstance(startup_time, float) else "N",
                    "qemu-system-x86_64 -m 128M -smp 1 ..."
                ])
        exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        csv_rows = []

        if not disable_host_memcached():
            buffered_print("Aborting due to port conflict.")
            return

        buffered_print("Starting Ubuntu QEMU VM with Memcached")

        start_time = time.time()
        vm_proc = subprocess.Popen(
            [
                "qemu-system-x86_64",
                "-m", "64M",
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


        buffered_print("Waiting for Memcached to accept connections...")
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
            avg_cpu_usage = 0.0
        else:
            csv_rows, avg_cpu_usage = monitor_resource_usage(qemu_proc, start_time)

    except Exception as e:
        buffered_print(f"Exception occurred: {e}")
        cleanup()

    finally:
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
            writer.writerows(csv_rows)

        tee_print_all()
        duration = round(end_time - start_time, 3)
        buffered_print(f"QEMU duration: {duration}s")
        if 'avg_cpu_usage' in locals():
            buffered_print(f"Avg CPU during Memcached: {avg_cpu_usage}%")

if __name__ == "__main__":
    run_and_monitor_ubuntu_memcached()
