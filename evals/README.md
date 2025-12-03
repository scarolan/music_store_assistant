# 📊 LangSmith Evaluations

This directory contains the evaluation framework for comparing model performance across the Music Store Assistant.

## Overview

We use **LangSmith Evaluations** to:
- Compare different LLM providers (OpenAI, Anthropic, Google)
- Track quality metrics over time
- Run pairwise A/B comparisons
- Catch regressions before deployment

## Quick Start

### 1. Upload the Golden Dataset

First, create the evaluation dataset in LangSmith:

```bash
uv run python evals/datasets/create_datasets.py
```

This uploads 50 comprehensive test cases covering:
- Music catalog queries (artists, albums, genres, songs)
- Account support queries
- Refund requests (HITL triggers)
- Edge cases and complex queries

### 2. Run Model Comparison

Run experiments across all 4 model configurations:

```bash
# Run all models (takes ~10-15 minutes)
uv run python evals/experiments/run_model_comparison.py

# Run specific model only
uv run python evals/experiments/run_model_comparison.py --model gpt-4o-mini

# Skip LLM-as-judge for faster iteration
uv run python evals/experiments/run_model_comparison.py --no-llm-judge
```

### 3. View Results in LangSmith

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Navigate to **Datasets & Experiments**
3. Select `music-store-assistant-golden`
4. Compare experiments side-by-side

### 4. Run Pairwise Comparison (Optional)

For head-to-head model battles:

```bash
# Compare latest experiments for two models
uv run python evals/experiments/run_pairwise.py --model1 gpt-4o-mini --model2 claude-haiku

# Compare specific experiments
uv run python evals/experiments/run_pairwise.py --exp1 "music-store-gpt-4o-mini-20241203" --exp2 "music-store-claude-haiku-20241203"
```

## Model Configurations

| Model Key | Models Used | Notes |
|-----------|-------------|-------|
| `gpt-4o` | GPT-4o everywhere | Quality ceiling |
| `gpt-4o-mini` | GPT-4o-mini everywhere | Baseline (default) |
| `claude-haiku` | Claude 3.5 Haiku everywhere | Speed optimized |
| `gemini-flash` | Gemini 2.0 Flash everywhere | Cost optimized |

## Evaluators

### Custom Evaluators (Fast, Deterministic)

| Evaluator | What it Checks |
|-----------|----------------|
| `routing_accuracy` | Did supervisor route to correct agent? |
| `tool_selection` | Did agent use the expected tool? |
| `contains_check` | Does response contain expected content? |
| `hallucination_check` | Did response make up content not in DB? |
| `hitl_trigger` | Did refund request trigger HITL? |

### LLM-as-Judge Evaluators (Slower, Subjective)

| Evaluator | What it Assesses |
|-----------|------------------|
| `helpfulness` | Is the response helpful and complete? |
| `clarity` | Is the response clear and well-organized? |
| `in_character` | Does it stay in character as music store assistant? |

## Directory Structure

```
evals/
├── datasets/
│   ├── create_datasets.py    # Upload dataset to LangSmith
│   └── golden_examples.json  # 50 test cases with expected outputs
├── evaluators/
│   ├── custom.py             # Deterministic evaluators
│   └── llm_judge.py          # LLM-as-judge evaluators
├── experiments/
│   ├── run_model_comparison.py  # Multi-model experiments
│   └── run_pairwise.py          # Head-to-head comparisons
└── README.md                 # This file
```

## Adding Test Cases

Edit `evals/datasets/golden_examples.json` and add new examples:

```json
{
  "id": "music-051",
  "category": "music_artist_albums",
  "inputs": {"message": "Your test message here"},
  "expected": {
    "route": "music",
    "tool": "get_albums_by_artist",
    "contains": ["Expected", "content"],
    "not_contains": ["Hallucination"]
  }
}
```

Then re-run the upload:

```bash
uv run python evals/datasets/create_datasets.py
```

## Demo Script

For demos, run experiments while explaining:

1. **Show the dataset** - Navigate to Datasets & Experiments in LangSmith
2. **Run comparison** - `uv run python evals/experiments/run_model_comparison.py --model gpt-4o-mini`
3. **View traces** - Click into individual runs to see reasoning
4. **Compare models** - Select multiple experiments and click "Compare"
5. **Pairwise battle** - Run `run_pairwise.py` for head-to-head

## Cost Considerations

Approximate costs per full run (50 examples × 4 models = 200 evaluations):

| Component | Cost Estimate |
|-----------|---------------|
| Target function calls | ~$0.50-2.00 |
| LLM-as-judge (3 judges × 200) | ~$0.30-0.50 |
| Pairwise comparison (50 judgments) | ~$0.05-0.10 |
| **Total per full comparison** | **~$1-3** |

Use `--no-llm-judge` to reduce costs during development.

## Troubleshooting

### Dataset not found
```bash
uv run python evals/datasets/create_datasets.py
```

### Missing API keys
Ensure `.env` has:
```bash
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=lsv2_...
ANTHROPIC_API_KEY=sk-ant-...  # For Claude
GOOGLE_API_KEY=...            # For Gemini
```

### Experiment failed for one model
Check that the required API key is set for that provider.
