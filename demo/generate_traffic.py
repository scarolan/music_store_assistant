#!/usr/bin/env python3
"""Generate traffic against the Music Store Assistant API for demo purposes."""

import requests
import time
import random
from datetime import datetime

API_URL = "http://localhost:8000"

# Various customer queries to generate diverse traces
MUSIC_QUERIES = [
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
]

SUPPORT_QUERIES = [
    "Show me my recent purchases",
    "What's on my account?",
    "Can you tell me about my orders?",
    "Show me my invoices",
    "What's my customer information?",
]

def make_request(query: str, thread_id: str) -> dict:
    """Make a chat request to the API."""
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": query,
                "thread_id": thread_id,
                "customer_id": random.randint(1, 59)  # Chinook has customers 1-59
            },
            timeout=30
        )
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_conversation(conversation_id: int):
    """Generate a multi-turn conversation."""
    thread_id = f"demo-traffic-{conversation_id}"

    # Random mix of queries
    if random.random() < 0.7:  # 70% music queries
        queries = random.sample(MUSIC_QUERIES, k=random.randint(1, 3))
    else:  # 30% support queries
        queries = random.sample(SUPPORT_QUERIES, k=random.randint(1, 2))

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Conversation #{conversation_id} (thread: {thread_id})")

    for i, query in enumerate(queries, 1):
        print(f"  Query {i}: {query[:50]}...")
        result = make_request(query, thread_id)
        if result:
            print(f"    ✓ Response: {len(result.get('response', ''))} chars")

        # Small delay between queries in same conversation
        time.sleep(random.uniform(0.5, 1.5))

def main():
    """Generate traffic with multiple concurrent conversations."""
    print("🎸 Music Store Traffic Generator")
    print(f"Target: {API_URL}")
    print("=" * 60)

    # Check if server is running
    try:
        health = requests.get(f"{API_URL}/health", timeout=2)
        print(f"✓ Server status: {health.json()}\n")
    except Exception as e:
        print(f"✗ Server not responding: {e}")
        return

    # Generate conversations
    num_conversations = 15
    print(f"Generating {num_conversations} conversations...\n")

    for i in range(num_conversations):
        generate_conversation(i + 1)

        # Delay between conversations to spread out traffic
        if i < num_conversations - 1:
            delay = random.uniform(0.5, 2.0)
            time.sleep(delay)

    print("\n" + "=" * 60)
    print(f"✓ Generated {num_conversations} conversations!")
    print("Check your Grafana dashboard for traces and metrics.")
    print(f"Query in Tempo: {{service.name=\"music-store-assistant\"}}")

if __name__ == "__main__":
    main()
