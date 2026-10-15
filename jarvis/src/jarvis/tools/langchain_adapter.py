from typing import Any, List, Optional
from langchain_core.tools import BaseTool, StructuredTool

from jarvis.tools.tools_gateway import ToolsGateway


def create_gateway_tools(gateway: ToolsGateway) -> List[BaseTool]:
    """
    Create LangChain compatible BaseTool instances backed by the centralized ToolsGateway.
    Enforces path traversal protection and command allowlists via the gateway.
    Handles unexpected keyword arguments gracefully.
    """

    def list_files(directory: str = ".", recursive: bool = False, **kwargs: Any) -> Any:
        """List files and directories in the allowed workspace directory."""
        res = gateway.execute("list_files", {"directory": directory, "recursive": recursive})
        return res.data if res.success else f"Error: {res.error}"

    def read_file(file_path: str, **kwargs: Any) -> Any:
        """Read the complete text content of a file from the allowed workspace directory."""
        res = gateway.execute("read_file", {"file_path": file_path})
        return res.data if res.success else f"Error: {res.error}"

    def write_file(file_path: str, content: str, **kwargs: Any) -> Any:
        """Write content to a file in the allowed workspace directory."""
        res = gateway.execute("write_file", {"file_path": file_path, "content": content})
        return res.data if res.success else f"Error: {res.error}"

    def search_files(pattern: str, directory: str = ".", **kwargs: Any) -> Any:
        """Search files in the allowed workspace directory for a text pattern."""
        res = gateway.execute("search_files", {"pattern": pattern, "directory": directory})
        return res.data if res.success else f"Error: {res.error}"

    def run_command(command: str, args: Optional[List[str]] = None, **kwargs: Any) -> Any:
        """Execute a permitted system command safely without shell expansion."""
        # Support LLMs passing full command string or alternative argument keys
        parts = command.strip().split()
        cmd_name = parts[0] if parts else command
        parsed_args = parts[1:] if len(parts) > 1 else []

        raw_args = args if args is not None else kwargs.get("v__args") or kwargs.get("arguments") or []
        if isinstance(raw_args, str):
            raw_args = [raw_args]
        final_args = list(raw_args) + parsed_args

        res = gateway.execute("run_command", {"command": cmd_name, "args": final_args})
        return res.data if res.success else f"Error: {res.error}"

    return [
        StructuredTool.from_function(list_files, name="list_files", description="List files in allowed directory.", handle_tool_error=True),
        StructuredTool.from_function(read_file, name="read_file", description="Read file from allowed directory.", handle_tool_error=True),
        StructuredTool.from_function(write_file, name="write_file", description="Write content to a file in allowed directory.", handle_tool_error=True),
        StructuredTool.from_function(search_files, name="search_files", description="Search files for a text pattern.", handle_tool_error=True),
        StructuredTool.from_function(run_command, name="run_command", description="Execute a permitted system command safely.", handle_tool_error=True),
    ]
