import logging
import os
import uvicorn
import tempfile
import shutil
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from knowledge_hub.app.config import app_logger
from knowledge_hub.app.config.database import Base, engine, get_db
from knowledge_hub.app.database.qdrant_store import QdrantStore
from knowledge_hub.app.embeddings import LocalLMStudioEmbeddingProvider
from knowledge_hub.app.enums import FileType
from knowledge_hub.app.repositories import DocumentMetaDataRepository, ChunkMetaDataRepository
from knowledge_hub.app.service import IngestionService, DocumentMetaDataService, RetrievalService, LlmService
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
        from knowledge_hub.app.entity.evaluation import EvaluationRunEntity, EvaluationResultEntity
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

# Mount Static Assets Directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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

class DocumentResponseData(BaseModel):
    document_id: str = Field(..., description="Unique document ID")
    file_name: str = Field(..., description="File name")
    file_type: str = Field(..., description="File type")
    file_hash: str = Field(..., description="File content hash")
    status: str = Field(..., description="Processing status")
    total_pages: Optional[int] = Field(None, description="Total page count")
    doc_version: str = Field(..., description="Document version string")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    chunk_count: int = Field(0, description="Total associated chunks")

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

def get_llm_service() -> LlmService:
    return LlmService()

def get_retrieval_service(
    metadata_service: DocumentMetaDataService = Depends(get_document_metadata_service),
    vector_store: QdrantStore = Depends(get_vector_store),
    llm_service: LlmService = Depends(get_llm_service),
) -> RetrievalService:
    return RetrievalService(
        document_metadata_service=metadata_service,
        vector_store=vector_store,
        llm_service=llm_service,
    )

