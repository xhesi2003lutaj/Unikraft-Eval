import os
import re
import matplotlib.pyplot as plt
import pandas as pd

# List of input files with .txt extension
files = [
    # 'fibonacci_5_ubuntu.txt',
    # 'fibonacci_5_unikraft.txt',
    # 'fibonacci_30_ubuntu.txt',
    # 'fibonacci_30_unikraft.txt',
    'fibonacci_50_ubuntu.txt',
    'fibonacci_50_unikraft.txt'
]

# Regex pattern to extract time from lines
pattern = re.compile(r"Elapsed time:\s+(\d+)\s+ns")

# Store results
results = []

# Process each file
for file in files:
    with open(file, 'r') as f:
        times_ns = []
        for line in f:
            match = pattern.search(line)
            if match:
                times_ns.append(int(match.group(1)))

        if times_ns:
            avg_ns = sum(times_ns) / len(times_ns)
            avg_ms = avg_ns / 1_000_000  # Convert to milliseconds

            parts = file.replace('.txt', '').split('_')
            fib_input = parts[1]
            platform = parts[2]

            results.append({
                'Fibonacci': fib_input,
                'Platform': platform,
                'AverageTime_ms': avg_ms
            })

# Convert to DataFrame
df = pd.DataFrame(results)

# Plot settings
fib_inputs = sorted(df['Fibonacci'].unique(), key=int)
platforms = ['ubuntu', 'unikraft']
bar_width = 0.35
x = range(len(fib_inputs))

plt.figure(figsize=(10, 6))

# Plot grouped bars
for i, platform in enumerate(platforms):
    times = []
    for fib in fib_inputs:
        match = df[(df['Fibonacci'] == fib) & (df['Platform'] == platform)]
        if not match.empty:
            times.append(match['AverageTime_ms'].values[0])
        else:
            print(f"Warning: No data for {platform} Fibonacci {fib}")
            times.append(None)

    # Filter out missing data
    offsets = [pos + (i - 0.5) * bar_width for pos, t in zip(x, times) if t is not None]
    valid_times = [t for t in times if t is not None]
    bars = plt.bar(offsets, valid_times, width=bar_width, label=platform.capitalize())

    # Add labels
    for rect in bars:
        height = rect.get_height()
        plt.text(rect.get_x() + rect.get_width() / 2, height + 0.5,
                 f'{height:.2f}', ha='center', va='bottom', fontsize=8)

# Final chart formatting
plt.xlabel('Fibonacci Sequence')
plt.ylabel('Average Time (ms)')
plt.title('Average Execution Time of Fibonacci in C Code (Milliseconds)')
plt.xticks(ticks=x, labels=fib_inputs)
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

# Save and show the plot
plt.savefig('50_fibonacci_times_ms.png', dpi=300)
plt.show()
