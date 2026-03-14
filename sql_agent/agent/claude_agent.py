"""
Claude SQL Agent using the modern Anthropic Python SDK.

Uses `@beta_tool` decorated functions with `tool_runner` for automatic
tool-use orchestration — no manual agentic loop needed.
"""

import anthropic
from anthropic import Anthropic
from tools.sql_tool import ALL_TOOLS, initialize_tools, cleanup_tools
from config import Config


class ClaudeSQLAgent:
    """SQL analyst agent powered by Claude with automatic tool orchestration."""

    def __init__(self, model: str = None):
        self.model = model or Config.MODEL
        self.client = Anthropic(
            max_retries=Config.MAX_RETRIES,
            timeout=Config.TIMEOUT,
        )
        self.messages = []  # Conversation memory

        # Initialize tools (connects to database)
        initialize_tools()

    def ask(self, question: str) -> str:
        """
        Ask the agent a question. Uses tool_runner to automatically
        handle the tool-use loop (schema lookup → SQL execution → summary).

        Args:
            question: Natural language question about the data.

        Returns:
            The agent's text response with data insights.
        """
        # Add user message to conversation history
        self.messages.append({"role": "user", "content": question})

        try:
            # tool_runner auto-handles the agentic loop:
            #   1. Sends the message to Claude
            #   2. If Claude wants to call a tool, it calls it automatically
            #   3. Sends the tool result back to Claude
            #   4. Repeats until Claude gives a final text response
            runner = self.client.beta.messages.tool_runner(
                model=self.model,
                max_tokens=Config.MAX_TOKENS,
                system=Config.SYSTEM_PROMPT,
                tools=ALL_TOOLS,
                messages=self.messages,
            )

            final_response = None
            for message in runner:
                # Each iteration is an API round-trip
                # The runner auto-executes tool calls and feeds results back
                final_response = message

            # Extract the final text from the last message
            if final_response:
                # Add assistant response to conversation memory
                self.messages.append({
                    "role": "assistant",
                    "content": final_response.content,
                })

                # Extract text from content blocks
                text_parts = []
                for block in final_response.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)

                if text_parts:
                    return "\n".join(text_parts)

            return "No response generated."

        except anthropic.AuthenticationError:
            return "❌ Authentication failed. Please check your ANTHROPIC_API_KEY in .env"

        except anthropic.RateLimitError:
            return "⏳ Rate limit exceeded. Please wait a moment and try again."

        except anthropic.APIConnectionError as e:
            return f"🌐 Connection error: Could not reach the Anthropic API.\n   {e.__cause__}"

        except anthropic.APIStatusError as e:
            return f"❌ API error ({e.status_code}): {e.message}"

    def reset_conversation(self):
        """Clear conversation history to start fresh."""
        self.messages = []
        print("🔄 Conversation history cleared.")

    def cleanup(self):
        """Release resources."""
        cleanup_tools()