#!/usr/bin/env python3
"""
Continuous Traffic Generator for Music Store Assistant Demo

Generates ongoing realistic traffic for 30 minutes (or until stopped).
Runs at a moderate pace to keep Grafana dashboards populated with fresh data.
"""

import requests
import random
import time
import signal
import sys
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

# Mix of music and support queries
QUERIES = [
    # Music queries (70%)
    "What albums does AC/DC have?",
    "Do you have any Pink Floyd albums?",
    "What genres of music do you have?",
    "Show me some rock music",
    "What tracks are by Led Zeppelin?",
    "Do you have any jazz albums?",
    "Tell me about Metallica albums",
    "What classical music do you have?",
    "Show me blues artists",
    "Do you have any Metal albums?",

    # Support queries (30%)
    "Show me my recent purchases",
    "What's on my account?",
    "Can you tell me about my orders?",
    "What's my customer information?",
    "Show me my invoices",
]

running = True

def signal_handler(sig, frame):
    global running
    print("\n\n🛑 Stopping continuous traffic generation...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def make_request():
    """Make a single request to the API"""
    query = random.choice(QUERIES)
    thread_id = f"continuous-{random.randint(1000, 9999)}"
    customer_id = random.randint(1, 59)

    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": query,
                "thread_id": thread_id,
                "customer_id": customer_id
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            response_len = len(data.get("response", ""))
            return True, response_len
        else:
            return False, 0
    except Exception as e:
        return False, 0

def main():
    print("🎸 Continuous Traffic Generator")
    print(f"Target: {API_URL}")
    print("=" * 60)
    print("Generating traffic for 30 minutes (or until Ctrl+C)...")
    print(f"Started at {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    print()

    # Run for 30 minutes
    end_time = datetime.now() + timedelta(minutes=30)
    request_count = 0
    success_count = 0

    while running and datetime.now() < end_time:
        request_count += 1
        success, response_len = make_request()

        if success:
            success_count += 1
            status = "✓"
        else:
            status = "✗"

        # Print progress every 10 requests
        if request_count % 10 == 0:
            elapsed = (datetime.now() - (end_time - timedelta(minutes=30))).total_seconds() / 60
            success_rate = (success_count / request_count) * 100
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Requests: {request_count} | "
                  f"Success: {success_count} ({success_rate:.1f}%) | "
                  f"Elapsed: {elapsed:.1f} min")

        # Wait 3-7 seconds between requests (moderate pace)
        time.sleep(random.uniform(3, 7))

    # Summary
    print()
    print("=" * 60)
    if running:
        print("✅ Completed 30-minute traffic generation")
    else:
        print("✅ Traffic generation stopped by user")
    print(f"Total requests: {request_count}")
    print(f"Successful: {success_count} ({(success_count/request_count)*100:.1f}%)")
    print("=" * 60)

if __name__ == "__main__":
    main()
