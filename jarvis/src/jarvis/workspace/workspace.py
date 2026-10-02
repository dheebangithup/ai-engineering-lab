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
    Return the default JARVIS workspace.
    """
    return Workspace(
        root=Path.home() / ".jarvis"
    )           