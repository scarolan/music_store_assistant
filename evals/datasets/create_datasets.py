"""Upload golden dataset to LangSmith.

This script creates or updates the evaluation dataset in LangSmith
with our golden test cases.

Usage:
    uv run python evals/datasets/create_datasets.py
"""

import json
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

# Load environment variables
load_dotenv()

DATASET_NAME = "music-store-assistant-golden"
DATASET_DESCRIPTION = """Golden test cases for evaluating the Music Store Assistant.

Categories:
- music_artist_albums: Artist album queries
- music_artist_tracks: Artist track/song queries
- music_genre: Genre-based queries
- music_song_search: Song title searches
- music_genres_list: List all genres
- music_recommendation: Similar artist recommendations
- music_edge_case: Edge cases (artists not in DB)
- support_account: Account information queries
- support_invoice: Invoice lookup queries
- refund_hitl: Refund requests (HITL triggers)
- greeting: Greetings and general help
- edge_case: Off-topic and unusual inputs
- complex_query: Multi-part or nuanced queries
"""


def load_golden_examples() -> list[dict]:
    """Load golden examples from JSON file."""
    json_path = Path(__file__).parent / "golden_examples.json"
    with open(json_path) as f:
        data = json.load(f)
    return data["examples"]


def create_or_update_dataset(client: Client, examples: list[dict]) -> None:
    """Create or update the LangSmith dataset."""
    # Check if dataset exists
    existing_datasets = list(client.list_datasets(dataset_name=DATASET_NAME))

    if existing_datasets:
        dataset = existing_datasets[0]
        print(f"Found existing dataset: {dataset.name} (id: {dataset.id})")

        # Delete existing examples to replace with fresh ones
        existing_examples = list(client.list_examples(dataset_id=dataset.id))
        if existing_examples:
            print(f"Deleting {len(existing_examples)} existing examples...")
            for example in existing_examples:
                client.delete_example(example.id)
    else:
        # Create new dataset
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=DATASET_DESCRIPTION,
        )
        print(f"Created new dataset: {dataset.name} (id: {dataset.id})")

    # Upload examples
    print(f"Uploading {len(examples)} examples...")

    for example in examples:
        client.create_example(
            dataset_id=dataset.id,
            inputs=example["inputs"],
            outputs=example["expected"],
            metadata={
                "id": example["id"],
                "category": example["category"],
            },
        )

    print(f"✅ Successfully uploaded {len(examples)} examples to '{DATASET_NAME}'")
    print("   View at: https://smith.langchain.com/datasets")


def main():
    """Main entry point."""
    client = Client()

    # Verify connection
    print("Connecting to LangSmith...")

    examples = load_golden_examples()
    print(f"Loaded {len(examples)} golden examples")

    # Show category breakdown
    categories = {}
    for ex in examples:
        cat = ex["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategory breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    print()
    create_or_update_dataset(client, examples)


if __name__ == "__main__":
    main()
