from h2.settings import SettingCodes
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # goes up from app/config to project root
class AppSettings(BaseSettings):

    QDRANT_API_KEY: str = ''
    QDRANT_URL: str = ''
    COLLECTION_NAME: str = ''

    LOCAL_LM_EMBEDDING_MODEL: str = ''
    LOCAL_LM_URL: str = 'http://localhost:1234/v1'
    LOCAL_LM_API_KEY: str = 'lm-studio'
    LOCAL_LM_CHAT_MODEL: str = 'qwen2.5-7b-instruct-1m:3'
    LOCAL_LM_TEMPERATURE: float = 0.7

    GROQ_API_KEY:str=''
    GROQ_VISION_MODEL:str='llama-3.1-8b-instant'

    POSTGRES_URL: str = ''
    
    # LLM Settings for the RAG Retrieval Pipeline
    LLM_PROVIDER: str = 'lm_studio'  # "groq" | "openai" | "lm_studio"
    LLM_MODEL: str = 'qwen2.5-7b-instruct-1m:3'

    # Context & Retrieval Settings
    MAX_CONTEXT_TOKENS: int = 6000
    DEFAULT_SCORE_THRESHOLD: float = 0.6
    DEFAULT_TOP_K: int = 5

    # Evaluation Settings
    RAGAS_EVAL_PROVIDER: str = "groq"  # "groq" | "openai" | "lm_studio"
    RAGAS_EVAL_MODEL: str = "llama-3.1-8b-instant"


    # Configurable Indexed Payload Fields for Qdrant Metadata Filtering
    INDEXED_PAYLOAD_FIELDS: dict[str, str] = {
        "document_id": "keyword",
        "page_number": "integer",
        "chunk_id": "keyword",
        "file_type": "keyword",
        "doc_version": "keyword",
        "file_name": "keyword",
    }

    # BM25 Hybrid Retrieval Settings
    DEFAULT_RETRIEVAL_MODE: str = 'dense'      # "dense" | "bm25" | "hybrid"
    DEFAULT_BM25_WEIGHT: float = 0.3           # BM25 weight in hybrid RRF fusion
    DEFAULT_DENSE_WEIGHT: float = 0.7          # Dense vector weight in hybrid RRF fusion
    BM25_TOP_K_MULTIPLIER: float = 1.5         # Fetch top_k * multiplier candidates for better fusion
    ENABLE_BM25_INDEX_ON_STARTUP: bool = True  # Build BM25 index from Qdrant on app startup

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")

