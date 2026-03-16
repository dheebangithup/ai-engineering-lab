import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.retail_agent import RetailAgent

async def main():
    agent = RetailAgent()
    agent.reset_conversation()
    
    print("\n--- Efficiency Test: One-Turn Query (Using Pre-cached Skill Schema) ---")
    print("Asking: 'Who are our top customers?' (Triggering Business Intelligence skill)")
    async for event in agent.stream_ask("Who are our top customers?"):
        if event['type'] == 'text':
            print(event['content'], end="")
        elif event['type'] == 'tool_start':
            print(f"\n[Tool Use: {event['name']}]")
            # If the first tool is execute_sql_query, the optimization is working!
    
    print("\n\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(main())
