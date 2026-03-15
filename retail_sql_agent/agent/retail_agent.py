"""
Skills-based SQL Agent using the Anthropic Python SDK.

Loads SKILL.md files from .claude/skills/ and executes multi-turn 
agentic loops with granular event streaming for the UI.
"""

import asyncio
import os
import json
import traceback
from typing import AsyncIterator, Any

from dotenv import load_dotenv
load_dotenv()

import anthropic
from anthropic import AsyncAnthropic
from tools.database_tools import ALL_TOOLS as SQL_TOOLS, initialize_tools, cleanup_tools, _db as sql_db
from tools.export_tools import export_to_csv, export_to_json
from config import Config, logger

# Helper to get Anthropic-compatible tool definitions
def get_tool_definitions():
    return [
        {
            "name": "get_database_schema",
            "description": "Get database schema — all tables and columns. Call this first before any SQL query.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "execute_sql_query",
            "description": "Execute a safe SQL SELECT query on the sales database. Returns rows, columns, and data preview.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Valid SQL SELECT statement"},
                    "explanation": {"type": "string", "description": "What this query does"},
                },
                "required": ["query", "explanation"],
            },
        },
        {
            "name": "export_to_csv",
            "description": "Export SQL query results to a CSV file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query whose results to export"},
                    "filename": {"type": "string", "description": "Output filename (e.g. top_products.csv)"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "export_to_json",
            "description": "Export SQL query results to a JSON file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query whose results to export"},
                    "filename": {"type": "string", "description": "Output filename (e.g. sales_data.json)"},
                },
                "required": ["query"],
            },
        }
    ]

# Mapping tool names to implementation functions
TOOL_MAP = {
    "get_database_schema": lambda **kwargs: sql_db.get_schema(),
    "execute_sql_query": lambda **kwargs: sql_db.execute_query(kwargs["query"]),
    "export_to_csv": export_to_csv,
    "export_to_json": export_to_json,
}


