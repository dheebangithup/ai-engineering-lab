import json

from tools.sql_tool import SQLAnalystToolkit, get_tool_definitions
from anthropic import Anthropic, DefaultAioHttpClient


class ClaudeSQLAgent:

    def __init__(self):
        self.client = Anthropic()

        self.toolkit = SQLAnalystToolkit()
        self.toolkit.initialize()

        self.tools = get_tool_definitions()

    def ask(self, question: str):

        messages = [
            {
                "role": "user",
                "content": question
            }
        ]

        system_prompt = """
You are a professional data analyst.

When answering questions about data:
1. Always inspect database schema first
2. Generate safe SQL queries
3. Use tools to retrieve data
4. Summarize results clearly
"""

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=system_prompt,
            tools=self.tools,
            messages=messages
        )

        # Agentic loop: keep going until Claude stops calling tools
        while response.stop_reason == "tool_use":
            # Process all tool_use blocks in this response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    print(f"\n🔧 Claude calling tool: {tool_name}")

                    if tool_name == "get_database_schema":
                        result = self.toolkit.get_schema()
                    elif tool_name == "execute_sql_query":
                        result = self.toolkit.execute_query(
                            tool_input["query"],
                            tool_input["explanation"]
                        )
                    else:
                        result = {"error": "Unknown tool"}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            # Append assistant response + all tool results
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Call the API again with updated messages
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system=system_prompt,
                tools=self.tools,
                messages=messages
            )

        # Extract final text response
        for block in response.content:
            if block.type == "text":
                return block.text

        return "No response generated."