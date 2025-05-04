import subprocess

for i in range(5):
    out_file = f"nginx_ubuntu_run_100_{i}.txt"
    with open(out_file, "w") as f:
        subprocess.run(
            ["wrk", "-t4", "-c100", "-d30s", "http://localhost:8080/"],
            stdout=f
        )