class RetailAgent:
    """
    SQL Analyst Agent that implements the Skills architecture independently.
    Uses AsyncAnthropic for multi-turn streaming.
    """

    def __init__(self):
        self.model = Config.MODEL
        self.client = AsyncAnthropic()
        self.messages = []
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.session_file = os.path.join(self.project_root, "session.json")
        
        initialize_tools()
        self.skills_prompt = self._load_skills()
        self._load_session()

    def _load_session(self):
        """Restore conversation from disk if available."""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    self.messages = data.get("messages", [])
                    logger.info(f"📂 Session restored ({len(self.messages)} messages).")
            except Exception as e:
                logger.error(f"Error loading session: {e}", exc_info=True)

    def _save_session(self):
        """Save conversation to disk."""
        try:
            with open(self.session_file, "w") as f:
                json.dump({"messages": self.messages}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session: {e}", exc_info=True)

    def _load_skills(self) -> str:
        """Scan .claude/skills/ and build a combined system prompt."""
        skills_path = os.path.join(self.project_root, ".claude", "skills")
        if not os.path.exists(skills_path):
            return ""

        skills_content = ["\n## AVAILABLE SKILLS\n"]
        self.loaded_skills = []
        for skill_dir in os.listdir(skills_path):
            skill_md = os.path.join(skills_path, skill_dir, "SKILL.md")
            if os.path.isfile(skill_md):
                try:
                    with open(skill_md, "r", encoding="utf-8") as f:
                        raw_content = f.read()
                        content = raw_content
                        if content.startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 3:
                                content = f"**Skill Description**: {parts[1].strip()}\n{parts[2].strip()}"
                        
                        name = skill_dir.replace("-", " ").title()
                        self.loaded_skills.append(name)
                        skills_content.append(f"### Skill: {name}\n{content}\n")
                        logger.info(f"Loaded skill: {name}")
                except Exception as e:
                    logger.error(f"Error loading skill {skill_dir}: {e}", exc_info=True)
        
        return "\n".join(skills_content)

    async def stream_ask(self, question: str) -> AsyncIterator[dict[str, Any]]:
        """
        Stream structured flow events using a multi-turn loop.
        """
        self.messages.append({"role": "user", "content": question})
        system_prompt = f"{Config.SYSTEM_PROMPT}\n{self.skills_prompt}"

        max_turns = 10
        turn = 0
        
        try:
            while turn < max_turns:
                turn += 1
                
                # Stream the current round
                stream = await self.client.beta.messages.create(
                    model=self.model,
                    max_tokens=Config.MAX_TOKENS,
                    system=system_prompt,
                    tools=get_tool_definitions(),
                    messages=self.messages,
                    stream=True
                )
                
                accumulated_text = ""
                tool_use_blocks = {} # id -> {id, name, input}
                current_block_id = None

                async for chunk in stream:
                    if chunk.type == "content_block_start":
                        if chunk.content_block.type == "tool_use":
                            current_block_id = chunk.content_block.id
                            tool_use_blocks[current_block_id] = {
                                "id": chunk.content_block.id,
                                "name": chunk.content_block.name,
                                "input": ""
                            }
                    
                    elif chunk.type == "content_block_delta":
                        if chunk.delta.type == "text_delta":
                            accumulated_text += chunk.delta.text
                            yield {"type": "text", "content": chunk.delta.text}
                            
                            # Check if the exact skill name is mentioned in the text stream
                            active_skills = []
                            acc_lower = accumulated_text.lower()
                            for s in getattr(self, "loaded_skills", []):
                                if s.lower() in acc_lower or s.replace(" ", "-").lower() in acc_lower:
                                    active_skills.append(s)
                                   
                            # Deduplicate and update UI
                            active_skills = list(set(active_skills))
                            if active_skills:
                                yield {"type": "active_skills", "content": active_skills}
                                
                        elif chunk.delta.type == "input_json_delta":
                            tool_use_blocks[current_block_id]["input"] += chunk.delta.partial_json
                    
                    elif chunk.type == "content_block_stop":
                        # If a tool block finished, yield it for the UI now that we have args
                        if current_block_id in tool_use_blocks:
                            bu = tool_use_blocks[current_block_id]
                            try:
                                args = json.loads(bu["input"]) if bu["input"] else {}
                            except:
                                args = {"raw": bu["input"]}
                            
                            yield {
                                "type": "tool_start", 
                                "name": bu["name"], 
                                "args": args
                            }
                            current_block_id = None
                
                # Turn finished - build assistant message for history
                assistant_content_blocks = []
                if accumulated_text:
                    assistant_content_blocks.append({"type": "text", "text": accumulated_text})
                
                for bu in tool_use_blocks.values():
                    try:
                        parsed_input = json.loads(bu["input"]) if bu["input"] else {}
                    except:
                        parsed_input = {"error": "JSON parse error", "raw": bu["input"]}
                    
                    assistant_content_blocks.append({
                        "type": "tool_use",
                        "id": bu["id"],
                        "name": bu["name"],
                        "input": parsed_input
                    })
                
                self.messages.append({"role": "assistant", "content": assistant_content_blocks})
                self._save_session()
                
                # Check for tool use to decide if we need more turns
                if not tool_use_blocks:
                    break
                
                # Execute all tool calls in this turn
                for tool_call in tool_use_blocks.values():
                    name = tool_call["name"]
                    try:
                        input_data = json.loads(tool_call["input"]) if tool_call["input"] else {}
                    except:
                        input_data = {}
                    
                    result = self._execute_tool(name, input_data)
                    yield {"type": "tool_result", "name": name, "result": result}
                    
                    self.messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call["id"],
                                "content": str(result),
                            }
                        ],
                    })
                    self._save_session()

        except Exception as e:
            logger.error(f"Agent Error: {str(e)}", exc_info=True)
            yield {"type": "error", "content": f"Agent Error: {str(e)}"}

    def _execute_tool(self, name: str, input_data: dict) -> Any:
        if name in TOOL_MAP:
            try:
                # Return tool results as strings (required by Anthropic API)
                res = TOOL_MAP[name](**input_data)
                if hasattr(res, 'to_json'): # Handle DataFrames
                    return res.to_json(orient="records", date_format="iso")
                logger.debug(f"Executed tool {name} successfully.")
                return str(res)
            except Exception as e:
                logger.error(f"Error executing tool {name}: {str(e)}", exc_info=True)
                return f"Error executing tool {name}: {str(e)}"
        logger.warning(f"Tool {name} not found in TOOL_MAP.")
        return f"Error: Tool {name} not found"

    def reset_conversation(self):
        self.messages = []
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
        logger.info("🔄 Conversation reset and session file cleared.")

    def cleanup(self):
        cleanup_tools()
