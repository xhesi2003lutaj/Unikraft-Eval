import subprocess
import psutil
import time
import os
import signal
import csv

LOG_DIR = "metrics"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "unikraft_memcached_metrics.csv")
TEED_LOG_FILE = os.path.join(LOG_DIR, "memcached_full_output.log")
# Add at the top
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

def find_qemu_proc(timeout=10):
    qemu_proc = None
    deadline = time.time() + timeout
    while time.time() < deadline: # HOw long the fs. should wait to find the qemu process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']): # iterating over currently running processes
            try:
                if 'qemu-system-x86_64' in proc.info['name']:
                    # Optionally filter further based on command line args
                    if any('memcached' in arg or '.img' in arg for arg in proc.info['cmdline']): # Making sure the qemu process is the one initiated by kraft
                        print("e gjeti qemu")
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
        for line in iter(proc.stdout.readline, b''): # more can be retrieved than only the start of nginx, because I am runnig kraft in debug mode
            decoded = line.decode("utf-8", errors="ignore").strip()
            log_lines.append(decoded)
            now = time.time()
            elapsed = round(now - start_time, 3)

            if nginx_ready_trigger.lower() in decoded.lower() and nginx_started is None:
                nginx_started = now
                buffered_print(f"NGINX Started at +{elapsed:.2f}s: {decoded}")
                csv_rows.append([elapsed, "", "", "memcached_started"])

            if proc.poll() is None: # poll return None if process still running
                try:
                    stats = proc_qemu.cpu_percent(interval=0.1), proc_qemu.memory_info().rss // 1024 # proc_qemu made global in run_and_monitor_nginx(
                    csv_rows.append([elapsed, stats[0], stats[1], "running"])
                except Exception: # passing because logically and technically kraft cannot exit before the app and qemu 
                    pass

    except KeyboardInterrupt:
        nginx_stopped = time.time()
        elapsed = round(nginx_stopped - start_time, 3)
        buffered_print(f"MEMCACHED Stopped via Ctrl+C at +{elapsed:.2f}s")
        csv_rows.append([elapsed, "", "", "nginx_stopped"])

    finally:
        proc.stdout.close()

    return csv_rows, nginx_started, nginx_stopped

def print_process_tree(pid, indent=""):
    try:
        proc = psutil.Process(pid)
        print(f"{indent}{proc.pid}: {' '.join(proc.cmdline())}")
        for child in proc.children(recursive=False):
            print_process_tree(child.pid, indent + "    ")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

def run_and_monitor_nginx():
    buffered_print("Starting the Unikraft unikernel")
    start_time = time.time()
    
    kraft_proc = subprocess.Popen(
        ["kraft", "run", "--log-level", "debug", "--log-type", "basic", "-p", "11211:11211", "--plat", "qemu", "--arch", "x86_64", "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    buffered_print("Waiting for QEMU to start...")
    time.sleep(3)  # Give QEMU time to spawn

    qemu_proc = find_qemu_proc_by_port("11211")
    if not qemu_proc:
        print("Could not find the QEMU process.")
        kraft_proc.kill()
        return

    buffered_print(f"QEMU PID: {qemu_proc.pid}")
    print_process_tree(kraft_proc.pid)

    global proc_qemu
    proc_qemu = qemu_proc
    print("CMD:", ' '.join(qemu_proc.cmdline()))    

    # Monitoring the kraft process and collecting metrics
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
        buffered_print(f"MEMCACHED lifetime: {round(nginx_end - nginx_start, 3)}s")

    with open(TEED_LOG_FILE, "a") as log_file:
        for line in full_log_lines:
            log_file.write(line + "\n")

if __name__ == "__main__":
    run_and_monitor_nginx()
