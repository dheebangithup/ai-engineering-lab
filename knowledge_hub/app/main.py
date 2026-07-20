import logging
import os
import uvicorn
import tempfile
import shutil
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from knowledge_hub.app.config import app_logger
from knowledge_hub.app.config.database import Base, engine, get_db
from knowledge_hub.app.database.qdrant_store import QdrantStore
from knowledge_hub.app.embeddings import LocalLMStudioEmbeddingProvider
from knowledge_hub.app.enums import FileType
from knowledge_hub.app.repositories import DocumentMetaDataRepository, ChunkMetaDataRepository
from knowledge_hub.app.service import IngestionService, DocumentMetaDataService, RetrievalService
from knowledge_hub.app.service.retrieval_service import RetrievalResult
from knowledge_hub.app.model import SearchRequest, SearchResponse
from knowledge_hub.app.model.api_reponse import ApiResponse, ResponseBuilder

# Configure logging globally
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Initialize database tables via lifespan event
@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_logger = logging.getLogger("app")
    try:
        startup_logger.info("Application starting up. Initializing resources...")
        from knowledge_hub.app.entity.document_metadata import DocumentMetaDataEntity
        from knowledge_hub.app.entity.chunk_metadata import ChunkMetaDataEntity
        startup_logger.info("Checking/Creating database tables (if they do not already exist)...")
        Base.metadata.create_all(bind=engine)
        startup_logger.info("Database tables verified/created successfully.")
    except Exception as e:
        startup_logger.error("Failed to check/create database tables during startup", exc_info=True)
        raise e
    yield
    startup_logger.info("Application shutting down. Cleaning up resources...")

