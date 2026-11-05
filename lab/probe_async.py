import time
from concurrent.futures import ThreadPoolExecutor
import httpx

with ThreadPoolExecutor() as pool:
    pending = pool.submit(
        httpx.get, "http://127.0.0.1:8010/wait", timeout=10,
    )
    time.sleep(0.3)
    response = httpx.get("http://127.0.0.1:8010/health", timeout=10)
    print("health:", response.status_code)
    print("wait finished before health:", pending.done())
    print("wait:", pending.result().status_code)
