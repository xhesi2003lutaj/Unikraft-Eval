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

# Read from files
memcached_file = "../../../../../metrics/startup_times.txt"
nginx_file = "memcached_full_output.log"

memcached_times = read_times_from_file(memcached_file)
nginx_times = read_times_from_file(nginx_file, strip_s=True)

# Compute averages
avg_memcached = sum(memcached_times) / len(memcached_times) if memcached_times else 0
avg_nginx = sum(nginx_times) / len(nginx_times) if nginx_times else 0

# Plot
labels = ['Memcached (Ubuntu)', 'Memcached (Unikraft)']
averages = [avg_memcached, avg_nginx]
colors = ['steelblue', 'orange']  # Add custom colors here

plt.figure(figsize=(8, 6))
plt.bar(labels, averages, color=colors)
plt.ylabel('Average Startup Time (s)')
plt.title('Average Startup Time Comparison')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

plt.show()
