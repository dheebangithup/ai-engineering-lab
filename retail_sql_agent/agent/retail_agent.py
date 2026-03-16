"""
Skills-based SQL Agent using the Anthropic Python SDK.

Loads SKILL.md files from .claude/skills/ automatically via the SDK 
and executes multi-turn agentic loops.
"""

import asyncio
import os
import json
import traceback
from typing import AsyncIterator, Any

from dotenv import load_dotenv
load_dotenv()

from claude_agent_sdk import query, ClaudeAgentOptions, create_sdk_mcp_server
from claude_agent_sdk.types import AssistantMessage, UserMessage, TextBlock, ToolUseBlock, ToolResultBlock, ResultMessage

from tools.database_tools import DB_TOOLS, initialize_tools, cleanup_tools
from tools.export_tools import EXPORT_TOOLS
from core.session_manager import SessionManager
from config import Config, logger

class RetailAgent:
    """
    SQL Analyst Agent using claude_agent_sdk for native tool and skill orchestration.
    """

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.session_id = None
        
        initialize_tools()
        
        self.mcp_config = create_sdk_mcp_server(
            name="retail",
            version="1.0.0",
            tools=DB_TOOLS + EXPORT_TOOLS
        )
        self.session_manager = SessionManager()

    @property
    def loaded_skills(self) -> list[str]:
        """Dynamically list skills for the UI from the .claude/skills directory."""
        skills_path = os.path.join(self.project_root, ".claude", "skills")
        if not os.path.exists(skills_path):
            return []
        return [d.replace("-", " ").title() for d in os.listdir(skills_path) 
                if os.path.isdir(os.path.join(skills_path, d))]

    async def stream_ask(self, question: str) -> AsyncIterator[dict[str, Any]]:
        options = ClaudeAgentOptions(
            cwd=self.project_root,
            setting_sources=["user", "project"],
            mcp_servers={"retail": self.mcp_config},
            allowed_tools=[
                "Skill", 
                "mcp__retail__get_database_schema", 
                "mcp__retail__execute_sql_query", 
                "mcp__retail__export_to_csv", 
                "mcp__retail__export_to_json"
            ],
            permission_mode="bypassPermissions",
            system_prompt=Config.SYSTEM_PROMPT,
            resume=self.session_id  # Use native SDK session resuming
        )

        # Record user question
        if self.session_id:
            self.session_manager.add_event(self.session_id, {"type": "user_question", "content": question})

        try:
            tool_use_map = {} 
            
            async for message in query(prompt=question, options=options):
                # Capture session_id from any message that has it
                if hasattr(message, "session_id") and message.session_id:
                    if self.session_id != message.session_id:
                        self.session_id = message.session_id
                        yield {"type": "session_id", "content": self.session_id}
                        # Now that we have an ID, record the question if it wasn't recorded
                        self.session_manager.create_or_update_session(self.session_id)
                        self.session_manager.add_event(self.session_id, {"type": "user_question", "content": question})

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            chunk_text = block.text
                            if self.session_id:
                                self.session_manager.add_event(self.session_id, {"type": "text", "content": chunk_text})
                            yield {"type": "text", "content": chunk_text}
                            
                            # Check active skills for UI highlighting
                            skills = self.loaded_skills
                            acc_lower = chunk_text.lower()
                            active = [s for s in skills if s.lower() in acc_lower or s.replace(" ", "-").lower() in acc_lower]
                            if active:
                                active_list = list(set(active))
                                if self.session_id:
                                    self.session_manager.add_event(self.session_id, {"type": "active_skills", "content": active_list})
                                yield {"type": "active_skills", "content": active_list}
                                
                        elif isinstance(block, ToolUseBlock):
                            display_name = block.name.replace("mcp__retail__", "")
                            tool_use_map[block.id] = display_name
                            event = {"type": "tool_start", "name": display_name, "args": block.input}
                            if self.session_id:
                                self.session_manager.add_event(self.session_id, event)
                            yield event
                            
                elif isinstance(message, UserMessage):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            name = tool_use_map.get(block.tool_use_id, "Tool")
                            event = {"type": "tool_result", "name": name, "result": block.content}
                            if self.session_id:
                                self.session_manager.add_event(self.session_id, event)
                            yield event
                            
        except Exception as e:
            logger.error(f"Agent Error: {str(e)}", exc_info=True)
            yield {"type": "error", "content": f"Agent Error: {str(e)}"}

    def reset_conversation(self):
        self.session_id = None
        logger.info("🔄 Native SDK session reset.")

    def cleanup(self):
        cleanup_tools()

