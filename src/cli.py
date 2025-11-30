#!/usr/bin/env python3
"""Command-line interface for the Music Store Assistant.

A simple REPL for interacting with the agent directly from the terminal.
Useful for demos, testing, and development.

Usage:
    uv run python -m src.cli
    uv run python -m src.cli --customer-id 42
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from src.graph import create_graph


def get_last_ai_response(messages: list) -> str:
    """Extract the last AI response from message history."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            # Skip routing messages from supervisor
            if msg.name == "supervisor":
                continue
            return msg.content
    return "[No response]"


def format_tool_calls(messages: list) -> list[str]:
    """Extract tool calls for verbose output."""
    tools_used = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tools_used.append(f"  🔧 {tc['name']}({tc['args']})")
        if isinstance(msg, ToolMessage):
            tools_used.append(f"  📤 Result: {msg.content[:100]}...")
    return tools_used


def main():
    """Run the interactive CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Music Store Assistant CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    uv run python -m src.cli
    uv run python -m src.cli --customer-id 42
    uv run python -m src.cli --verbose
        """,
    )
    parser.add_argument(
        "--customer-id",
        type=int,
        default=1,
        help="Customer ID for the session (default: 1)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show tool calls and routing decisions",
    )
    args = parser.parse_args()

    # Create graph with memory checkpointer for conversation persistence
    checkpointer = MemorySaver()
    graph = create_graph(checkpointer=checkpointer)

    # Session config with source tag for LangSmith filtering
    config = {
        "configurable": {
            "thread_id": "cli-session",
            "customer_id": args.customer_id,
        },
        "tags": ["source:cli"],
    }

    print("\n" + "=" * 60)
    print("🎵  Welcome to Algorhythm Music Store!")
    print("=" * 60)
    print(f"Customer ID: {args.customer_id}")
    print("Type 'quit' or 'q' to exit, 'clear' to reset conversation")
    print("-" * 60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 🎶")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "q", "exit"):
            print("\nGoodbye! 🎶")
            break

        if user_input.lower() == "clear":
            # Create fresh graph with new checkpointer
            checkpointer = MemorySaver()
            graph = create_graph(checkpointer=checkpointer)
            print("\n[Conversation cleared]\n")
            continue

        # Invoke the graph
        try:
            result = graph.invoke(
                {
                    "messages": [HumanMessage(content=user_input)],
                    "customer_id": args.customer_id,
                },
                config=config,
            )

            # Check for HITL interrupt
            state = graph.get_state(config)
            if state.next and "refund_tools" in state.next:
                print("\n🔒 **Refund Request Requires Approval**")
                print("   A supervisor needs to approve this refund.")
                approval = input("   Approve refund? (yes/no): ").strip().lower()

                if approval in ("yes", "y"):
                    # Resume the graph
                    from langgraph.types import Command

                    result = graph.invoke(Command(resume=True), config)
                    print("   ✅ Refund approved and processed!\n")
                else:
                    print("   ❌ Refund rejected.\n")
                    continue

            if args.verbose:
                tool_calls = format_tool_calls(result["messages"])
                if tool_calls:
                    print("\n[Tools Used]")
                    for tc in tool_calls:
                        print(tc)
                    print()

            response = get_last_ai_response(result["messages"])
            print(f"\n🤖 Assistant: {response}\n")

        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            if args.verbose:
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    main()