# Create FastAPI application
app = FastAPI(
    title="Enterprise Knowledge Hub API",
    description="REST API for the Enterprise Knowledge Hub. Handles high-performance document ingestion, vector storage, metadata management, and semantic retrieval.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Pydantic Schemas for API Documentation
class IngestRequest(BaseModel):
    file_path: str = Field(
        ...,
        description="Relative or absolute path to the document file. On Windows, use forward slashes (/) or double backslashes (\\\\) to avoid JSON escape sequence errors.",
        examples=["knowledge_hub/data/attention-is-all-you-need-paper.pdf"]
    )
    file_type: FileType = Field(
        FileType.PDF,
        description="The file format/type of the document (pdf, docx, md, image)."
    )
    chunk_size: int = Field(
        500,
        description="Size of text chunks to split the document into.",
        ge=1,
        le=8192
    )
    new_after_n_chars: int = Field(
        2400,
        description="Target size to start a new chunk.",
        ge=1
    )
    combine_text_under_n_chars: int = Field(
        500,
        description="Threshold to combine tiny chunks.",
        ge=0
    )
    strategy: str = Field(
        "hi_res",
        description="Unstructured partitioning strategy (hi_res, fast, auto, ocr_only)."
    )
    keep_table_as_html: bool = Field(
        False,
        description="Keep tables structured as HTML."
    )

class IngestionResponseData(BaseModel):
    document_id: str = Field(..., description="The unique UUID of the ingested document.")
    file_name: str = Field(..., description="The name of the file processed.")
    file_type: str = Field(..., description="The type of the file processed.")
    status: str = Field(..., description="Ingestion processing status (e.g., SUCCESS, FAILED).")
    total_pages: int | None = Field(None, description="Total number of pages parsed from the document.")

# Dependency Injection Providers
def get_document_metadata_service(db: Session = Depends(get_db)) -> DocumentMetaDataService:
    return DocumentMetaDataService(
        doc_repo=DocumentMetaDataRepository(db),
        chunk_repo=ChunkMetaDataRepository(db)
    )

def get_embedding_provider() -> LocalLMStudioEmbeddingProvider:
    return LocalLMStudioEmbeddingProvider()

def get_vector_store(embedding_provider: LocalLMStudioEmbeddingProvider = Depends(get_embedding_provider)) -> QdrantStore:
    return QdrantStore(embedding_provider=embedding_provider)

def get_retrieval_service(
    metadata_service: DocumentMetaDataService = Depends(get_document_metadata_service),
    vector_store: QdrantStore = Depends(get_vector_store)
) -> RetrievalService:
    return RetrievalService(document_metadata_service=metadata_service, vector_store=vector_store)

# Routes
@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint verifying server status and welcoming users.
    """
    return {"message": "Welcome to the Enterprise Knowledge Hub API"}

@app.post(
    "/api/v1/ingest",
    response_model=ApiResponse[IngestionResponseData],
    status_code=status.HTTP_200_OK,
    tags=["Ingestion"],
    summary="Ingest a document file",
    description="Parses, chunks, embeds, and indexes an uploaded document file into the vector store and relational metadata database."
)
async def ingest_document(
    file: UploadFile = File(..., description="The document file to upload"),
    file_type: FileType = Form(FileType.PDF, description="The file format/type of the document (pdf, docx, md, image)."),
    chunk_size: int = Form(500, description="Size of text chunks to split the document into.", ge=1, le=8192),
    new_after_n_chars: int = Form(2400, description="Target size to start a new chunk.", ge=1),
    combine_text_under_n_chars: int = Form(500, description="Threshold to combine tiny chunks.", ge=0),
    strategy: str = Form("hi_res", description="Unstructured partitioning strategy (hi_res, fast, auto, ocr_only)."),
    keep_table_as_html: bool = Form(False, description="Keep tables structured as HTML."),
    doc_version: str = Form("1.0.0", description="Document version reference."),
    doc_id: Optional[str] = Form(None, description="Optional document ID parameter."),
    db: Session = Depends(get_db),
    embedding_provider: LocalLMStudioEmbeddingProvider = Depends(get_embedding_provider),
    vector_store: QdrantStore = Depends(get_vector_store),
    metadata_service: DocumentMetaDataService = Depends(get_document_metadata_service)
):
    app_logger.info(f"Ingestion Request received for uploaded file: '{file.filename}' (content-type: {file.content_type}, type: {file_type.value}, version: {doc_version}, doc_id: {doc_id})")

    # 1. Validation
    if not file.filename:
        app_logger.error("Validation Error: Uploaded file has no filename.")
        return ResponseBuilder.failure(
            message="Uploaded file must have a valid filename.",
            error_code=status.HTTP_400_BAD_REQUEST
        )

    temp_dir = None
    try:
        # Create a unique temporary directory to store the uploaded file
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        app_logger.info(f"Created temporary directory '{temp_dir}' for processing '{file.filename}'")

        # Write uploaded file content to the temp path in chunks
        bytes_written = 0
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunk size
                buffer.write(chunk)
                bytes_written += len(chunk)

        app_logger.info(f"Successfully saved uploaded file to '{temp_file_path}' ({bytes_written} bytes written)")

        # Validate that the file is not empty
        if bytes_written == 0:
            app_logger.error(f"Validation Error: Uploaded file '{file.filename}' is empty (0 bytes).")
            return ResponseBuilder.failure(
                message=f"Uploaded file '{file.filename}' is empty.",
                error_code=status.HTTP_400_BAD_REQUEST
            )

        # 2. Process Ingestion
        from knowledge_hub.app.processor.unstructured_processor import UnStructuredProcessor
        from unstructured.partition.utils.constants import PartitionStrategy

        app_logger.info(f"Initializing UnStructuredProcessor: strategy={strategy}, keep_table_as_html={keep_table_as_html}, chunk_size={chunk_size}")

        strategy_map = {
            "hi_res": PartitionStrategy.HI_RES,
            "fast": PartitionStrategy.FAST,
            "ocr_only": PartitionStrategy.OCR_ONLY,
            "auto": PartitionStrategy.AUTO
        }
        strategy_enum = strategy_map.get(strategy.lower(), PartitionStrategy.HI_RES)

        processor = UnStructuredProcessor(
            strategyType=strategy_enum,
            keepTableAsHtml=keep_table_as_html,
            chunk_size=chunk_size,
            new_after_n_chars=new_after_n_chars,
            combine_text_under_n_chars=combine_text_under_n_chars
        )

        ingestion_service = IngestionService(
            processor=processor,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            meta_data_service=metadata_service
        )

        app_logger.info(f"Running Ingestion pipeline for: '{temp_file_path}' (doc_version: {doc_version}, doc_id: {doc_id})")
        doc_meta = ingestion_service.ingest(temp_file_path, file_type, doc_version, doc_id)

        app_logger.info(f"Ingestion pipeline completed successfully. Generated Document ID: {doc_meta.document_id}")

        response_data = IngestionResponseData(
            document_id=str(doc_meta.document_id),
            file_name=doc_meta.file_name,
            file_type=doc_meta.file_type,
            status=doc_meta.status,
            total_pages=doc_meta.total_pages
        )
        return ResponseBuilder.success(
            data=response_data,
            message="Document ingestion completed successfully"
        )
    except Exception as e:
        app_logger.error(f"Ingestion pipeline failed for uploaded file '{file.filename}'", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Ingestion pipeline failed: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # Clean up temporary directory and files
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                app_logger.info(f"Successfully cleaned up temporary directory '{temp_dir}'")
            except Exception as cleanup_err:
                app_logger.warning(f"Failed to clean up temporary directory '{temp_dir}': {cleanup_err}", exc_info=True)

@app.post(
    "/api/v1/search",
    response_model=ApiResponse[RetrievalResult],
    status_code=status.HTTP_200_OK,
    tags=["Retrieval"],
    summary="Search / Retrieve documents with ContextBuilder and Prompt Provisioning",
    description="Performs semantic vector search against Qdrant, builds context via ContextBuilder pipeline, and provisions versioned prompt templates."
)
async def search_documents(
    request: SearchRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
):
    app_logger.info(f"Search Request received: query='{request.query}', top_k={request.top_k}, prompt_name={request.prompt_name}")

    # 1. Validation
    if not request.query.strip():
        app_logger.error("Validation Error: Empty search query")
        return ResponseBuilder.failure(
            message="Search query cannot be empty",
            error_code=status.HTTP_400_BAD_REQUEST
        )

    # 2. Process Search
    try:
        response = retrieval_service.search(request)
        if response.success and response.data:
            num_chunks = response.data.built_context.chunk_count if response.data.built_context else 0
            app_logger.info(f"Search succeeded for query: '{request.query}'. Assembled {num_chunks} context chunks.")
        else:
            app_logger.error(f"Search failed for query: '{request.query}'. Message: {response.message}")
        return response
    except Exception as e:
        app_logger.error(f"Search failed for query: '{request.query}'", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Search failed: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

if __name__ == "__main__":
        uvicorn.run(
            "knowledge_hub.app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
        )
