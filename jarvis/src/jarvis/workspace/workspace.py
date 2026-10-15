import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    """
    Root filesystem location for all JARVIS runtime data.
    """

    root: Path

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    @property
    def embedding_models_dir(self) -> Path:
        return self.models_dir / "embeddings"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def vector_store_dir(self) -> Path:
        return self.data_dir / "vector_store"

    @property
    def qdrant_dir(self) -> Path:
        return self.vector_store_dir / "qdrant"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    def initialize(self) -> None:
        """
        Create the JARVIS workspace directory structure.
        """
        directories = (
            self.root,
            self.models_dir,
            self.embedding_models_dir,
            self.data_dir,
            self.vector_store_dir,
            self.qdrant_dir,
            self.cache_dir,
            self.logs_dir,
        )

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

def default_workspace() -> Workspace:
    """
    Return the default JARVIS workspace (single source of truth).
    Respects JARVIS_WORKSPACE environment variable if configured.
    """
    env_root = os.getenv("JARVIS_WORKSPACE")
    root_path = Path(env_root).resolve() if env_root else (Path.home() / ".jarvis")
    return Workspace(root=root_path)


def initialize_workspace(workspace: Workspace | None = None) -> Workspace:
    """
    Application-level initialization function to set up all runtime workspace
    directories at startup time rather than inside agent components.
    """
    ws = workspace or default_workspace()
    ws.initialize()
    return ws