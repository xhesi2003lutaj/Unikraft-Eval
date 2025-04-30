import subprocess
import time
import requests

def start_nginx():
    subprocess.run(["sudo", "systemctl", "restart", "nginx"])

def wait_for_nginx_ready(url="http://localhost", timeout=10):
    start = time.time()
    deadline = start + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=0.5)
            if r.status_code == 200:
                return time.time() - start
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.1)
    raise TimeoutError("NGINX did not become ready in time.")

if __name__ == "__main__":
    print("Restarting NGINX...")
    start_time = time.time()
    start_nginx()
    try:
        ready_in = wait_for_nginx_ready()
        print(f"NGINX ready in {ready_in:.3f} seconds")
    except TimeoutError as e:
        print(e)
