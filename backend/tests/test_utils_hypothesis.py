from hypothesis import given, strategies as st
from agent.utils import insert_citation_markers

@given(
    text=st.text(min_size=1, max_size=500),
    end_indices=st.lists(st.integers(min_value=0, max_value=500), max_size=5)
)
def test_insert_citation_never_raises(text, end_indices):
    """Property test to ensure insert_citation_markers never crashes."""
    # Filter indices to ensure they are within the text length
    valid_indices = [idx for idx in end_indices if idx <= len(text)]

    citations = [{"end_index": idx, "segments": []} for idx in valid_indices]

    try:
        result = insert_citation_markers(text, citations)
        assert isinstance(result, str)
        assert len(result) >= len(text)  # Citations only add text
    except Exception as e:
        pytest.fail(f"insert_citation_markers raised exception: {e}")

@given(st.text())
def test_insert_citation_empty_citations(text):
    """Test that providing empty citations returns the original text."""
    result = insert_citation_markers(text, [])
    assert result == text
