import json
import os
import matplotlib.pyplot as plt
from collections import defaultdict

def load_metric(prefix, count, metric_key, max_time=30):
    metric_data = defaultdict(list)
    time_keys = set()

    for i in range(count):
        filename = f"{prefix}_run1_{i}.json"
        if not os.path.exists(filename):
            print(f"Missing file: {filename}")
            continue
        try:
            with open(filename) as f:
                data = json.load(f)
            time_series = data.get("ALL STATS", {}).get("Gets", {}).get("Time-Serie", {})
            for t, stats in time_series.items():
                t_int = int(t)
                if t_int > max_time:
                    continue
                if metric_key in stats:
                    metric_data[t_int].append(stats[metric_key])
                    time_keys.add(t_int)
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    x = sorted(time_keys)
    y = [sum(metric_data[t]) / len(metric_data[t]) for t in x if metric_data[t]]
    return x, y

def plot_metric(unikraft_xy, ubuntu_xy, ylabel, title, filename, labels):
    plt.figure(figsize=(12, 6))
    if unikraft_xy[0] and unikraft_xy[1]:
        plt.plot(unikraft_xy[0], unikraft_xy[1], label=labels[0], marker='o')
    if ubuntu_xy[0] and ubuntu_xy[1]:
        plt.plot(ubuntu_xy[0], ubuntu_xy[1], label=labels[1], marker='x')
    plt.xlabel("Time Interval (s)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.show()
def plot_combined_overview(
    unikraft_ops, ubuntu_ops,
    unikraft_avg_lat, ubuntu_avg_lat,
    unikraft_p95, ubuntu_p95,
    unikraft_max_lat, ubuntu_max_lat
):
    fig, axs = plt.subplots(3, 1, figsize=(14, 12), sharex=True)

    # --- Latency Metrics ---
    axs[0].plot(*unikraft_avg_lat, label="Unikraft - Avg Latency", marker='o')
    axs[0].plot(*ubuntu_avg_lat, label="Ubuntu - Avg Latency", marker='x')
    axs[0].plot(*unikraft_p95, label="Unikraft - p99 Latency", marker='o')
    axs[0].plot(*ubuntu_p95, label="Ubuntu - p99 Latency", marker='x')
    axs[0].plot(*unikraft_max_lat, label="Unikraft - Max Latency", marker='o')
    axs[0].plot(*ubuntu_max_lat, label="Ubuntu - Max Latency", marker='x')
    axs[0].set_ylabel("Latency (ms)")
    axs[0].set_title("Latency Metrics Over Time")
    axs[0].legend()
    axs[0].grid(True)

    # --- Throughput ---
    axs[1].plot(*unikraft_ops, label="Unikraft - Throughput", marker='o')
    axs[1].plot(*ubuntu_ops, label="Ubuntu - Throughput", marker='x')
    axs[1].set_ylabel("Ops/sec")
    axs[1].set_title("Throughput Over Time")
    axs[1].legend()
    axs[1].grid(True)

    # --- Request Distribution (reuse ops/sec for now) ---
    axs[2].plot(*unikraft_ops, label="Unikraft - Requests", marker='o')
    axs[2].plot(*ubuntu_ops, label="Ubuntu - Requests", marker='x')
    axs[2].set_ylabel("Request Count")
    axs[2].set_xlabel("Time Interval (s)")
    axs[2].set_title("Request Distribution Over Time")
    axs[2].legend()
    axs[2].grid(True)

    plt.tight_layout()
    plt.savefig("combined_metrics_overview.png", dpi=300)
    plt.show()

# Configuration
max_time = 30
runs = 5
prefixes = ["unikraft", "ubuntu"]

# Throughput (ops/sec)
unikraft_ops = load_metric("unikraft", runs, "Count", max_time)
ubuntu_ops = load_metric("ubuntu", runs, "Count", max_time)
plot_metric(unikraft_ops, ubuntu_ops, "Operations Per Second", "Throughput Over Time", "throughput_plot.png",
            ["Unikraft - Throughput (ops/sec)", "Ubuntu - Throughput (ops/sec)"])

# Average Latency
unikraft_avg_lat = load_metric("unikraft", runs, "Average Latency", max_time)
ubuntu_avg_lat = load_metric("ubuntu", runs, "Average Latency", max_time)
plot_metric(unikraft_avg_lat, ubuntu_avg_lat, "Latency (ms)", "Average Latency Over Time", "avg_latency_plot.png",
            ["Unikraft - Avg Latency", "Ubuntu - Avg Latency"])

# p95 Latency
unikraft_p95 = load_metric("unikraft", runs, "p99.00", max_time)
ubuntu_p95 = load_metric("ubuntu", runs, "p99.00", max_time)
plot_metric(unikraft_p95, ubuntu_p95, "Latency (ms)", "p99 Latency Over Time", "p99_latency_plot.png",
            ["Unikraft - p99 Latency", "Ubuntu - p99 Latency"])

# Max Latency
unikraft_max_lat = load_metric("unikraft", runs, "Max Latency", max_time)
ubuntu_max_lat = load_metric("ubuntu", runs, "Max Latency", max_time)
plot_metric(unikraft_max_lat, ubuntu_max_lat, "Latency (ms)", "Max Latency Over Time", "max_latency_plot.png",
            ["Unikraft - Max Latency", "Ubuntu - Max Latency"])

# Request Distribution (Count)
# This is essentially the same as throughput but plotted separately if desired
plot_metric(unikraft_ops, ubuntu_ops, "Request Count per Interval", "Request Distribution Over Time", "request_distribution_plot.png",
            ["Unikraft - Requests", "Ubuntu - Requests"])

plot_combined_overview(
    unikraft_ops, ubuntu_ops,
    unikraft_avg_lat, ubuntu_avg_lat,
    unikraft_p95, ubuntu_p95,
    unikraft_max_lat, ubuntu_max_lat
)