# Routes
@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint serving the Enterprise RAG Web Portal UI or welcome JSON.
    """
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        app_logger.info("Serving Web Portal static UI (index.html)")
        return FileResponse(index_file)
    app_logger.info("Serving default API status response")
    return {"message": "Welcome to the Enterprise Knowledge Hub API"}

@app.get(
    "/api/v1/documents",
    response_model=ApiResponse[List[DocumentResponseData]],
    status_code=status.HTTP_200_OK,
    tags=["Metadata"],
    summary="List all uploaded documents",
    description="Retrieves metadata for all ingested documents stored in the database."
)
async def list_documents(
    metadata_service: DocumentMetaDataService = Depends(get_document_metadata_service)
):
    app_logger.info("API Endpoint: GET /api/v1/documents requested")
    try:
        docs = metadata_service.get_all_docs()
        result = []
        for doc in docs:
            chunk_cnt = len(doc.chunks) if doc.chunks else 0
            created_str = doc.created_at.isoformat() if doc.created_at else None
            result.append(DocumentResponseData(
                document_id=str(doc.document_id),
                file_name=doc.file_name,
                file_type=doc.file_type,
                file_hash=doc.file_hash,
                status=doc.status,
                total_pages=doc.total_pages,
                doc_version=doc.doc_version,
                created_at=created_str,
                chunk_count=chunk_cnt
            ))
        app_logger.info(f"API Endpoint: GET /api/v1/documents returned {len(result)} records successfully.")
        return ResponseBuilder.success(data=result, message=f"Successfully fetched {len(result)} documents")
    except Exception as e:
        app_logger.error("API Endpoint: GET /api/v1/documents failed", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Failed to fetch documents: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.delete(
    "/api/v1/documents/{document_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    tags=["Metadata"],
    summary="Delete a document and its chunks",
    description="Removes document metadata and associated chunks from relational database."
)
async def delete_document(
    document_id: str,
    metadata_service: DocumentMetaDataService = Depends(get_document_metadata_service)
):
    app_logger.info(f"API Endpoint: DELETE /api/v1/documents/{document_id} requested")
    try:
        doc = metadata_service.get_doc(document_id)
        if not doc:
            app_logger.warning(f"API Endpoint: Document ID '{document_id}' not found for deletion.")
            return ResponseBuilder.failure(
                message=f"Document with ID '{document_id}' not found",
                error_code=status.HTTP_404_NOT_FOUND
            )
        metadata_service.delete_doc_and_chunks(document_id)
        app_logger.info(f"API Endpoint: Successfully deleted document ID '{document_id}'.")
        return ResponseBuilder.success(
            data={"document_id": document_id},
            message=f"Document '{doc.file_name}' deleted successfully"
        )
    except Exception as e:
        app_logger.error(f"API Endpoint: DELETE /api/v1/documents/{document_id} failed", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Failed to delete document: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
    enable_vision_model: Optional[bool] = Form(False, description="enable vision model for to get summary for images,tbales"),
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
            combine_text_under_n_chars=combine_text_under_n_chars,
            enable_vision_model=enable_vision_model

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

# --- Evaluation Request Schemas ---
class EvalQueryItem(BaseModel):
    question: str = Field(..., description="The query sent to the RAG system")
    contexts: List[str] = Field(..., description="The retrieved context chunks")
    answer: str = Field(..., description="The system generated response")
    ground_truth: str = Field(..., description="The actual expected answer")

class EvaluationPayload(BaseModel):
    run_name: Optional[str] = Field(None, description="Descriptive label for this evaluation run")
    test_set: List[EvalQueryItem] = Field(..., description="List of queries, contexts, and answers to evaluate")

class DynamicEvalQueryItem(BaseModel):
    question: str = Field(..., description="The query to run through the RAG system")
    ground_truth: str = Field(..., description="The actual expected answer")

class DynamicEvaluationPayload(BaseModel):
    run_name: Optional[str] = Field(None, description="Descriptive label for this evaluation run")
    test_questions: List[DynamicEvalQueryItem] = Field(..., description="List of queries and ground truths to run through RAG and evaluate")


# --- Evaluation Endpoints ---
@app.post(
    "/api/v1/evaluate/static",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    tags=["Evaluation"],
    summary="Evaluate static logs or datasets",
    description="Computes Ragas metrics on pre-retrieved contexts and pre-generated answers, saving results to history."
)
async def evaluate_rag_static(
    payload: EvaluationPayload,
    db: Session = Depends(get_db)
):
    from knowledge_hub.app.service.evaluation_service import EvaluationService
    app_logger.info(f"API Endpoint: POST /api/v1/evaluate/static called with {len(payload.test_set)} items.")
    try:
        service = EvaluationService(db)
        test_set_dicts = [item.dict() for item in payload.test_set]
        results = service.run_evaluation(test_set_dicts, run_name=payload.run_name)
        app_logger.info(f"Static evaluation completed successfully. Run ID: {results.get('run_id')}")
        return ResponseBuilder.success(data=results, message="Static evaluation completed successfully.")
    except Exception as e:
        app_logger.error("Ragas static evaluation failed", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Evaluation failed: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.post(
    "/api/v1/evaluate/pipeline",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    tags=["Evaluation"],
    summary="Evaluate active RAG pipeline on-the-fly",
    description="Retrieves contexts, generates responses, and evaluates the performance on a set of questions."
)
async def evaluate_rag_pipeline(
    payload: DynamicEvaluationPayload,
    db: Session = Depends(get_db),
    retrieval_service = Depends(get_retrieval_service)
):
    from knowledge_hub.app.service.evaluation_service import EvaluationService
    app_logger.info(f"API Endpoint: POST /api/v1/evaluate/pipeline called with {len(payload.test_questions)} questions.")
    try:
        service = EvaluationService(db)
        test_questions_dicts = [item.dict() for item in payload.test_questions]
        results = service.run_dynamic_pipeline_evaluation(
            retrieval_service=retrieval_service,
            test_questions=test_questions_dicts,
            run_name=payload.run_name
        )
        app_logger.info(f"Pipeline evaluation completed successfully. Run ID: {results.get('run_id')}")
        return ResponseBuilder.success(data=results, message="Pipeline evaluation completed successfully.")
    except Exception as e:
        app_logger.error("Ragas pipeline evaluation failed", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Pipeline evaluation failed: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get(
    "/api/v1/evaluate/runs",
    response_model=ApiResponse[List[dict]],
    status_code=status.HTTP_200_OK,
    tags=["Evaluation"],
    summary="List all evaluation runs",
    description="Retrieves history of overall evaluation runs stored in the database."
)
async def list_evaluation_runs(
    db: Session = Depends(get_db)
):
    from knowledge_hub.app.entity.evaluation import EvaluationRunEntity
    app_logger.info("API Endpoint: GET /api/v1/evaluate/runs requested.")
    try:
        runs = db.query(EvaluationRunEntity).order_by(EvaluationRunEntity.created_at.desc()).all()
        result = []
        for r in runs:
            created_str = r.created_at.isoformat() if r.created_at else None
            result.append({
                "run_id": str(r.run_id),
                "run_name": r.run_name,
                "provider": r.provider,
                "eval_model": r.eval_model,
                "avg_faithfulness": r.avg_faithfulness,
                "avg_answer_relevance": r.avg_answer_relevance,
                "avg_context_recall": r.avg_context_recall,
                "avg_context_precision": r.avg_context_precision,
                "created_at": created_str
            })
        app_logger.info(f"Successfully retrieved {len(result)} evaluation runs.")
        return ResponseBuilder.success(data=result, message=f"Successfully fetched {len(result)} runs")
    except Exception as e:
        app_logger.error("Failed to list evaluation runs", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Failed to fetch runs: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get(
    "/api/v1/evaluate/runs/{run_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    tags=["Evaluation"],
    summary="Get details of a specific evaluation run",
    description="Retrieves overall scores and query-by-query breakdown of evaluation results."
)
async def get_evaluation_run_details(
    run_id: str,
    db: Session = Depends(get_db)
):
    from knowledge_hub.app.entity.evaluation import EvaluationRunEntity
    app_logger.info(f"API Endpoint: GET /api/v1/evaluate/runs/{run_id} requested.")
    try:
        run = db.query(EvaluationRunEntity).filter(EvaluationRunEntity.run_id == run_id).first()
        if not run:
            app_logger.warning(f"Evaluation run '{run_id}' not found.")
            return ResponseBuilder.failure(
                message=f"Evaluation run with ID '{run_id}' not found",
                error_code=status.HTTP_404_NOT_FOUND
            )
        
        # Build individual test query details list
        individual_results = []
        for res in run.results:
            individual_results.append({
                "result_id": str(res.result_id),
                "question": res.question,
                "contexts": res.contexts,
                "answer": res.answer,
                "ground_truth": res.ground_truth,
                "faithfulness": res.faithfulness,
                "answer_relevance": res.answer_relevance,
                "context_recall": res.context_recall,
                "context_precision": res.context_precision
            })
            
        created_str = run.created_at.isoformat() if run.created_at else None
        
        result_data = {
            "run_id": str(run.run_id),
            "run_name": run.run_name,
            "provider": run.provider,
            "eval_model": run.eval_model,
            "avg_faithfulness": run.avg_faithfulness,
            "avg_answer_relevance": run.avg_answer_relevance,
            "avg_context_recall": run.avg_context_recall,
            "avg_context_precision": run.avg_context_precision,
            "created_at": created_str,
            "individual_results": individual_results
        }
        
        app_logger.info(f"Successfully retrieved details for evaluation run '{run_id}' with {len(individual_results)} individual scores.")
        return ResponseBuilder.success(data=result_data, message="Successfully fetched run details")
    except Exception as e:
        app_logger.error(f"Failed to fetch details for evaluation run '{run_id}'", exc_info=True)
        return ResponseBuilder.failure(
            message=f"Failed to fetch run details: {str(e)}",
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

if __name__ == "__main__":
        uvicorn.run(
            "knowledge_hub.app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
        )
