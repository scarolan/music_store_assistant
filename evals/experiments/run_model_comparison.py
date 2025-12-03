"""Run evaluation experiments across multiple models.

This script runs the same golden dataset through different model configurations
and records the results as separate experiments in LangSmith.

Usage:
    # Run all models
    uv run python evals/experiments/run_model_comparison.py

    # Run specific model
    uv run python evals/experiments/run_model_comparison.py --model gpt-4o-mini

    # Run with custom concurrency
    uv run python evals/experiments/run_model_comparison.py --concurrency 4
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langsmith import Client

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evals.evaluators.custom import EVALUATORS
from evals.evaluators.llm_judge import get_llm_evaluators
from src.graph import create_graph

# Load environment variables
load_dotenv()

# Dataset name (must match what create_datasets.py creates)
DATASET_NAME = "music-store-assistant-golden"

# Model configurations to compare
MODEL_CONFIGS = {
    "gpt-4o": {
        "display_name": "GPT-4o (Quality Ceiling)",
        "env_vars": {
            "SUPERVISOR_MODEL": "gpt-4o",
            "MUSIC_EXPERT_MODEL": "gpt-4o",
            "SUPPORT_REP_MODEL": "gpt-4o",
        },
    },
    "gpt-4o-mini": {
        "display_name": "GPT-4o-mini (Baseline)",
        "env_vars": {
            "SUPERVISOR_MODEL": "gpt-4o-mini",
            "MUSIC_EXPERT_MODEL": "gpt-4o-mini",
            "SUPPORT_REP_MODEL": "gpt-4o-mini",
        },
    },
    "claude-haiku": {
        "display_name": "Claude 3.5 Haiku (Speed)",
        "env_vars": {
            "SUPERVISOR_MODEL": "claude-3-5-haiku-20241022",
            "MUSIC_EXPERT_MODEL": "claude-3-5-haiku-20241022",
            "SUPPORT_REP_MODEL": "claude-3-5-haiku-20241022",
        },
    },
    "gemini-flash": {
        "display_name": "Gemini 2.0 Flash (Cost)",
        "env_vars": {
            "SUPERVISOR_MODEL": "gemini-2.0-flash",
            "MUSIC_EXPERT_MODEL": "gemini-2.0-flash",
            "SUPPORT_REP_MODEL": "gemini-2.0-flash",
        },
    },
}


def create_target_function(model_key: str):
    """Create a target function for evaluation with specific model config.

    Returns a function that invokes the graph with the given model configuration.
    """
    config = MODEL_CONFIGS[model_key]

    def target(inputs: dict) -> dict:
        """Target function for LangSmith evaluation."""
        # Set environment variables for this model
        original_env = {}
        for key, value in config["env_vars"].items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            # Create fresh graph with these model settings
            graph = create_graph()

            # Build state with customer_id
            state = {
                "messages": [HumanMessage(content=inputs["message"])],
                "customer_id": 16,  # Default demo customer
            }

            # Invoke graph
            result = graph.invoke(
                state,
                config={"configurable": {"customer_id": 16}},
            )

            return result

        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    return target


def run_experiment(
    client: Client,
    model_key: str,
    max_concurrency: int = 2,
    use_llm_judge: bool = True,
) -> str:
    """Run evaluation experiment for a specific model.

    Args:
        client: LangSmith client
        model_key: Key from MODEL_CONFIGS
        max_concurrency: Number of concurrent evaluations
        use_llm_judge: Whether to include LLM-as-judge evaluators

    Returns:
        Experiment ID
    """
    config = MODEL_CONFIGS[model_key]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    experiment_prefix = f"music-store-{model_key}-{timestamp}"

    print(f"\n{'='*60}")
    print(f"Running experiment: {config['display_name']}")
    print(f"Experiment prefix: {experiment_prefix}")
    print(f"{'='*60}")

    # Build evaluator list
    evaluators = EVALUATORS.copy()

    if use_llm_judge:
        # Use GPT-4o-mini as the judge model (fast and cheap)
        evaluators.extend(get_llm_evaluators("openai:gpt-4o-mini"))

    # Create target function
    target = create_target_function(model_key)

    # Run evaluation
    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        max_concurrency=max_concurrency,
        metadata={
            "model_key": model_key,
            "model_config": config["env_vars"],
            "timestamp": timestamp,
        },
    )

    print(f"\n✅ Experiment complete: {experiment_prefix}")
    print(f"   Results: {results}")

    return experiment_prefix


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run model comparison experiments"
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_CONFIGS.keys()),
        help="Run specific model only (default: all models)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Max concurrent evaluations (default: 2)",
    )
    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="Skip LLM-as-judge evaluators (faster, cheaper)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available model configurations",
    )

    args = parser.parse_args()

    if args.list_models:
        print("\nAvailable model configurations:")
        for key, config in MODEL_CONFIGS.items():
            print(f"  {key}: {config['display_name']}")
            for env_key, env_val in config["env_vars"].items():
                print(f"    {env_key}={env_val}")
        return

    client = Client()

    # Verify dataset exists
    datasets = list(client.list_datasets(dataset_name=DATASET_NAME))
    if not datasets:
        print(f"❌ Dataset '{DATASET_NAME}' not found!")
        print("   Run: uv run python evals/datasets/create_datasets.py")
        sys.exit(1)

    print(f"Found dataset: {DATASET_NAME}")

    # Determine which models to run
    models_to_run = [args.model] if args.model else list(MODEL_CONFIGS.keys())

    print(f"\nWill run experiments for: {models_to_run}")
    print(f"LLM-as-judge: {'disabled' if args.no_llm_judge else 'enabled'}")
    print(f"Concurrency: {args.concurrency}")

    # Run experiments
    experiment_ids = []
    for model_key in models_to_run:
        try:
            exp_id = run_experiment(
                client,
                model_key,
                max_concurrency=args.concurrency,
                use_llm_judge=not args.no_llm_judge,
            )
            experiment_ids.append((model_key, exp_id))
        except Exception as e:
            print(f"❌ Failed to run {model_key}: {e}")
            continue

    # Summary
    print("\n" + "="*60)
    print("EXPERIMENT SUMMARY")
    print("="*60)
    for model_key, exp_id in experiment_ids:
        print(f"  {model_key}: {exp_id}")

    print("\n🔗 View results at: https://smith.langchain.com/datasets")
    print("   Compare experiments in the Datasets & Experiments view")


if __name__ == "__main__":
    main()
