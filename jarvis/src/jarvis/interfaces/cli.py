"""
Interactive CLI Interface for J.A.R.V.I.S.
Allows direct terminal conversational interaction with real-time reasoning and tool trace display.
"""

import asyncio
import sys
from jarvis.core.jarvis import Jarvis
from jarvis.core.schemas import JarvisRequest
from jarvis.logger import setup_logging
from jarvis.tools.schemas import PermissionRequest


async def terminal_approval_handler(req: PermissionRequest) -> bool:
    """Prompt the user in the CLI before running DANGEROUS actions."""
    print("\n" + "!" * 60)
    print(f"⚠️  SECURITY AUTHORIZATION REQUIRED:")
    print(f"   Tool:   {req.tool_name} ({req.tool_id})")
    print(f"   Tier:   {req.permission_tier.value.upper()}")
    print(f"   Args:   {req.arguments}")
    print("!" * 60)

    try:
        reply = input("Authorize this action? [y/N]: ").strip().lower()
        return reply in ("y", "yes")
    except EOFError:
        return False


async def run_cli() -> None:
    """Interactive command-line loop."""
    setup_logging()
    jarvis = Jarvis()
    jarvis.permissions.approval_callback = terminal_approval_handler

    print("Initializing J.A.R.V.I.S. subsystems...")
    await jarvis.initialize()

    print("\n" + "=" * 60)
    print(" 🤖 J.A.R.V.I.S. Personal AI Assistant (Type 'exit' to quit)")
    print("=" * 60 + "\n")

    try:
        while True:
            try:
                user_input = input("\n🧑 User: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nShutting down J.A.R.V.I.S. Farewell, sir.")
                break

            response = await jarvis.process(JarvisRequest(query=user_input))

            if response.tools_used:
                print(f"🔧 [Tools Used]: {', '.join(response.tools_used)}")
            if response.steps:
                print(f"🧠 [Reasoning Steps]: {len(response.steps)} step(s)")

            print(f"\n🎙️ J.A.R.V.I.S.:\n{response.answer}")

    finally:
        await jarvis.shutdown()


def main() -> None:
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
