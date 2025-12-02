#!/usr/bin/env python3
"""Report token usage and costs from LangSmith for test runs.

This script queries LangSmith for traces tagged with 'test' and/or 'ci-cd'
and generates a cost report. Run after pytest to see your token burn.

Usage:
    # After running tests:
    uv run python scripts/report_test_costs.py
    
    # For CI runs specifically:
    uv run python scripts/report_test_costs.py --tag ci-cd
    
    # Last N minutes (default 10):
    uv run python scripts/report_test_costs.py --minutes 30
"""

import argparse
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment
load_dotenv()


def get_test_run_costs(tag: str = "test", minutes: int = 10) -> dict:
    """Query LangSmith for test run costs.
    
    Args:
        tag: Filter traces by this tag (e.g., 'test', 'ci-cd')
        minutes: Look back this many minutes
        
    Returns:
        dict with token counts and cost estimates
    """
    from langsmith import Client
    
    client = Client()
    
    # Calculate time window
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes)
    
    # Query runs with the specified tag
    runs = list(client.list_runs(
        project_name=os.getenv("LANGCHAIN_PROJECT", "music-store-assistant"),
        filter=f'has(tags, "{tag}")',
        start_time=start_time,
        end_time=end_time,
    ))
    
    # Aggregate token usage
    stats = {
        "total_runs": len(runs),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "runs_with_tokens": 0,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "tag": tag,
    }
    
    for run in runs:
        if run.prompt_tokens or run.completion_tokens:
            stats["runs_with_tokens"] += 1
            stats["prompt_tokens"] += run.prompt_tokens or 0
            stats["completion_tokens"] += run.completion_tokens or 0
            stats["total_tokens"] += run.total_tokens or 0
    
    # Estimate costs (GPT-4o-mini pricing as default)
    # Input: $0.15 per 1M tokens, Output: $0.60 per 1M tokens
    input_cost = (stats["prompt_tokens"] / 1_000_000) * 0.15
    output_cost = (stats["completion_tokens"] / 1_000_000) * 0.60
    stats["estimated_cost_gpt4o_mini"] = input_cost + output_cost
    
    # GPT-4o pricing for comparison
    # Input: $2.50 per 1M tokens, Output: $10.00 per 1M tokens
    input_cost_4o = (stats["prompt_tokens"] / 1_000_000) * 2.50
    output_cost_4o = (stats["completion_tokens"] / 1_000_000) * 10.00
    stats["estimated_cost_gpt4o"] = input_cost_4o + output_cost_4o
    
    return stats


def format_report(stats: dict) -> str:
    """Format stats as a human-readable report."""
    lines = [
        "",
        "=" * 65,
        "🔥 LANGSMITH TEST RUN COST REPORT",
        "=" * 65,
        f"  Time Window:          {stats['start_time'][:19]} to {stats['end_time'][:19]}",
        f"  Filter Tag:           {stats['tag']}",
        "-" * 65,
        f"  Total Traces:         {stats['total_runs']:,}",
        f"  Traces with Tokens:   {stats['runs_with_tokens']:,}",
        "-" * 65,
        f"  Prompt Tokens:        {stats['prompt_tokens']:,}",
        f"  Completion Tokens:    {stats['completion_tokens']:,}",
        f"  Total Tokens:         {stats['total_tokens']:,}",
        "-" * 65,
        "  💰 Estimated Costs:",
        f"     GPT-4o-mini:       ${stats['estimated_cost_gpt4o_mini']:.4f}",
        f"     GPT-4o:            ${stats['estimated_cost_gpt4o']:.4f}",
        "-" * 65,
        "  📊 CI/CD Budget Projection (100 runs/month):",
        f"     GPT-4o-mini:       ${stats['estimated_cost_gpt4o_mini'] * 100:.2f}/month",
        f"     GPT-4o:            ${stats['estimated_cost_gpt4o'] * 100:.2f}/month",
        "=" * 65,
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Report LangSmith test costs")
    parser.add_argument("--tag", default="test", help="Tag to filter by (default: test)")
    parser.add_argument("--minutes", type=int, default=10, help="Look back N minutes (default: 10)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    try:
        stats = get_test_run_costs(tag=args.tag, minutes=args.minutes)
        
        if args.json:
            import json
            print(json.dumps(stats, indent=2))
        else:
            print(format_report(stats))
            
    except Exception as e:
        print(f"Error querying LangSmith: {e}")
        print("\nMake sure you have LANGCHAIN_API_KEY set in your .env file")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
