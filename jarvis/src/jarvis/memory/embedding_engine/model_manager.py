from pathlib import Path

from huggingface_hub import hf_hub_download

from jarvis.workspace import Workspace

from .config import EmbeddingConfig
from .exceptions import ModelDownloadError


class ModelManager:

    def __init__(
        self,
        config: EmbeddingConfig,
        workspace: Workspace,
    ):
        self.config = config
        self.workspace = workspace

    @property
    def model_path(self) -> Path:
        return (
            self.workspace.embedding_models_dir
            / self.config.model_filename
        )

    def is_downloaded(self) -> bool:
        return self.model_path.exists()

    def ensure_model(self) -> Path:
        if self.is_downloaded():
            return self.model_path

        self.workspace.embedding_models_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            f"Downloading embedding model: "
            f"{self.config.model_repo}"
        )

        try:
            downloaded_path = hf_hub_download(
                repo_id=self.config.model_repo,
                filename=self.config.model_filename,
                local_dir=self.workspace.embedding_models_dir,
            )

            return Path(downloaded_path)

        except Exception as exc:
            raise ModelDownloadError(
                f"Failed to download embedding model: {exc}"
            ) from exc