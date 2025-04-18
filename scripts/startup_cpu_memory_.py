import subprocess
import psutil
import time
import os
import signal
import csv

LOG_DIR = "metrics"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "unikraft_nginx_metrics.csv")

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
                    if any('unikraft' in arg or '.img' in arg for arg in proc.info['cmdline']): # Making sure the qemu process is the one initiated by kraft
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
                print(f"NGINX Started at +{elapsed:.2f}s: {decoded}")
                csv_rows.append([elapsed, "", "", "nginx_started"])

            if proc.poll() is None: # poll return None if process still running
                try:
                    stats = proc_qemu.cpu_percent(interval=0.1), proc_qemu.memory_info().rss // 1024 # proc_qemu made global in run_and_monitor_nginx(
                    csv_rows.append([elapsed, stats[0], stats[1], "running"])
                except Exception: # passing because logically and technically kraft cannot exit before the app and qemu 
                    pass

    except KeyboardInterrupt:
        nginx_stopped = time.time()
        elapsed = round(nginx_stopped - start_time, 3)
        print(f"NGINX Stopped via Ctrl+C at +{elapsed:.2f}s")
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
    print("Starting the Unikraft unikernel")
    start_time = time.time()
    
    kraft_proc = subprocess.Popen(
        ["kraft", "run", "--log-level", "debug", "--log-type", "basic", "-p", "8080:80", "--plat", "qemu", "--arch", "x86_64", "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    print("Waiting for QEMU to start...")
    time.sleep(3)  # Give QEMU time to spawn

    qemu_proc = find_qemu_proc_by_port("8080")
    if not qemu_proc:
        print("Could not find the QEMU process.")
        kraft_proc.kill()
        return

    print(f"QEMU PID: {qemu_proc.pid}")
    print_process_tree(kraft_proc.pid)

    global proc_qemu
    proc_qemu = qemu_proc
    print("CMD:", ' '.join(qemu_proc.cmdline()))    

    # Monitoring the kraft process and collecting metrics
    csv_rows, nginx_start, nginx_end = monitor_process(kraft_proc, start_time)

    kraft_proc.wait()
    end_time = time.time()

    with open(LOG_FILE, "w", newline='') as log_file:
        csv_writer = csv.writer(log_file)
        csv_writer.writerow(["Time Elapsed", "CPU (%)", "Memory (KB)", "Event"])
        csv_writer.writerows(csv_rows)

    print("QEMU ended")
    print(f"Boot Time: {round(nginx_start - start_time, 3) if nginx_start else 'N/A'}s")
    print(f"Total Runtime: {round(end_time - start_time, 3)}s")

    if nginx_end:
        print(f"NGINX lifetime: {round(nginx_end - nginx_start, 3)}s")

if __name__ == "__main__":
    run_and_monitor_nginx()
# def run_and_monitor_nginx():
#     # Launch kraft run
#     print("Starting the Unikraft unikernel")
#     start_time = time.time()
#     kraft_proc = subprocess.Popen(# THe command is specific to nginx , each application is using a specific port defined in the qemu arguments
#         ["kraft", "run", "--log-level", "debug", "--log-type", "basic", "-p","8080:80", "--plat", "qemu", "--arch", "x86_64", "."],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT
#     )

#     print("Waiting for qemu")
#     print("kraft proc pid ",kraft_proc.pid)
#     qemu_proc = find_qemu_proc() 
#     print(f"QEMU PID: {qemu_proc.pid}")
#     print_process_tree(kraft_proc.pid)

#     pidfile = '/home/xhesilda/.local/share/kraftkit/runtime/86b1f614e5c4/machine.pid'

#     with open(pidfile) as f:
#         qemu_pid = int(f.read().strip())

#     global proc_qemu
#     proc_qemu = psutil.Process(qemu_proc.pid)
#     print("CMD:", ' '.join(qemu_proc.cmdline()))    


#     # Monitoring and looking for nginx startup/shutdown logs:w
#     csv_rows, nginx_start, nginx_end = monitor_process(kraft_proc, start_time)

#     kraft_proc.wait()
#     end_time = time.time()

#     # Writing all metrics to file at once after the application has exited to not introduce unecessary overhead
#     with open(LOG_FILE, "w", newline='') as log_file:
#         csv_writer = csv.writer(log_file)
#         csv_writer.writerow(["Time Elapsed", "CPU (%)", "Memory (KB)", "Event"])
#         csv_writer.writerows(csv_rows)


#     print("QEMU ended")
#     print(f"Boot Time: {round(nginx_start - start_time, 3) if nginx_start else 'N/A'}s")
#     print(f"Total Runtime: {round(end_time - start_time, 3)}s")

#     if nginx_end:
#         print(f"NGINX lifetime: {round(nginx_end - nginx_start, 3)}s")


# if __name__ == "__main__":
#     run_and_monitor_nginx()


