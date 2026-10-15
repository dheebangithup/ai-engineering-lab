from pathlib import Path
import pytest

from jarvis.tools.implementations import register_default_tools
from rank_bm25 import BM25Okapi
from jarvis.tools.schemas import ToolDefinition
from jarvis.tools.tool_discovery import ToolDiscovery, tokenize
from jarvis.tools.tool_registry import ToolRegistry


@pytest.fixture
def populated_registry(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry()
    register_default_tools(registry, allowed_base_dir=tmp_path)
    return registry


@pytest.fixture
def discovery(populated_registry: ToolRegistry) -> ToolDiscovery:
    return ToolDiscovery(populated_registry)


def test_tokenize_filters_stop_words_and_punctuation() -> None:
    text = "Find all the files, in the project!"
    tokens = tokenize(text)
    assert "find" in tokens
    assert "files" in tokens
    assert "project" in tokens
    assert "the" not in tokens
    assert "in" not in tokens
    assert "all" not in tokens


def test_discovery_relevant_tool(discovery: ToolDiscovery) -> None:
    # "Find all Python files in the project" should match list_files or search_files
    results = discovery.discover("Find all Python files in the project")
    assert len(results) > 0
    top_ids = [t.id for t in results]
    assert "list_files" in top_ids or "search_files" in top_ids
    # Verify they are ToolDefinitions (no implementations exposed)
    for tool_def in results:
        assert isinstance(tool_def, ToolDefinition)
        assert hasattr(tool_def, "parameters")


def test_discovery_reads_content_matches_read_file(discovery: ToolDiscovery) -> None:
    results = discovery.discover("Read the complete text of a file")
    assert len(results) > 0
    assert results[0].id == "read_file"


def test_discovery_command_matches_run_command(discovery: ToolDiscovery) -> None:
    results = discovery.discover("Run a system command safely")
    assert len(results) > 0
    assert results[0].id == "run_command"


def test_discovery_no_match_returns_empty_list(discovery: ToolDiscovery) -> None:
    results = discovery.discover("bake a chocolate cake with frosting")
    assert results == []


def test_discovery_empty_query_returns_empty_list(discovery: ToolDiscovery) -> None:
    assert discovery.discover("") == []
    assert discovery.discover("   ") == []
    assert discovery.discover("the an a in") == []


def test_discovery_max_results_limit(discovery: ToolDiscovery) -> None:
    # Query with generic word matching multiple tools
    results = discovery.discover("file directory", max_results=2)
    assert len(results) <= 2


def test_discovery_empty_registry() -> None:
    empty_registry = ToolRegistry()
    empty_discovery = ToolDiscovery(empty_registry)
    assert empty_discovery.discover("find files") == []


def test_bm25_okapi_direct() -> None:
    corpus = [
        ["python", "files", "list"],
        ["command", "execute", "terminal"],
        ["write", "file", "disk"],
    ]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(["python"])
    assert scores[0] > 0.0
    assert scores[1] == 0.0
