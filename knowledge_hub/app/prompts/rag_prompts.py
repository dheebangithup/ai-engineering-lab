"""
Pre-defined Enterprise RAG Prompt Templates with Version Control.
"""

from knowledge_hub.app.prompts.prompt_registry import prompt_registry
from knowledge_hub.app.prompts.prompt_template import PromptTemplate


# ---------------------------------------------------------------------------
# Prompt Version 1.0.0 — Basic Strict Grounded QA Prompt
# ---------------------------------------------------------------------------
RAG_QA_PROMPT_V1_0 = PromptTemplate(
    name="rag_qa",
    version="v1.0.0",
    description="Standard strict RAG question-answering prompt with context grounding.",
    input_variables=["context", "query"],
    system_prompt=(
        "You are an enterprise AI assistant for Knowledge Hub.\n"
        "Answer the user's question accurately using ONLY the provided context.\n"
        "If the context does not contain sufficient information to answer, state clearly:\n"
        "\"I cannot answer this question based on the provided context.\"\n"
        "Do not make up facts or extrapolate beyond the provided text."
    ),
    user_template=(
        "Context Information:\n"
        "---------------------\n"
        "{context}\n"
        "---------------------\n\n"
        "User Question: {query}\n"
        "Answer:"
    ),
    is_active=False,
)

# ---------------------------------------------------------------------------
# Prompt Version 1.1.0 — Enhanced Citation-Aware RAG Prompt (Current Active)
# ---------------------------------------------------------------------------
RAG_QA_PROMPT_V1_1 = PromptTemplate(
    name="rag_qa",
    version="v1.1.0",
    description="Advanced citation-aware RAG prompt requiring source references and structured formatting.",
    input_variables=["context", "query"],
    system_prompt=(
        "You are an enterprise AI assistant for Knowledge Hub.\n"
        "Your goal is to provide comprehensive, factual, and strictly grounded answers.\n\n"
        "Guidelines:\n"
        "1. Rely ONLY on the context provided below.\n"
        "2. When stating facts, cite the source file and page number formatted as [Source: <filename> | Page <page>] when available.\n"
        "3. If the context does not provide sufficient detail, explicitly state what is missing.\n"
        "4. Keep your answer clear, professional, and well-structured using markdown."
    ),
    user_template=(
        "Retrieved Context:\n"
        "===================\n"
        "{context}\n"
        "===================\n\n"
        "Question: {query}\n\n"
        "Structured Answer (with inline citations):"
    ),
    is_active=True,
)


def register_default_prompts() -> None:
    """Register built-in versioned prompts with the global registry."""
    prompt_registry.register(RAG_QA_PROMPT_V1_0, set_active=False)
    prompt_registry.register(RAG_QA_PROMPT_V1_1, set_active=True)


# Auto-register default prompts on module load
register_default_prompts()
