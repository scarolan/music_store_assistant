"""Run pairwise comparisons between model experiments.

This script compares two experiments head-to-head using an LLM judge
to determine which model produces better responses.

Usage:
    # Compare two specific experiments
    uv run python evals/experiments/run_pairwise.py --exp1 "music-store-gpt-4o-mini-xxx" --exp2 "music-store-claude-haiku-xxx"

    # Compare latest experiments for two models
    uv run python evals/experiments/run_pairwise.py --model1 gpt-4o-mini --model2 claude-haiku
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
load_dotenv()

DATASET_NAME = "music-store-assistant-golden"

# Pairwise comparison prompt
PAIRWISE_PROMPT = """You are comparing two responses from customer support chatbots for a music store.

User Question: {inputs}

Response A:
{outputs_a}

Response B:
{outputs_b}

Which response is better for a music store customer support bot? Consider:
1. Helpfulness - Does it answer the question?
2. Accuracy - Is the information correct?
3. Clarity - Is it easy to understand?
4. Appropriateness - Does it stay on topic as a music store assistant?

Answer with just "A" or "B" (or "TIE" if truly equal), then explain briefly why.
"""


def extract_response_text(outputs: dict) -> str:
    """Extract the final response text from graph outputs."""
    messages = outputs.get("messages", [])

    for msg in reversed(messages):
        if isinstance(msg, dict):
            if msg.get("type") == "ai" and msg.get("name") != "supervisor":
                content = msg.get("content", "")
                if content:
                    return content
        else:
            # Handle message objects
            if hasattr(msg, "type") and msg.type == "ai":
                if getattr(msg, "name", None) != "supervisor" and msg.content:
                    return str(msg.content)

    return "[No response]"


def find_latest_experiment(client: Client, model_key: str) -> str | None:
    """Find the most recent experiment for a given model key."""
    # List experiments for the dataset
    datasets = list(client.list_datasets(dataset_name=DATASET_NAME))
    if not datasets:
        return None

    dataset_id = datasets[0].id

    # Get projects (experiments) for this dataset
    projects = list(client.list_projects(reference_dataset_id=dataset_id))

    # Filter by model key in name and sort by created_at
    matching = [p for p in projects if model_key in p.name]
    if not matching:
        return None

    # Sort by creation time (most recent first)
    matching.sort(key=lambda p: p.created_at, reverse=True)

    return matching[0].name


def run_pairwise_comparison(
    client: Client,
    experiment_a: str,
    experiment_b: str,
    judge_model: str = "openai:gpt-4o-mini",
) -> dict:
    """Run pairwise comparison between two experiments.

    Args:
        client: LangSmith client
        experiment_a: Name of first experiment
        experiment_b: Name of second experiment
        judge_model: Model to use as judge

    Returns:
        dict with comparison results
    """
    print(f"\n{'='*60}")
    print("PAIRWISE COMPARISON")
    print(f"{'='*60}")
    print(f"Experiment A: {experiment_a}")
    print(f"Experiment B: {experiment_b}")
    print(f"Judge model: {judge_model}")
    print(f"{'='*60}\n")

    # Get runs from both experiments
    runs_a = {
        r.reference_example_id: r
        for r in client.list_runs(project_name=experiment_a, is_root=True)
    }
    runs_b = {
        r.reference_example_id: r
        for r in client.list_runs(project_name=experiment_b, is_root=True)
    }

    # Find common examples
    common_examples = set(runs_a.keys()) & set(runs_b.keys())
    print(f"Found {len(common_examples)} common examples to compare\n")

    if not common_examples:
        print("❌ No common examples found between experiments!")
        return {}

    # Track results
    results = {
        "a_wins": 0,
        "b_wins": 0,
        "ties": 0,
        "comparisons": [],
    }

    # Create pairwise evaluator
    from langchain_openai import ChatOpenAI

    judge = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    for i, example_id in enumerate(common_examples):
        run_a = runs_a[example_id]
        run_b = runs_b[example_id]

        # Get input
        inputs = run_a.inputs.get("message", "[Unknown input]")

        # Get responses
        response_a = extract_response_text(run_a.outputs or {})
        response_b = extract_response_text(run_b.outputs or {})

        # Ask judge
        prompt = PAIRWISE_PROMPT.format(
            inputs=inputs,
            outputs_a=response_a,
            outputs_b=response_b,
        )

        try:
            judgment = judge.invoke(prompt)
            judgment_text = judgment.content.strip()

            # Parse result
            if judgment_text.upper().startswith("A"):
                winner = "A"
                results["a_wins"] += 1
            elif judgment_text.upper().startswith("B"):
                winner = "B"
                results["b_wins"] += 1
            else:
                winner = "TIE"
                results["ties"] += 1

            results["comparisons"].append({
                "example_id": str(example_id),
                "input": inputs,
                "winner": winner,
                "judgment": judgment_text[:200],
            })

            print(f"[{i+1}/{len(common_examples)}] Winner: {winner}")

        except Exception as e:
            print(f"[{i+1}/{len(common_examples)}] Error: {e}")
            results["ties"] += 1

    # Summary
    total = results["a_wins"] + results["b_wins"] + results["ties"]
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Experiment A wins: {results['a_wins']} ({100*results['a_wins']/total:.1f}%)")
    print(f"Experiment B wins: {results['b_wins']} ({100*results['b_wins']/total:.1f}%)")
    print(f"Ties: {results['ties']} ({100*results['ties']/total:.1f}%)")
    print(f"{'='*60}")

    if results["a_wins"] > results["b_wins"]:
        print(f"\n🏆 WINNER: {experiment_a}")
    elif results["b_wins"] > results["a_wins"]:
        print(f"\n🏆 WINNER: {experiment_b}")
    else:
        print("\n🤝 TIE - No clear winner")

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run pairwise comparison between experiments"
    )
    parser.add_argument(
        "--exp1",
        help="Name of first experiment",
    )
    parser.add_argument(
        "--exp2",
        help="Name of second experiment",
    )
    parser.add_argument(
        "--model1",
        help="Find latest experiment for this model key",
    )
    parser.add_argument(
        "--model2",
        help="Find latest experiment for this model key",
    )
    parser.add_argument(
        "--judge",
        default="openai:gpt-4o-mini",
        help="Model to use as judge (default: openai:gpt-4o-mini)",
    )

    args = parser.parse_args()

    client = Client()

    # Resolve experiment names
    if args.exp1 and args.exp2:
        exp1 = args.exp1
        exp2 = args.exp2
    elif args.model1 and args.model2:
        print(f"Finding latest experiments for {args.model1} and {args.model2}...")
        exp1 = find_latest_experiment(client, args.model1)
        exp2 = find_latest_experiment(client, args.model2)

        if not exp1:
            print(f"❌ No experiment found for {args.model1}")
            sys.exit(1)
        if not exp2:
            print(f"❌ No experiment found for {args.model2}")
            sys.exit(1)

        print(f"Found: {exp1}")
        print(f"Found: {exp2}")
    else:
        print("❌ Must provide either --exp1/--exp2 or --model1/--model2")
        parser.print_help()
        sys.exit(1)

    # Run comparison
    results = run_pairwise_comparison(client, exp1, exp2, args.judge)

    # Print full results if requested
    print("\nDetailed comparisons:")
    for comp in results.get("comparisons", [])[:5]:
        print(f"\n  Input: {comp['input'][:50]}...")
        print(f"  Winner: {comp['winner']}")
        print(f"  Reason: {comp['judgment'][:100]}...")


if __name__ == "__main__":
    main()
