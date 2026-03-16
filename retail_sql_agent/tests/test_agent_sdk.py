import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.retail_agent import RetailAgent

async def main():
    agent = RetailAgent()
    agent.reset_conversation()
    
    print("\n--- Turn 1: Get Schema ---")
    async for event in agent.stream_ask("Can you get the database schema?"):
        if event['type'] == 'text':
            print(event['content'], end="")
    
    print("\n\n--- Turn 2: Query (Should remember schema) ---")
    async for event in agent.stream_ask("How many products do we have?"):
        if event['type'] == 'text':
            print(event['content'], end="")
        elif event['type'] == 'tool_start':
            print(f"\n[Tool Use: {event['name']}]")
    
    print("\n\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(main())
