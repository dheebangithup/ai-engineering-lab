import json
import sys
import os
import logging
import traceback

# Setup basic logging to see evaluation details
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("evaluate_runner")

# Ensure project root is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(project_root)

try:
    from knowledge_hub.app.config.database import SessionLocal
    from knowledge_hub.app.service.evaluation_service import EvaluationService
except ImportError as err:
    logger.error("Failed to import required modules. Make sure your Python path is configured correctly.", exc_info=True)
    sys.exit(1)

def run_static_test(evaluator: EvaluationService):
    """
    Executes a static Ragas evaluation test using pre-defined question, context, and answer.
    """
    logger.info("Starting static dataset offline evaluation...")
    
    # Resolve path to the generated golden dataset JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "data", "attention_golden_set.json")
    
    logger.info(f"Loading test dataset from: {dataset_path}")
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            dummy_eval_set = json.load(f)
    except FileNotFoundError:
        logger.error(f"Dataset file not found at {dataset_path}. Falling back to basic default dataset.")
        dummy_eval_set = [
            {
                "question": "What is the primary benefit of Multi-Head Attention?",
                "contexts": [
                    "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions."
                ],
                "answer": "Multi-head attention enables the model to focus on information in different representation subspaces and positions simultaneously.",
                "ground_truth": "Multi-head attention lets the network project queries, keys, and values into multiple representation subspaces, attending to sequence information in parallel."
            }
        ]
    
    try:
        report = evaluator.run_evaluation(dummy_eval_set, run_name="CLI Offline Static Test Run")
        logger.info(f"Static evaluation completed successfully. Run ID: {report['run_id']}")
        print("\n===========================================")
        print("STATIC EVALUATION REPORT (LM Studio Embeddings)")
        print("===========================================")
        print(f"Run ID: {report['run_id']}")
        print("Aggregated Average Scores:")
        for metric, score in report['summary_scores'].items():
            print(f"  - {metric:22} : {score:.4f}")
        print("===========================================\n")
    except Exception as e:
        logger.error(f"Error during static evaluation: {e}")
        traceback.print_exc()

def run_dynamic_test(evaluator: EvaluationService, db):
    """
    Executes a dynamic RAG pipeline evaluation where queries are run through the live retrieval engine first.
    """
    logger.info("Starting dynamic RAG pipeline evaluation...")
    
    try:
        # Construct pipeline dependencies manually for CLI execution
        from knowledge_hub.app.embeddings import LocalLMStudioEmbeddingProvider
        from knowledge_hub.app.database.qdrant_store import QdrantStore
        from knowledge_hub.app.service import DocumentMetaDataService, RetrievalService, LlmService
        from knowledge_hub.app.repositories import DocumentMetaDataRepository, ChunkMetaDataRepository
        
        logger.info("Initializing metadata services and vector store connection...")
        metadata_service = DocumentMetaDataService(
            doc_repo=DocumentMetaDataRepository(db),
            chunk_repo=ChunkMetaDataRepository(db)
        )
        
        embeddings = LocalLMStudioEmbeddingProvider()
        vector_store = QdrantStore(embedding_provider=embeddings)
        llm_service = LlmService()
        
        retrieval_service = RetrievalService(
            document_metadata_service=metadata_service,
            vector_store=vector_store,
            llm_service=llm_service
        )
        
        # Resolve path to the generated golden dataset JSON
        dataset_path = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "data", "attention_golden_set.json")
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                golden_data = json.load(f)
            # Take a small subset of 2 questions so the CLI dynamic test runs quickly
            test_questions = [
                {
                    "question": item["question"],
                    "ground_truth": item["ground_truth"]
                }
                for item in golden_data[:2]
            ]
        except Exception:
            # Fallback
            test_questions = [
                {
                    "question": "What is the dimension of the embeddings in the system?",
                    "ground_truth": "The embedding dimension returned by the nomic-embed-text provider is 384."
                }
            ]
        
        logger.info("Running dynamic pipeline evaluation. Invoking live retrieval and LLM generation...")
        report = evaluator.run_dynamic_pipeline_evaluation(
            retrieval_service=retrieval_service,
            test_questions=test_questions,
            run_name="CLI Live Pipeline Test Run"
        )
        
        logger.info(f"Dynamic pipeline evaluation completed successfully. Run ID: {report['run_id']}")
        print("\n===========================================")
        print("DYNAMIC PIPELINE EVALUATION REPORT")
        print("===========================================")
        print(f"Run ID: {report['run_id']}")
        print("Aggregated Average Scores:")
        for metric, score in report['summary_scores'].items():
            print(f"  - {metric:22} : {score:.4f}")
        print("===========================================\n")
        
    except Exception as e:
        logger.error(f"Error during dynamic pipeline evaluation: {e}")
        traceback.print_exc()

def main():
    print("Initializing Database Connection session...")
    db = SessionLocal()
    try:
        evaluator = EvaluationService(db)
        
        # Run both evaluation profiles
        run_static_test(evaluator)
        # run_dynamic_test(evaluator, db)
        
    except Exception as main_err:
        logger.error(f"Failed to execute evaluations: {main_err}")
        traceback.print_exc()
    finally:
        logger.info("Closing database session connection.")
        db.close()

if __name__ == "__main__":
    main()
