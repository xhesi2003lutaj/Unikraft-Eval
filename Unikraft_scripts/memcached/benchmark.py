# measuring network I/O performance, stressing the request/response cycle while focusing on application-level I/O, particularly memory-based I/O, 
# since memcached operates entirely on RAM


import subprocess

for i in range(5):
    subprocess.run([
        "memtier_benchmark",
        "-s", "127.0.0.1",
        "-p", "11211",
        "--protocol=memcache_text",
        "--threads=4",
        "--clients=50",
        "--test-time=30",
        f"--json-out-file=unikraft_run1_{i}.json"
    ])

