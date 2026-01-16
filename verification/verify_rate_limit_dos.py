
import sys
import os
import time
import asyncio
from collections import defaultdict
from unittest.mock import MagicMock

# Add backend/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/src")))

from agent.security import RateLimitMiddleware
from fastapi import Request, Response

async def mock_call_next(request):
    return Response("ok")

def create_mock_request(client_ip):
    scope = {
        'type': 'http',
        'path': '/agent/test', # protected path
        'headers': [(b'host', b'localhost')],
        'client': (client_ip, 12345),
        'method': 'GET',
        'scheme': 'http'
    }
    return Request(scope)

async def run_benchmark():
    print("--- RateLimitMiddleware DoS Verification (Optimized) ---")

    app_mock = MagicMock()
    mw = RateLimitMiddleware(app_mock, limit=100, window=60, protected_paths=["/agent"])

    print("Pre-filling with 10,001 active IPs...")
    now = time.time()
    for i in range(10001):
        mw.requests[f"1.1.{i}.{i}"] = [now]

    # SIMULATE CLEANUP ALREADY RAN RECENTLY
    mw.last_cleanup = now

    print(f"Dictionary size: {len(mw.requests)}")
    print(f"Cleanup interval: {mw.cleanup_interval}")
    print(f"Time since last cleanup: {time.time() - mw.last_cleanup:.4f}s")

    # Measure time for a request from a NEW IP
    # This should SKIP the O(N) cleanup scan
    req = create_mock_request("2.2.2.2")

    start_time = time.time()
    response = await mw.dispatch(req, mock_call_next)
    end_time = time.time()

    duration = (end_time - start_time) * 1000 # ms
    print(f"Time taken for request (SKIP CLEANUP): {duration:.4f} ms")

    # Verify status
    print(f"Response status: {response.status_code}")

    # NOW FORCE CLEANUP TO RUN
    print("\n--- Force Cleanup Run ---")
    mw.last_cleanup = 0 # reset

    start_time = time.time()
    response = await mw.dispatch(req, mock_call_next)
    end_time = time.time()

    duration_full = (end_time - start_time) * 1000 # ms
    print(f"Time taken for request (FULL CLEANUP): {duration_full:.4f} ms")
    print(f"Response status: {response.status_code}")

    return duration

if __name__ == "__main__":
    asyncio.run(run_benchmark())
