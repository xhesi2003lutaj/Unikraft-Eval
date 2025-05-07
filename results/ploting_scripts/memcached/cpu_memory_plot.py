import matplotlib.pyplot as plt
import csv

ubuntu_path = "../../../../../metrics/cpu_usage_ubuntu.log"
unikraft_path = "cpu_usage_unikraft.log"

def read_cpu_mem_log(path):
    times, cpus, mems = [], [], []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                time_val = row.get("Time (s)") or row.get("Time Elapsed") or row.get(" Time Elapsed")
                cpu_val = row.get("CPU Usage (%)") or row.get("CPU (%)") or row.get(" CPU (%)")
                mem_val = row.get("Memory (KB)") or row.get(" Memory (KB)")
                if time_val is not None and cpu_val is not None and mem_val is not None:
                    print("brenda")
                    times.append(float(time_val.strip()))
                    cpus.append(float(cpu_val.strip()))
                    mems.append(float(mem_val.strip()))
            except Exception:
                continue
    return times, cpus, mems

ubuntu_time, ubuntu_cpu, ubuntu_mem = read_cpu_mem_log(ubuntu_path)
unikraft_time, unikraft_cpu, unikraft_mem = read_cpu_mem_log(unikraft_path)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

ax1.plot(ubuntu_time, ubuntu_cpu, label="Ubuntu VM", marker='o')
ax1.plot(unikraft_time, unikraft_cpu, label="Unikraft", marker='x')
ax1.set_ylabel("CPU Usage (%)")
ax1.set_title("CPU and Memory Usage of QEMU During 5 Consecutive Memcached Benchmarking (4 threads, 50 clients, in a timeframe of 30s)")
ax1.legend()
ax1.grid(True)

ax2.plot(ubuntu_time, ubuntu_mem, label="Ubuntu VM", marker='o')
ax2.plot(unikraft_time, unikraft_mem, label="Unikraft", marker='x')
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Memory Usage (KB)")
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.savefig("cpu_memory_usage_comparison.png", dpi=300)
plt.show()