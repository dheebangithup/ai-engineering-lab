from typing import Optional

from jarvis.workspace import (
    Workspace,
    default_workspace,
    get_workspace,
    initialize_workspace,
    set_active_workspace,
)


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
    "Workspace",
    "get_workspace",
    "set_active_workspace",
    "initialize_app",
    "initialize_workspace",
    "default_workspace",
    "main",
]
