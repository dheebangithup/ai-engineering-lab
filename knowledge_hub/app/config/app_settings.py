from h2.settings import SettingCodes
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # goes up from app/config to project root
class AppSettings(BaseSettings):

    QDRANT_API_KEY: str = ''
    QDRANT_URL: str = ''
    COLLECTION_NAME: str = ''

    LOCAL_LM_EMBEDDING_MODEL: str = ''
    LOCAL_LM_URL: str = ''
    LOCAL_LM_API_KEY: str = ''

    POSTGRES_URL: str = ''

    # Context & Retrieval Settings
    MAX_CONTEXT_TOKENS: int = 6000
    DEFAULT_SCORE_THRESHOLD: float = 0.7
    DEFAULT_TOP_K: int = 5

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")
