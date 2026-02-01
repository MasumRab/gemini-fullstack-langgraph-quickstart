import importlib
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# Fixture to mock dependencies before importing the module under test
@pytest.fixture
def mock_dependencies():
    with patch.dict(
        sys.modules,
        {
            "sentence_transformers": MagicMock(),
            "faiss": MagicMock(),
            "langchain_text_splitters": MagicMock(),
            "chromadb": MagicMock(),
        },
    ):
        # We need to configure the mocks
        mock_st = sys.modules["sentence_transformers"]
        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_embedder.encode.return_value = np.zeros(384)
        mock_st.SentenceTransformer.return_value = mock_embedder

        mock_faiss = sys.modules["faiss"]
        mock_faiss.IndexFlatL2.return_value = MagicMock()
        mock_faiss.IndexIDMap.return_value = MagicMock()

        mock_splitter = sys.modules["langchain_text_splitters"]
        splitter_instance = MagicMock()
        splitter_instance.split_text.return_value = ["chunk1", "chunk2"]
        mock_splitter.RecursiveCharacterTextSplitter.return_value = splitter_instance

        yield {
            "embedder": mock_embedder,
            "faiss": mock_faiss,
            "splitter": splitter_instance,
        }


# Fixture to provide the DeepSearchRAG class and EvidenceChunk class
# ensuring the module is reloaded with mocked dependencies
# AND cleaned up afterwards to prevent pollution
@pytest.fixture
def rag_classes(mock_dependencies):
    import agent.rag as rag_module

    importlib.reload(rag_module)

    yield rag_module

    # Teardown: Remove the module from sys.modules so next import reloads it fresh (with real deps or whatever environment has)
    if "agent.rag" in sys.modules:
        del sys.modules["agent.rag"]


@pytest.fixture
def mock_config():
    with patch("config.app_config.config") as mock_cfg:
        mock_cfg.rag_store = "faiss"
        mock_cfg.dual_write = False
        yield mock_cfg


def test_initialization(rag_classes, mock_config, mock_dependencies):
    rag = rag_classes.DeepSearchRAG(config=mock_config)
    assert rag.use_faiss is True
    assert rag.use_chroma is False
    mock_dependencies["faiss"].IndexFlatL2.assert_called_with(384)
    mock_dependencies["embedder"].get_sentence_embedding_dimension.assert_called()


def test_ingest_research_results(rag_classes, mock_config, mock_dependencies):
    rag = rag_classes.DeepSearchRAG(config=mock_config)
    documents = [
        {"content": "Doc 1 content", "url": "http://example.com/1", "score": 0.9}
    ]
    subgoal_id = "sg_1"

    ids = rag.ingest_research_results(documents, subgoal_id)

    assert len(ids) == 2
    assert len(rag.doc_store) == 2
    # rag.index_with_ids is the mock returned by IndexIDMap
    # Bolt Optimization: Should be called once with batch
    assert rag.index_with_ids.add_with_ids.call_count == 1

    evidence = rag.doc_store[ids[0]]
    assert evidence.content == "chunk1"
    assert evidence.subgoal_id == subgoal_id


def test_retrieve_empty_index(rag_classes, mock_config):
    rag = rag_classes.DeepSearchRAG(config=mock_config)
    rag.index_with_ids.ntotal = 0
    results = rag.retrieve("query")
    assert results == []


def test_retrieve_success(rag_classes, mock_config):
    rag = rag_classes.DeepSearchRAG(config=mock_config)

    rag.index_with_ids.ntotal = 10
    rag.index_with_ids.search.return_value = (
        np.array([[0.1, 0.2]], dtype=np.float32),
        np.array([[0, 1]]),
    )

    rag.doc_store[0] = rag_classes.EvidenceChunk(
        content="res1",
        source_url="url1",
        subgoal_id="sg1",
        relevance_score=0.9,
        timestamp=0,
        chunk_id="c1",
    )
    rag.doc_store[1] = rag_classes.EvidenceChunk(
        content="res2",
        source_url="url2",
        subgoal_id="sg1",
        relevance_score=0.8,
        timestamp=0,
        chunk_id="c2",
    )

    results = rag.retrieve("query", top_k=2)
    assert len(results) == 2
    assert results[0][0].content == "res1"
    assert abs(results[0][1] - (1 / 1.1)) < 0.0001


def test_audit_and_prune(rag_classes, mock_config):
    rag = rag_classes.DeepSearchRAG(config=mock_config)
    subgoal_id = "sg1"
    rag.subgoal_evidence_map[subgoal_id] = [0, 1, 2]
    rag.doc_store[0] = rag_classes.EvidenceChunk("c1", "u", subgoal_id, 0.9, 0, "id1")
    rag.doc_store[1] = rag_classes.EvidenceChunk("c2", "u", subgoal_id, 0.4, 0, "id2")
    rag.doc_store[2] = rag_classes.EvidenceChunk("c3", "u", subgoal_id, 0.6, 0, "id3")

    result = rag.audit_and_prune(subgoal_id, relevance_threshold=0.5)

    assert result["status"] == "success"
    assert result["original_count"] == 3
    assert result["kept_count"] == 2
    assert result["pruned_count"] == 1


def test_get_context_for_synthesis(rag_classes, mock_config):
    rag = rag_classes.DeepSearchRAG(config=mock_config)
    rag.retrieve = MagicMock(
        return_value=[
            (rag_classes.EvidenceChunk("Content A", "Url A", "sg1", 0.9, 0, "1"), 0.9),
            (rag_classes.EvidenceChunk("Content B", "Url B", "sg1", 0.8, 0, "2"), 0.8),
        ]
    )

    context = rag.get_context_for_synthesis("query")
    assert "[Source: Url A]" in context
    assert "Content A" in context
    assert "---" in context


@patch("agent.rag.call_llm_robust")
def test_verify_subgoal_coverage(mock_llm, rag_classes, mock_config):
    rag = rag_classes.DeepSearchRAG(config=mock_config)
    rag.retrieve = MagicMock(
        return_value=[
            (rag_classes.EvidenceChunk("Content", "Url", "sg1", 0.9, 0, "1"), 0.9)
        ]
    )

    mock_llm.return_value = (
        '```json\n{"verified": true, "confidence": 0.9, "reasoning": "ok"}\n```'
    )

    result = rag.verify_subgoal_coverage("goal", "sg1", MagicMock())

    assert result["verified"] is True
    assert result["confidence"] == 0.9


def test_initialization_no_deps(mock_config):
    # Specialized test for missing dependencies
    with patch.dict(sys.modules):
        # Force missing modules
        for mod in ["sentence_transformers", "faiss", "chromadb"]:
            sys.modules[mod] = None

        import agent.rag as rag_module

        importlib.reload(rag_module)

        with pytest.raises(ImportError, match="sentence-transformers required"):
            rag_module.DeepSearchRAG(config=mock_config)

    # Cleanup here too
    if "agent.rag" in sys.modules:
        del sys.modules["agent.rag"]
