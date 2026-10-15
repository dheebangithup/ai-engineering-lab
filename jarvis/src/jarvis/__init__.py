from typing import Optional

from jarvis.workspace import Workspace, default_workspace, initialize_workspace


def initialize_app(workspace: Optional[Workspace] = None) -> Workspace:
    """
    App-level startup initialization: sets up runtime directories once
    at application bootstrap time.
    """
    return initialize_workspace(workspace)


def main() -> None:
    initialize_app()
    print("Hello from jarvis!")


__all__ = [
    "initialize_app",
    "initialize_workspace",
    "main",
]
