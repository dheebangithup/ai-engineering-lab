import logging

import uvicorn
from fastapi import FastAPI

from knowledge_hub.app.config.database import SessionLocal
from knowledge_hub.app.database.qdrant_store import QdrantStore
from knowledge_hub.app.embeddings import LocalLMStudioEmbeddingProvider
from knowledge_hub.app.enums import FileType
from knowledge_hub.app.repositories import DocumentMetaDataRepository, ChunkMetaDataRepository
from knowledge_hub.app.service import IngestionService, DocumentMetaDataService

app = FastAPI()

# Initialize database tables
startup_logger = logging.getLogger("app")
try:
    from knowledge_hub.app.config.database import Base, engine
    from knowledge_hub.app.entity.document_metadata import DocumentMetaDataEntity
    from knowledge_hub.app.entity.chunk_metadata import ChunkMetaDataEntity
    startup_logger.info("Checking/Creating database tables...")
    Base.metadata.create_all(bind=engine)
    startup_logger.info("Database tables verified/created successfully.")
except Exception as e:
    startup_logger.error("Failed to check/create database tables", exc_info=True)
    raise e

@app.get("/")
async def root():
    return {"!!!! Welcome to Enterprise Knowledge Hub !!!"}


@app.get('/check')
async def check_api():

    from knowledge_hub.app.parser.UnstructuredParser import UnstructuredParser

    FILE = '../data/attention-is-all-you-need-paper.pdf'
    parser = UnstructuredParser()
    from knowledge_hub.app.chunkers.recursive_chunker import RecursiveChunker as Chunker

    chunker = Chunker( chunk_size=512, chunk_overlap=20)
    embeder=LocalLMStudioEmbeddingProvider()
    print("embedding done")

    IngestionService(
        parser=parser,
        chunker=chunker,
        embedding_provider=embeder,
        vector_store=QdrantStore(embedding_provider=embeder),
        meta_data_service=DocumentMetaDataService(
            doc_repo=DocumentMetaDataRepository(SessionLocal()),
            chunk_repo=ChunkMetaDataRepository(SessionLocal()),
        )
    ).ingest(FILE,FileType.PDF)

    return 'done'



# Configure logging globally
logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more verbosity
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Create a singleton logger for the app
logger = logging.getLogger("app")


if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8000)

