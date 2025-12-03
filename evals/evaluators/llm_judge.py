"""LLM-as-Judge evaluators for quality assessment.

These evaluators use an LLM to assess subjective qualities of responses:
- Helpfulness: Is the response helpful and complete?
- Clarity: Is the response clear and easy to understand?
- Appropriateness: Does the response stay in character as a music store assistant?
"""

from openevals.llm import create_llm_as_judge


# Custom prompt for evaluating music store assistant responses
HELPFULNESS_PROMPT = """You are evaluating a customer support chatbot for a music store called "Algorhythm".

The chatbot should:
1. Answer questions about music catalog (artists, albums, genres)
2. Help with account and invoice queries
3. Process refund requests appropriately
4. Stay in character as a helpful music store assistant

Given the user's question and the assistant's response, evaluate if the response is HELPFUL.

A helpful response:
- Directly addresses the user's question
- Provides relevant information from the catalog/database
- Is complete (doesn't leave the user hanging)
- Acknowledges if information is not available

User Question: {inputs}

Assistant Response: {outputs}

Is this response helpful? Answer with just "Yes" or "No", then explain briefly.
"""

CLARITY_PROMPT = """You are evaluating a customer support chatbot response for clarity.

A clear response:
- Is easy to understand
- Is well-organized (lists, formatting where appropriate)
- Doesn't ramble or include unnecessary information
- Uses appropriate language for a customer

User Question: {inputs}

Assistant Response: {outputs}

Is this response clear and well-written? Answer with just "Yes" or "No", then explain briefly.
"""

IN_CHARACTER_PROMPT = """You are evaluating if a customer support chatbot stays in character.

The chatbot is for "Algorhythm", a music store. It should:
- Only discuss music, catalog, and account topics
- Politely redirect off-topic questions
- Not pretend to have capabilities it doesn't have
- Not make up information about music not in its catalog

User Question: {inputs}

Assistant Response: {outputs}

Does the assistant appropriately stay in character as a music store assistant? 
Answer with just "Yes" or "No", then explain briefly.
"""


def create_helpfulness_evaluator(model: str = "openai:gpt-4o-mini"):
    """Create an LLM-as-judge evaluator for helpfulness."""
    return create_llm_as_judge(
        prompt=HELPFULNESS_PROMPT,
        model=model,
        feedback_key="helpfulness",
    )


def create_clarity_evaluator(model: str = "openai:gpt-4o-mini"):
    """Create an LLM-as-judge evaluator for clarity."""
    return create_llm_as_judge(
        prompt=CLARITY_PROMPT,
        model=model,
        feedback_key="clarity",
    )


def create_in_character_evaluator(model: str = "openai:gpt-4o-mini"):
    """Create an LLM-as-judge evaluator for staying in character."""
    return create_llm_as_judge(
        prompt=IN_CHARACTER_PROMPT,
        model=model,
        feedback_key="in_character",
    )


def get_llm_evaluators(model: str = "openai:gpt-4o-mini") -> list:
    """Get all LLM-as-judge evaluators."""
    return [
        create_helpfulness_evaluator(model),
        create_clarity_evaluator(model),
        create_in_character_evaluator(model),
    ]
