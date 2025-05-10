import matplotlib.pyplot as plt

def read_times_from_file(filepath, strip_s=False):
    times = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if strip_s and line.endswith('s'):
                line = line[:-1]  # remove 's'
            try:
                times.append(float(line))
            except ValueError:
                continue  # skip invalid lines
    return times

# === File Paths ===
unikraft_file = "startup_times_nginx.txt"
ubuntu_file = "../../../../../metrics_nginx/startup_times_nginx.txt"

unikraft_times = read_times_from_file(unikraft_file)
ubuntu_times = read_times_from_file(ubuntu_file)

# === Compute Averages ===
avg_unikraft = sum(unikraft_times) / len(unikraft_times) if unikraft_times else 0
avg_ubuntu = sum(ubuntu_times) / len(ubuntu_times) if ubuntu_times else 0

# === Plot ===
labels = ['Nginx (Unikraft)', 'Nginx (Ubuntu)']
averages = [avg_unikraft, avg_ubuntu]
colors = ['green', 'royalblue']

plt.figure(figsize=(8, 6))
plt.bar(labels, averages, color=colors)
plt.ylabel('Average Startup Time (s)')
plt.title('Average Startup Time: Nginx on Unikraft vs Ubuntu')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig("nginx_startup_comparison.png")
plt.show()
