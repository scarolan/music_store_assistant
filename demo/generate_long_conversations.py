#!/usr/bin/env python3
"""Generate long multi-turn conversations to drive up prompt tokens."""

import requests
import time
import random
from datetime import datetime

API_URL = "http://localhost:8000"

# Long conversation flows with follow-up questions
CONVERSATION_FLOWS = [
    [
        "What genres of music do you have?",
        "Tell me more about the Rock genre. What are some popular rock artists?",
        "What albums does Led Zeppelin have?",
        "Show me all the tracks from their albums",
        "Do you have any other classic rock bands like The Rolling Stones?",
        "What about AC/DC? What albums do they have?",
    ],
    [
        "I'm looking for some new music. What do you recommend?",
        "I like jazz and blues. What jazz artists do you have?",
        "Tell me about Miles Davis albums",
        "What tracks are on those albums?",
        "Do you have any similar artists in the jazz genre?",
        "What about blues artists? Who do you have?",
    ],
    [
        "Show me my account information",
        "What are my recent purchases?",
        "Tell me more about invoice 98",
        "What items were on that invoice?",
        "Can you show me all my invoices from this year?",
        "What's my total spending so far?",
    ],
    [
        "Do you have any Metal albums?",
        "Tell me about Metallica. What albums do they have?",
        "What tracks are on the Master of Puppets album?",
        "Do you have any other metal bands like Iron Maiden?",
        "What about Black Sabbath? Do you carry their albums?",
        "Show me all heavy metal artists in your catalog",
    ],
    [
        "What classical music do you have?",
        "Tell me about Bach. What recordings do you have?",
        "What about Beethoven? Do you have his symphonies?",
        "Show me all classical composers in your catalog",
        "What are the most popular classical albums?",
        "Do you have any opera recordings?",
    ],
]

def make_request(query: str, thread_id: str, customer_id: int) -> dict:
    """Make a chat request to the API."""
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": query,
                "thread_id": thread_id,
                "customer_id": customer_id
            },
            timeout=45
        )
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_long_conversation(conversation_id: int):
    """Generate a long multi-turn conversation."""
    thread_id = f"long-convo-{conversation_id}"
    customer_id = random.randint(1, 59)

    # Pick a random conversation flow
    flow = random.choice(CONVERSATION_FLOWS)

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 💬 Long Conversation #{conversation_id}")
    print(f"  Thread: {thread_id} | Customer: {customer_id} | {len(flow)} queries")
    print("  " + "=" * 60)

    for i, query in enumerate(flow, 1):
        print(f"  [{i}/{len(flow)}] {query[:60]}...")
        result = make_request(query, thread_id, customer_id)
        if result:
            response = result.get('response', '')
            print(f"       ✓ Response: {len(response)} chars")
        else:
            print(f"       ✗ Request failed")

        # Delay between queries to simulate thinking
        time.sleep(random.uniform(1.5, 3.0))

    print(f"  ✅ Conversation complete ({len(flow)} turns)")

def main():
    """Generate long conversations."""
    print("🎸 Long Conversation Generator")
    print(f"Target: {API_URL}")
    print("=" * 70)

    # Check if server is running
    try:
        health = requests.get(f"{API_URL}/health", timeout=2)
        print(f"✓ Server status: {health.json()}\n")
    except Exception as e:
        print(f"✗ Server not responding: {e}")
        return

    # Generate 5 long conversations
    num_conversations = 5
    print(f"Generating {num_conversations} long conversations (30+ queries total)...\n")

    for i in range(num_conversations):
        generate_long_conversation(i + 1)

        # Delay between conversations
        if i < num_conversations - 1:
            delay = random.uniform(2.0, 4.0)
            print(f"\n  ⏸️  Pausing {delay:.1f}s before next conversation...\n")
            time.sleep(delay)

    print("\n" + "=" * 70)
    print(f"✅ Generated {num_conversations} long conversations!")
    print("These multi-turn conversations will show high prompt token usage in Grafana.")
    print(f"Query in Tempo: {{service.name=\"music-store-assistant\"}}")

if __name__ == "__main__":
    main()
