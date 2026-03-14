from dotenv import load_dotenv

from agent.claude_agent import ClaudeSQLAgent

load_dotenv()
def main():

    agent = ClaudeSQLAgent()

    print("\n📊 SQL Analyst Agent Ready")
    print("Type 'exit' to quit\n")

    try:
        while True:

            question = input("🔎 Ask a question: ").strip()

            if not question:
                continue

            if question.lower() == "exit":
                break

            result = agent.ask(question)

            print("\n📈 Result:\n")
            print(result)
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Goodbye!")


if __name__ == "__main__":
    main()