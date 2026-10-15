import json
import sys
from pathlib import Path

# Add src to sys.path so demo can run directly from repository root
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from jarvis.tools import ToolDiscovery, ToolRegistry, ToolsGateway, register_default_tools


def run_demo() -> None:
    print("=" * 70)
    print("  J.A.R.V.I.S. Tools Gateway — Minimal MVP Demonstration")
    print("=" * 70)

    # 1. Initialize Registry and register tools constrained to the repository root
    registry = ToolRegistry()
    register_default_tools(registry=registry, allowed_base_dir=repo_root)

    discovery = ToolDiscovery(registry=registry)
    gateway = ToolsGateway(registry=registry)

    print(f"\n[INIT] Registered {len(registry.list_definitions())} tools:")
    for tool_def in registry.list_definitions():
        print(f"  • {tool_def.id:15} ({tool_def.name}) -> {tool_def.description}")

    # --- Workflow Scenario: Find Python files in the project ---
    user_query = "Find all Python files in the project"
    print("\n" + "-" * 70)
    print(f"STEP 1: User Request -> \"{user_query}\"")
    print("-" * 70)

    # STEP 2: ToolDiscovery identifies relevant tools
    print("\nSTEP 2: ToolDiscovery running BM25 query against registry...")
    matching_tools = discovery.discover(user_query, max_results=3)

    if not matching_tools:
        print("  No matching tools found!")
        return

    print(f"  Discovered {len(matching_tools)} relevant tool(s):")
    for t in matching_tools:
        print(f"    - ID: {t.id} | Name: {t.name}")

    # STEP 3: Agent receives selected tool's definition and input schema
    selected_tool = matching_tools[0]
    print(f"\nSTEP 3: Agent selects top matching tool: '{selected_tool.id}'")
    print("  Input Schema:")
    print(json.dumps(selected_tool.parameters, indent=4))

    # STEP 4: Agent constructs arguments based on schema
    arguments = {
        "directory": "src",
        "recursive": True,
    }
    print(f"\nSTEP 4: Agent supplies arguments:")
    print(json.dumps(arguments, indent=4))

    # STEP 5 & 6: Gateway validates and executes
    print(f"\nSTEP 5: ToolsGateway validating and executing '{selected_tool.id}'...")
    result = gateway.execute(selected_tool.id, arguments)

    print("\nSTEP 6: Structured ToolResult received:")
    print(f"  Tool ID: {result.tool_id}")
    print(f"  Success: {result.success}")

    if result.success and isinstance(result.data, list):
        py_files = [f for f in result.data if f["path"].endswith(".py")]
        print(f"  Found {len(py_files)} Python files in 'src':")
        for f in py_files:
            print(f"    - {f['path']} ({f['size']} bytes)")

    # --- Safeguards Demonstration ---
    print("\n" + "=" * 70)
    print("  Safeguards & Error Handling Demonstration")
    print("=" * 70)

    # 1. Path Traversal Prevention
    print("\n1. Testing Path Traversal Prevention ('../../etc/passwd'):")
    traversal_result = gateway.execute("read_file", {"file_path": "../../etc/passwd"})
    print(f"  Success: {traversal_result.success}")
    print(f"  Error:   {traversal_result.error}")

    # 2. Command Allowlist Enforcement
    print("\n2. Testing Command Allowlist Prevention ('rm -rf'):")
    cmd_result = gateway.execute("run_command", {"command": "rm", "args": ["-rf", "/tmp/test"]})
    print(f"  Success: {cmd_result.success}")
    print(f"  Error:   {cmd_result.error}")

    # 3. Argument Schema Validation
    print("\n3. Testing Argument Validation (missing required 'file_path'):")
    val_result = gateway.execute("read_file", {})
    print(f"  Success: {val_result.success}")
    print(f"  Error:   {val_result.error}")

    # 4. Unknown Tool ID
    print("\n4. Testing Unknown Tool ID ('non_existent_tool'):")
    unk_result = gateway.execute("non_existent_tool", {})
    print(f"  Success: {unk_result.success}")
    print(f"  Error:   {unk_result.error}")

    # 5. Permitted Command Execution
    print("\n5. Testing Permitted Command ('echo hello world'):")
    echo_result = gateway.execute("run_command", {"command": "echo", "args": ["hello", "world"]})
    print(f"  Success: {echo_result.success}")
    print(f"  Output:  {echo_result.data}")

    print("\n" + "=" * 70)
    print("  Demonstration completed successfully.")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
