"""Evaluators for Music Store Assistant.

This module provides custom evaluators for grading the assistant's responses:
- Routing accuracy: Did the supervisor route to the correct agent?
- Tool selection: Did the agent use the expected tool?
- Hallucination detection: Did the response make up content not in the DB?
- Response quality: LLM-as-judge for helpfulness and clarity
"""

from langchain_core.messages import AIMessage
from langsmith.schemas import Example, Run


def routing_evaluator(run: Run, example: Example) -> dict:
    """Evaluate whether the supervisor routed to the correct agent.

    Checks if the 'route' in the run output matches the expected route.

    Returns:
        dict with 'key' and 'score' (1.0 for correct, 0.0 for incorrect)
    """
    expected_route = example.outputs.get("route") if example.outputs else None
    actual_route = run.outputs.get("route") if run.outputs else None

    if expected_route is None:
        return {"key": "routing_accuracy", "score": None, "comment": "No expected route"}

    is_correct = actual_route == expected_route

    return {
        "key": "routing_accuracy",
        "score": 1.0 if is_correct else 0.0,
        "comment": f"Expected: {expected_route}, Got: {actual_route}",
    }


def tool_selection_evaluator(run: Run, example: Example) -> dict:
    """Evaluate whether the agent selected the expected tool.

    Examines the message history for tool calls and checks against expected.

    Returns:
        dict with 'key' and 'score' (1.0 for correct, 0.0 for incorrect)
    """
    expected_tool = example.outputs.get("tool") if example.outputs else None

    # If no tool expected, check that no tool was called
    if expected_tool is None:
        return {"key": "tool_selection", "score": None, "comment": "No expected tool"}

    # Extract tool calls from the run
    messages = run.outputs.get("messages", []) if run.outputs else []
    tool_calls_found = []

    for msg in messages:
        # Handle both dict and object representations
        if isinstance(msg, dict):
            if msg.get("type") == "ai" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tool_calls_found.append(tc.get("name", ""))
        elif isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_found.append(tc.get("name", ""))

    # Check if expected tool was called
    tool_found = expected_tool in tool_calls_found

    return {
        "key": "tool_selection",
        "score": 1.0 if tool_found else 0.0,
        "comment": f"Expected: {expected_tool}, Found: {tool_calls_found}",
    }


def contains_evaluator(run: Run, example: Example) -> dict:
    """Evaluate whether the response contains expected content.

    Checks if specified strings appear in the final response.

    Returns:
        dict with 'key' and 'score' (proportion of expected items found)
    """
    expected_contains = example.outputs.get("contains", []) if example.outputs else []

    if not expected_contains:
        return {"key": "contains_check", "score": None, "comment": "No contains criteria"}

    # Get the final response text
    response_text = _extract_response_text(run)

    # Check each expected string (case-insensitive)
    found_count = 0
    missing = []

    for expected in expected_contains:
        if expected.lower() in response_text.lower():
            found_count += 1
        else:
            missing.append(expected)

    score = found_count / len(expected_contains)

    return {
        "key": "contains_check",
        "score": score,
        "comment": f"Found {found_count}/{len(expected_contains)}. Missing: {missing}",
    }


def not_contains_evaluator(run: Run, example: Example) -> dict:
    """Evaluate that response does NOT contain forbidden content (hallucination check).

    Checks that specified strings do NOT appear in the response.
    Useful for catching hallucinations about content not in the database.

    Returns:
        dict with 'key' and 'score' (1.0 if none found, 0.0 if hallucination detected)
    """
    not_contains = example.outputs.get("not_contains", []) if example.outputs else []

    if not not_contains:
        return {"key": "hallucination_check", "score": None, "comment": "No not_contains criteria"}

    # Get the final response text
    response_text = _extract_response_text(run)

    # Check that none of the forbidden strings appear
    hallucinations = []

    for forbidden in not_contains:
        if forbidden.lower() in response_text.lower():
            hallucinations.append(forbidden)

    score = 1.0 if not hallucinations else 0.0

    return {
        "key": "hallucination_check",
        "score": score,
        "comment": f"Hallucinations found: {hallucinations}" if hallucinations else "No hallucinations",
    }


def hitl_trigger_evaluator(run: Run, example: Example) -> dict:
    """Evaluate whether HITL was properly triggered for refund requests.

    Checks if the graph interrupted before refund_tools as expected.

    Returns:
        dict with 'key' and 'score'
    """
    expected_hitl = example.outputs.get("hitl_required", False) if example.outputs else False

    if not expected_hitl:
        return {"key": "hitl_trigger", "score": None, "comment": "HITL not expected"}

    # Check if process_refund tool was called (which triggers HITL)
    messages = run.outputs.get("messages", []) if run.outputs else []
    refund_tool_called = False

    for msg in messages:
        if isinstance(msg, dict):
            if msg.get("type") == "ai" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("name") == "process_refund":
                        refund_tool_called = True
        elif isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get("name") == "process_refund":
                    refund_tool_called = True

    return {
        "key": "hitl_trigger",
        "score": 1.0 if refund_tool_called else 0.0,
        "comment": "process_refund called" if refund_tool_called else "process_refund NOT called",
    }


def _extract_response_text(run: Run) -> str:
    """Extract the final assistant response text from a run."""
    messages = run.outputs.get("messages", []) if run.outputs else []

    # Find the last AI message that's not from the supervisor
    for msg in reversed(messages):
        if isinstance(msg, dict):
            if msg.get("type") == "ai" and msg.get("name") != "supervisor":
                content = msg.get("content", "")
                if content:
                    return content
        elif isinstance(msg, AIMessage):
            if getattr(msg, "name", None) != "supervisor" and msg.content:
                return str(msg.content)

    return ""


# Export all evaluators
EVALUATORS = [
    routing_evaluator,
    tool_selection_evaluator,
    contains_evaluator,
    not_contains_evaluator,
    hitl_trigger_evaluator,
]
