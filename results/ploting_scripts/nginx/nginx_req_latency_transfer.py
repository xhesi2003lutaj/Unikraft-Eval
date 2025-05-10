import re
import matplotlib.pyplot as plt
import os

# Parameters
runs = 5
concurrency = 100  # from filename convention
ubuntu_prefix = f"nginx_ubuntu_run_{concurrency}_"
unikraft_prefix = f"nginx_unikraft_run_{concurrency}_"

# Data storage
results = {
    "ubuntu": {"requests_per_sec": [], "latency_avg_ms": [], "transfer_per_sec_MB": []},
    "unikraft": {"requests_per_sec": [], "latency_avg_ms": [], "transfer_per_sec_MB": []},
}

# Regex patterns
req_sec_re = re.compile(r"Requests/sec:\s+([\d.]+)")
latency_re = re.compile(r"Latency\s+([\d.]+)ms")
transfer_re = re.compile(r"Transfer/sec:\s+([\d.]+)([KMG]B)")

# Helper to extract metrics from a file
def extract_metrics(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    req_sec_match = req_sec_re.search(content)
    latency_match = latency_re.search(content)
    transfer_match = transfer_re.search(content)

    if not req_sec_match:
        raise ValueError(f"Requests/sec not found in {filepath}")
    if not latency_match:
        raise ValueError(f"Latency not found in {filepath}")
    if not transfer_match:
        raise ValueError(f"Transfer/sec not found in {filepath}")

    req_sec = float(req_sec_match.group(1))
    latency = float(latency_match.group(1))

    transfer_val = float(transfer_match.group(1))
    transfer_unit = transfer_match.group(2)

    # Convert everything to MB
    if transfer_unit == "KB":
        transfer = transfer_val / 1024
    elif transfer_unit == "MB":
        transfer = transfer_val
    elif transfer_unit == "GB":
        transfer = transfer_val * 1024
    else:
        raise ValueError(f"Unknown transfer unit '{transfer_unit}' in {filepath}")

    return req_sec, latency, transfer

# Read files for both setups
for i in range(runs):
    for platform, prefix in [("ubuntu", ubuntu_prefix), ("unikraft", unikraft_prefix)]:
        filename = f"{prefix}{i}.txt"
        if os.path.exists(filename):
            try:
                req_sec, latency, transfer = extract_metrics(filename)
                results[platform]["requests_per_sec"].append(req_sec)
                results[platform]["latency_avg_ms"].append(latency)
                results[platform]["transfer_per_sec_MB"].append(transfer)
            except ValueError as e:
                print(f"Error parsing {filename}: {e}")
        else:
            print(f"Warning: {filename} not found.")

# Plotting function for individual metrics
def plot_metric(metric_key, ylabel):
    plt.figure(figsize=(8, 5))
    for platform in ["ubuntu", "unikraft"]:
        plt.plot(
            range(1, runs + 1),
            results[platform][metric_key],
            marker="o",
            label=platform.capitalize()
        )
    plt.title(f"{ylabel} across {runs} runs (c={concurrency})")
    plt.xlabel("Run")
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"{metric_key}_comparison.png")
    plt.show()

# Plot all metrics individually
plot_metric("requests_per_sec", "Requests per Second")
plot_metric("latency_avg_ms", "Average Latency (ms)")
plot_metric("transfer_per_sec_MB", "Transfer per Second (MB)")

# Combined subplot figure
fig, axs = plt.subplots(3, 1, figsize=(10, 12))

metrics = [
    ("requests_per_sec", "Requests per Second"),
    ("latency_avg_ms", "Average Latency (ms)"),
    ("transfer_per_sec_MB", "Transfer per Second (MB)"),
]

for i, (metric_key, ylabel) in enumerate(metrics):
    ax = axs[i]
    for platform in ["ubuntu", "unikraft"]:
        ax.plot(
            range(1, runs + 1),
            results[platform][metric_key],
            marker="o",
            label=platform.capitalize()
        )
    ax.set_title(ylabel)
    ax.set_xlabel("Run")
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True)

plt.tight_layout()
plt.savefig("all_metrics_combined.png")
plt.show()

