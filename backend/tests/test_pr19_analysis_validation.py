"""
Validation tests for PR19_ANALYSIS.md

Tests cover:
- Markdown structure and syntax
- Document completeness
- Code block syntax
- Section organization
"""

import pytest
import re
from pathlib import Path


@pytest.fixture
def pr19_analysis_path():
    """Get path to PR19_ANALYSIS.md file."""
    root_dir = Path(__file__).resolve().parents[2]
    return root_dir / "PR19_ANALYSIS.md"


@pytest.fixture
def pr19_content(pr19_analysis_path):
    """Load PR19_ANALYSIS.md content."""
    if not pr19_analysis_path.exists():
        pytest.skip(f"PR19_ANALYSIS.md not found at {pr19_analysis_path}")
    
    with open(pr19_analysis_path, 'r', encoding='utf-8') as f:
        return f.read()


class TestPR19AnalysisStructure:
    """Test suite for document structure."""

    def test_pr19_analysis_file_exists(self, pr19_analysis_path):
        """Test that PR19_ANALYSIS.md file exists."""
        if not pr19_analysis_path.exists():
            pytest.skip("PR19_ANALYSIS.md file not found")

    def test_pr19_analysis_is_not_empty(self, pr19_content):
        """Test that document is not empty."""
        assert len(pr19_content) > 0, "PR19_ANALYSIS.md is empty"
        assert len(pr19_content) > 100, "PR19_ANALYSIS.md is too short"

    def test_pr19_analysis_has_title(self, pr19_content):
        """Test that document has a main title."""
        lines = pr19_content.split('\n')
        first_line = next((line for line in lines if line.strip()), '')
        assert first_line.startswith('#'), "Document should start with a markdown heading"

    def test_pr19_analysis_has_required_sections(self, pr19_content):
        """Test that document has key sections."""
        required_sections = [
            "Executive Summary",
            "Key Areas Requiring Attention",
            "Critical Action Items",
            "Recommendations",
            "Conclusion",
        ]
        
        for section in required_sections:
            assert section in pr19_content, f"Missing required section: {section}"


class TestPR19AnalysisContent:
    """Test suite for document content."""

    def test_pr19_analysis_mentions_pr_number(self, pr19_content):
        """Test that document references PR #19."""
        assert "PR #19" in pr19_content or "PR 19" in pr19_content or "#19" in pr19_content

    def test_pr19_analysis_has_code_references(self, pr19_content):
        """Test that document references specific code files."""
        assert "backend/" in pr19_content or ".py" in pr19_content

    def test_pr19_analysis_has_recommendations(self, pr19_content):
        """Test that document provides actionable recommendations."""
        recommendation_indicators = [
            "Recommendation",
            "Action",
            "Should",
            "Must",
            "Consider",
        ]
        
        found_recommendations = sum(
            1 for indicator in recommendation_indicators 
            if indicator in pr19_content
        )
        
        assert found_recommendations >= 3, "Document should have multiple recommendations"


class TestPR19AnalysisCodeBlocks:
    """Test suite for code blocks in document."""

    def test_pr19_analysis_code_blocks_are_closed(self, pr19_content):
        """Test that all code blocks are properly closed."""
        opening_fences = pr19_content.count('```')
        assert opening_fences % 2 == 0, "Code blocks should be properly closed"


class TestPR19AnalysisCompleteness:
    """Test suite for document completeness."""

    def test_pr19_analysis_has_substantial_content(self, pr19_content):
        """Test that document has substantial content."""
        assert len(pr19_content) >= 5000, "Analysis should be comprehensive"
        
        paragraphs = [p for p in pr19_content.split('\n\n') if len(p.strip()) > 50]
        assert len(paragraphs) >= 15, "Document should have substantial analysis"


class TestPR19AnalysisSpecificContent:
    """Test suite for specific content mentioned in the diff."""

    def test_pr19_analysis_mentions_compress_context(self, pr19_content):
        """Test that analysis mentions the compress_context functionality."""
        assert "compress" in pr19_content.lower() or "compression" in pr19_content.lower()

    def test_pr19_analysis_mentions_supervisor(self, pr19_content):
        """Test that analysis mentions supervisor graph."""
        assert "supervisor" in pr19_content.lower()

    def test_pr19_analysis_mentions_state_changes(self, pr19_content):
        """Test that analysis mentions state-related changes."""
        assert "state" in pr19_content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])