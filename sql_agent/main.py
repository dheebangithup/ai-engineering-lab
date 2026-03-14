"""
SQL Agent CLI — Interactive command-line interface for querying data
using natural language powered by Claude.
"""

from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from agent.claude_agent import ClaudeSQLAgent


def main():
    agent = ClaudeSQLAgent()

    print("\n" + "=" * 50)
    print("📊  SQL Analyst Agent")
    print("=" * 50)
    print(f"Model: {agent.model}")
    print("Commands: 'exit' to quit | 'reset' to clear history")
    print("=" * 50 + "\n")

    try:
        while True:
            question = input("🔎 Ask a question: ").strip()

            if not question:
                continue

            if question.lower() == "exit":
                break

            if question.lower() == "reset":
                agent.reset_conversation()
                continue

            result = agent.ask(question)

            print(f"\n📈 Result:\n")
            print(result)
            print()  # Blank line between Q&A rounds

    except (EOFError, KeyboardInterrupt):
        print("\n")

    finally:
        agent.cleanup()
        print("👋 Goodbye!")


if __name__ == "__main__":
    main()