import logging
import time
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_groq import ChatGroq

from knowledge_hub.app.config import app_settings
from knowledge_hub.app.entity.evaluation import EvaluationRunEntity, EvaluationResultEntity

logger = logging.getLogger("app")

class EvaluationService:
    """
    Service responsible for orchestrating RAG evaluation using Ragas.
    Supports both offline static dataset scoring and active dynamic pipeline testing.
    """
    def __init__(self, db: Session):
        if db is None:
            logger.error("EvaluationService initialization failed: Session database is None")
            raise ValueError("Database session must be provided.")
        self.db = db
        logger.info("EvaluationService initialized successfully with database session.")

    def _to_python_float(self, val: Any) -> float | None:
        """
        Safely converts raw Ragas/numpy values to standard Python floats or None.
        Handles None, NaN, and Inf values by converting them to clean SQL NULLs (None).
        """
        if val is None:
            return None
        try:
            import math
            # Try parsing value to float
            f_val = float(val)
            if math.isnan(f_val) or math.isinf(f_val):
                return None
            return f_val
        except (ValueError, TypeError):
            return None

    def _get_evaluator_components(self):
        """
        Configures and returns the LLM and Embeddings to use for Ragas evaluation based on configuration.
        """
        provider = app_settings.RAGAS_EVAL_PROVIDER.lower()
        model = app_settings.RAGAS_EVAL_MODEL

        logger.info(f"Initializing Ragas evaluation components (Provider: '{provider}', Model: '{model}')")

        try:
            # 1. Initialize Evaluator LLM
            if provider == "groq":
                if not app_settings.GROQ_API_KEY:
                    logger.error("Failed to initialize Groq evaluator: GROQ_API_KEY is not configured")
                    raise ValueError("Groq API key is missing in configuration.")
                llm = ChatGroq(
                    api_key=app_settings.GROQ_API_KEY,
                    model=model or "llama-3-70b-8192",
                    temperature=0.0
                )
            elif provider == "lm_studio":
                logger.info(f"Setting up ChatOpenAI evaluator wrapper pointing to LM Studio at {app_settings.LOCAL_LM_URL}")
                llm = ChatOpenAI(
                    base_url=app_settings.LOCAL_LM_URL,
                    api_key=app_settings.LOCAL_LM_API_KEY or "lm-studio",
                    model=model or app_settings.LOCAL_LM_CHAT_MODEL,
                    temperature=0.0
                )
            elif provider == "openai":
                llm = ChatOpenAI(
                    model=model or "gpt-4-turbo",
                    temperature=0.0
                )
            else:
                logger.warning(f"Unknown evaluator provider '{provider}', falling back to default lm_studio.")
                llm = ChatOpenAI(
                    base_url=app_settings.LOCAL_LM_URL,
                    api_key=app_settings.LOCAL_LM_API_KEY or "lm-studio",
                    model=model or app_settings.LOCAL_LM_CHAT_MODEL,
                    temperature=0.0
                )

            # 2. Initialize Evaluator Embeddings (using the same backend settings as LocalLMStudioEmbeddingProvider)
            logger.info(f"Configuring OpenAIEmbeddings evaluator client pointing to LM Studio: URL={app_settings.LOCAL_LM_URL}, Model={app_settings.LOCAL_LM_EMBEDDING_MODEL}")
            embeddings = OpenAIEmbeddings(
                base_url=app_settings.LOCAL_LM_URL,
                api_key=app_settings.LOCAL_LM_API_KEY or "lm-studio",
                model=app_settings.LOCAL_LM_EMBEDDING_MODEL,
                check_embedding_ctx_length=False
            )
            
            logger.info("Ragas evaluation LLM and Embeddings initialized successfully.")
            return llm, embeddings

        except Exception as e:
            logger.error(f"Error during Ragas evaluation components initialization: {str(e)}", exc_info=True)
            raise e

    def run_evaluation(self, test_set: List[Dict[str, Any]], run_name: str = None) -> Dict[str, Any]:
        """
        Runs Ragas evaluation over a provided static dataset list.
        Each test item must look like:
        {
            "question": "...",
            "contexts": ["chunk 1 text", "chunk 2 text"],
            "answer": "Generated RAG answer",
            "ground_truth": "Expected ideal answer"
        }
        """
        # 1. Validation
        if not test_set:
            logger.error("Validation Error: Evaluation test set is empty or None")
            raise ValueError("Evaluation test set cannot be empty.")

        logger.info(f"Starting Ragas evaluation for run '{run_name or 'unnamed'}' containing {len(test_set)} test cases.")

        for i, item in enumerate(test_set):
            # Check required fields
            if "question" not in item or not str(item["question"]).strip():
                logger.error(f"Validation Error at test item index {i}: 'question' is missing or empty.")
                raise ValueError(f"Each test item must contain a valid, non-empty 'question' key. Found error at index {i}.")
            if "contexts" not in item or not isinstance(item["contexts"], list):
                logger.error(f"Validation Error at test item index {i}: 'contexts' is missing or not a list.")
                raise ValueError(f"Each test item must contain a 'contexts' list. Found error at index {i}.")
            if "answer" not in item:
                logger.error(f"Validation Error at test item index {i}: 'answer' key is missing.")
                raise ValueError(f"Each test item must contain a valid 'answer' key. Found error at index {i}.")

        start_time = time.perf_counter()

        try:
            # 2. Format dataset for Ragas
            questions = [item["question"] for item in test_set]
            contexts = [item["contexts"] for item in test_set]
            answers = [item["answer"] for item in test_set]
            # In this version of Ragas, context_recall and context_precision require a 'reference' column (string)
            references = [item["ground_truth"] if item.get("ground_truth") else "" for item in test_set]

            data_dict = {
                "question": questions,
                "contexts": contexts,
                "answer": answers,
                "reference": references
            }
            
            logger.info("Formatting dataset into HuggingFace Dataset format.")
            dataset = Dataset.from_dict(data_dict)
            
            # Get configured evaluator components
            llm, embeddings = self._get_evaluator_components()

            # 3. Execute Ragas Metrics Computation
            logger.info("Triggering Ragas evaluation metrics computation (faithfulness, answer_relevance, context_recall, context_precision)...")
            eval_start = time.perf_counter()
            result = evaluate(
                dataset=dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_recall,
                    context_precision
                ],
                llm=llm,
                embeddings=embeddings
            )
            eval_latency = time.perf_counter() - eval_start
            logger.info(f"Ragas evaluation computations succeeded in {eval_latency:.2f} seconds.")

            # 4. Save results to PostgreSQL database
            logger.info("Saving Ragas evaluation run averages and detailed breakdown to PostgreSQL...")
            # Safe key lookup from Ragas EvaluationResult's internal _repr_dict (containing averages)
            avg_faithfulness = None
            avg_answer_relevance = None
            avg_context_recall = None
            avg_context_precision = None
            
            if hasattr(result, "_repr_dict") and isinstance(result._repr_dict, dict):
                avg_faithfulness = result._repr_dict.get("faithfulness")
                avg_answer_relevance = result._repr_dict.get("answer_relevancy")
                avg_context_recall = result._repr_dict.get("context_recall")
                avg_context_precision = result._repr_dict.get("context_precision")
            else:
                # Fallback to computing averages manually from individual scores
                try:
                    avg_faithfulness = sum(result["faithfulness"]) / len(result["faithfulness"])
                except Exception:
                    pass
                try:
                    avg_answer_relevance = sum(result["answer_relevancy"]) / len(result["answer_relevancy"])
                except Exception:
                    pass
                try:
                    avg_context_recall = sum(result["context_recall"]) / len(result["context_recall"])
                except Exception:
                    pass
                try:
                    avg_context_precision = sum(result["context_precision"]) / len(result["context_precision"])
                except Exception:
                    pass

            db_run = EvaluationRunEntity(
                run_name=run_name or f"Run at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                provider=app_settings.RAGAS_EVAL_PROVIDER,
                eval_model=app_settings.RAGAS_EVAL_MODEL or "default",
                avg_faithfulness=self._to_python_float(avg_faithfulness),
                avg_answer_relevance=self._to_python_float(avg_answer_relevance),
                avg_context_recall=self._to_python_float(avg_context_recall),
                avg_context_precision=self._to_python_float(avg_context_precision)
            )
            
            self.db.add(db_run)
            self.db.flush()  # Populates db_run.run_id
            
            # Save query-by-query breakdown
            for i, item in enumerate(test_set):
                db_result = EvaluationResultEntity(
                    run_id=db_run.run_id,
                    question=item["question"],
                    contexts=item["contexts"],
                    answer=item["answer"],
                    ground_truth=item.get("ground_truth"),
                    faithfulness=self._to_python_float(result.scores[i].get("faithfulness")),
                    answer_relevance=self._to_python_float(result.scores[i].get("answer_relevancy")),
                    context_recall=self._to_python_float(result.scores[i].get("context_recall")),
                    context_precision=self._to_python_float(result.scores[i].get("context_precision"))
                )
                self.db.add(db_result)
            
            self.db.commit()
            total_latency = time.perf_counter() - start_time
            logger.info(f"Saved evaluation history successfully. Run ID: '{db_run.run_id}'. Total execution time: {total_latency:.2f} seconds.")

            summary_scores = {}
            f_clean = self._to_python_float(avg_faithfulness)
            r_clean = self._to_python_float(avg_answer_relevance)
            rc_clean = self._to_python_float(avg_context_recall)
            pr_clean = self._to_python_float(avg_context_precision)

            if f_clean is not None: summary_scores["faithfulness"] = f_clean
            if r_clean is not None: summary_scores["answer_relevancy"] = r_clean
            if rc_clean is not None: summary_scores["context_recall"] = rc_clean
            if pr_clean is not None: summary_scores["context_precision"] = pr_clean

            # Clean individual scores list of dictionaries
            cleaned_individual_scores = []
            for score_dict in result.scores:
                cleaned_dict = {}
                for k, v in score_dict.items():
                    cleaned_dict[k] = self._to_python_float(v)
                cleaned_individual_scores.append(cleaned_dict)

            return {
                "run_id": str(db_run.run_id),
                "summary_scores": summary_scores,
                "individual_scores": cleaned_individual_scores
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error occurred during Ragas evaluation execution or storage: {str(e)}", exc_info=True)
            raise e

    def run_dynamic_pipeline_evaluation(
        self,
        retrieval_service: Any,
        test_questions: List[Dict[str, str]],
        run_name: str = None
    ) -> Dict[str, Any]:
        """
        Runs the actual RAG pipeline for each query dynamically using RetrievalService,
        collects retrieved contexts and generated answers, and computes Ragas scores.
        """
        from knowledge_hub.app.model.search_request import SearchRequest

        # 1. Validation
        if not test_questions:
            logger.error("Validation Error: List of test questions is empty or None")
            raise ValueError("Test questions list cannot be empty.")
        if retrieval_service is None:
            logger.error("Validation Error: RetrievalService instance is None")
            raise ValueError("RetrievalService must be provided for dynamic evaluation.")

        logger.info(f"Starting dynamic RAG pipeline evaluation for {len(test_questions)} questions...")

        test_set = []
        for i, item in enumerate(test_questions):
            question = item.get("question")
            if not question or not str(question).strip():
                logger.error(f"Validation Error at dynamic question index {i}: 'question' is missing or empty.")
                raise ValueError(f"Each dynamic query must contain a valid, non-empty 'question' key. Error at index {i}.")
            
            ground_truth = item.get("ground_truth", "")

            # Trigger actual RetrievalService search and LLM generation
            logger.info(f"Dynamic Retrieval [{i+1}/{len(test_questions)}]: Querying RAG pipeline for '{question}'")
            try:
                search_request = SearchRequest(
                    query=question,
                    enable_llm_generation=True,
                    prompt_name="rag_qa"  # Default prompt name
                )
                response = retrieval_service.search(search_request)
                
                if not response or not response.success or not response.data:
                    logger.warning(f"Failed to fetch results from active RAG pipeline for query: '{question}'. Skipping.")
                    continue
                
                retrieval_data = response.data
                
                # Extract retrieved chunks text content
                contexts = []
                if retrieval_data.search_response and retrieval_data.search_response.results:
                    contexts = [
                        res.document.content for res in retrieval_data.search_response.results
                    ]
                else:
                    logger.warning(f"No vector candidate chunks returned for query: '{question}'")

                # Extract generated answer
                answer = ""
                if retrieval_data.llm_response:
                    answer = retrieval_data.llm_response.answer
                else:
                    logger.warning(f"No LLM text answer generated for query: '{question}'")

                test_set.append({
                    "question": question,
                    "contexts": contexts,
                    "answer": answer,
                    "ground_truth": ground_truth
                })
                logger.info(f"Dynamic Retrieval [{i+1}/{len(test_questions)}] Success: Chunks={len(contexts)}, Answer length={len(answer)}")
                
            except Exception as pipeline_err:
                logger.error(f"Error querying active RAG pipeline for query '{question}': {str(pipeline_err)}", exc_info=True)
                # Keep running other queries
                continue

        if not test_set:
            logger.error("RAG pipeline dynamic execution failed to retrieve results for all queries in the test set.")
            raise RuntimeError("All queries in the test set failed to run through the dynamic RAG pipeline.")

        logger.info(f"Dynamic pipeline execution phase completed. Collected {len(test_set)} successful query results out of {len(test_questions)} inputs.")

        # 2. Run Ragas evaluation over generated dataset
        return self.run_evaluation(test_set, run_name=run_name)
