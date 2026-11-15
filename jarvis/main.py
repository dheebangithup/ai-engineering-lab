"""
J.A.R.V.I.S. Main Entry Point.
Initializes the complete agent system across all layers and runs an interactive loop or demonstration.
"""

import asyncio
import os
import sys
from jarvis import config
from jarvis.core.jarvis import Jarvis
from jarvis.core.schemas import JarvisRequest
from jarvis.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("jarvis.main")


async def run_jarvis_demo() -> None:
    """Run an end-to-end demonstration of the J.A.R.V.I.S. orchestrator."""
    jarvis = Jarvis()
    await jarvis.initialize()

    print("\n" + "=" * 60)
    print(" 🤖 J.A.R.V.I.S. — Personal AI Engineering Partner Online")
    print("=" * 60)
    print(f"Workspace: {jarvis.workspace.root_dir}")
    print(f"Active Providers: {jarvis.provider_gateway.list_active_providers()}")
    print(f"Registered Tools: {len(jarvis.tools_gateway.registry)} tools across categories: {jarvis.tools_gateway.registry.list_categories()}")
    print("=" * 60 + "\n")

    test_queries = [
        "Hi Jarvis, are all systems operational?",
        "Inspect the files in our workspace and list what you find",
    ]

    for q in test_queries:
        print(f"\n💬 User: {q}")
        response = await jarvis.process(JarvisRequest(query=q))
        print(f"🧠 Classification: complexity={response.classification.complexity.value}, intent={response.classification.intent.value}")
        print(f"🤖 Agent Used:    {response.agent_used} (model: {response.model_used or 'N/A'}, provider: {response.provider_used or 'N/A'})")
        if response.tools_used:
            print(f"🔧 Tools Invoked: {response.tools_used}")
        print(f"\n🎙️ J.A.R.V.I.S.:\n{response.answer}\n")
        print("-" * 60)

    await jarvis.shutdown()


def main() -> None:
    asyncio.run(run_jarvis_demo())


if __name__ == "__main__":
    main()
