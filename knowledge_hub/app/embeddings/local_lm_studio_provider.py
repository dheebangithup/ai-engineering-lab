import uuid
from typing import override

from langchain_openai import OpenAIEmbeddings

from knowledge_hub.app.config import app_settings
from knowledge_hub.app.constants import ErrorMessage, ErrorCode
from knowledge_hub.app.embeddings.embedding_provider import EmbeddingProvider
from knowledge_hub.app.exception import InvalidInputException
from knowledge_hub.app.model import Document
from knowledge_hub.app.model import EmbeddedDocument
from knowledge_hub.app.config import app_logger


class LocalLMStudioEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        self.__DEFAULT_DIMENSION=384
        self.__embeddings_client = OpenAIEmbeddings(
            base_url=app_settings.LOCAL_LM_URL,  # Local LM Studio address
            api_key=app_settings.LOCAL_LM_API_KEY,  # LangChain requires a string placeholder
            model=app_settings.LOCAL_LM_EMBEDDING_MODEL,  # Use your exact loaded model name
            check_embedding_ctx_length=False  # Prevents errors with local text tokenization
        )

    @property
    @override
    def dimension(self) -> int:
        try:
            dimension = len(self.__embeddings_client.embed_query("sample text for check dimention"))
            app_logger.info(f"Successfully determined embedding dimension: {dimension}")
            return dimension
        except Exception as e:
            app_logger.warning("Error getting embedding dimension, using fallback", exc_info=True)
            app_logger.info(f"Returning fallback default dimension: {self.__DEFAULT_DIMENSION}")
            return self.__DEFAULT_DIMENSION

    @override
    def embed(self,chunks:list[Document])->list[EmbeddedDocument]:
        app_logger.info(f"Embedding {len(chunks)} documents")
        if chunks is None or len(chunks) == 0:
            app_logger.warning("Chunks list is empty. No documents to embed.")
            raise InvalidInputException(ErrorMessage.INPUT_SHOULD_NOT_BE_EMPTY,ErrorCode.INVALID_INPUT)
        #TODO implement Checkpointing approch, networl failed, track success chunk, retry only failed chunk,another api call - finally check total count
        embedded_docs=[]
        for i,chunk in enumerate(chunks,1):
            try:
                app_logger.info(f"Embedding chunk {i}/{len(chunks)}")
                embedings= self.__embeddings_client.embed_query(chunk.content)
                embedded_docs.append(EmbeddedDocument(
                   embedding=embedings,
                   document=chunk
                 ))
            except Exception as e:
                app_logger.warning(f"Error embedding chunk {i} document: {chunk}", exc_info=True)
                continue

        app_logger.info(f"Embeddings completed. Successfully embedded {len(embedded_docs)} documents out of {len(chunks)} chunks")

        return embedded_docs




