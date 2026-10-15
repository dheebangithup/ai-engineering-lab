import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class WorkspaceDirectory(str, Enum):
    """Standard subdirectory names for the JARVIS workspace."""
    MODELS = "models"
    EMBEDDINGS = "embeddings"
    DATA = "data"
    VECTOR_STORE = "vector_store"
    QDRANT = "qdrant"
    CACHE = "cache"
    LOGS = "logs"
    RESULTS = "results"
    WORKSPACE = "workspace"
    DOT_JARVIS = ".jarvis"


ENV_JARVIS_WORKSPACE: str = "JARVIS_WORKSPACE"


@dataclass(frozen=True)
class Workspace:
    """
    Root filesystem location for all JARVIS runtime data.
    """

    root: Path

    @property
    def models_dir(self) -> Path:
        return self.root / WorkspaceDirectory.MODELS.value

    @property
    def embedding_models_dir(self) -> Path:
        return self.models_dir / WorkspaceDirectory.EMBEDDINGS.value

    @property
    def data_dir(self) -> Path:
        return self.root / WorkspaceDirectory.DATA.value

    @property
    def vector_store_dir(self) -> Path:
        return self.data_dir / WorkspaceDirectory.VECTOR_STORE.value

    @property
    def qdrant_dir(self) -> Path:
        return self.vector_store_dir / WorkspaceDirectory.QDRANT.value

    @property
    def cache_dir(self) -> Path:
        return self.root / WorkspaceDirectory.CACHE.value

    @property
    def logs_dir(self) -> Path:
        return self.root / WorkspaceDirectory.LOGS.value

    @property
    def results_dir(self) -> Path:
        return self.root / WorkspaceDirectory.RESULTS.value

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
            self.results_dir,
        )

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


def default_workspace() -> Workspace:
    """
    Return the default JARVIS workspace (single source of truth).
    Respects JARVIS_WORKSPACE environment variable if configured.
    Falls back to a local 'workspace' directory in the project root if present,
    otherwise defaults to Path.home() / ".jarvis".
    """
    env_root = os.getenv(ENV_JARVIS_WORKSPACE)
    if env_root:
        root_path = Path(env_root).resolve()
    else:
        project_ws = Path(__file__).resolve().parent.parent.parent.parent / WorkspaceDirectory.WORKSPACE.value
        if project_ws.exists():
            root_path = project_ws
        else:
            root_path = Path.home() / WorkspaceDirectory.DOT_JARVIS.value
    return Workspace(root=root_path)


def initialize_workspace(workspace: Workspace | None = None) -> Workspace:
    """
    Application-level initialization function to set up all runtime workspace
    directories at startup time rather than inside agent components.
    """
    ws = workspace or default_workspace()
    ws.initialize()
    return ws