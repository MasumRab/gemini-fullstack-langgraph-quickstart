"""Unit tests for persistence functions.

Tests cover save/load operations, edge cases, and error handling.
Uses temporary directories to avoid touching real filesystem.
"""


class TestPersistence:
    """Tests for save_plan and load_plan functions."""

    def test_save_and_load_plan_roundtrip(self, tmp_path, monkeypatch):
        """Saved plan should be loadable."""
        from agent import persistence

        # Redirect PLAN_DIR to temp directory
        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        thread_id = "test-thread-123"
        todo_list = [{"id": "1", "title": "Task 1", "status": "pending"}]
        artifacts = {"doc1": "content1"}

        persistence.save_plan(thread_id, todo_list, artifacts)
        loaded = persistence.load_plan(thread_id)

        assert loaded is not None
        assert loaded["todo_list"] == todo_list
        assert loaded["artifacts"] == artifacts

    def test_load_plan_nonexistent_returns_none(self, tmp_path, monkeypatch):
        """Loading a nonexistent plan should return None."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        result = persistence.load_plan("nonexistent-thread")
        assert result is None

    def test_save_plan_with_empty_thread_id_does_nothing(self, tmp_path, monkeypatch):
        """Empty thread_id should not create a file."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        persistence.save_plan("", [], {})

        # No files should be created
        assert len(list(tmp_path.iterdir())) == 0

    def test_load_plan_with_empty_thread_id_returns_none(self, tmp_path, monkeypatch):
        """Empty thread_id should return None."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        result = persistence.load_plan("")
        assert result is None

    def test_thread_id_sanitization(self, tmp_path, monkeypatch):
        """Thread IDs with special chars should be sanitized."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        # Thread ID with special characters
        thread_id = "test/../../../etc/passwd"
        persistence.save_plan(thread_id, [{"task": "test"}], {})

        # File should be created with sanitized name
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        # Sanitized name should only contain safe characters
        filename = files[0].name
        assert ".." not in filename
        assert "/" not in filename

    def test_save_plan_creates_directory_if_missing(self, tmp_path, monkeypatch):
        """save_plan should create the plans directory if it doesn't exist."""
        from agent import persistence

        new_dir = tmp_path / "nested" / "plans"
        monkeypatch.setattr(persistence, "PLAN_DIR", str(new_dir))

        persistence.save_plan("test-id", [{"task": "test"}], {})

        assert new_dir.exists()
        assert (new_dir / "test-id.json").exists()

    def test_load_plan_with_corrupted_json_returns_none(self, tmp_path, monkeypatch, capsys):
        """Corrupted JSON should return None and not raise."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        # Create a corrupted file
        corrupted_file = tmp_path / "corrupted.json"
        corrupted_file.write_text("{ invalid json }", encoding="utf-8")

        result = persistence.load_plan("corrupted")

        assert result is None
        # Should print an error message
        captured = capsys.readouterr()
        assert "Error loading plan" in captured.out

    def test_save_plan_with_complex_data(self, tmp_path, monkeypatch):
        """Complex nested data should be saved correctly."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        todo_list = [
            {
                "id": "plan-0",
                "title": "Research topic",
                "query": "test query",
                "suggested_tool": "web_research",
                "status": "pending",
                "nested": {"key": "value", "list": [1, 2, 3]},
            }
        ]
        artifacts = {
            "summary": "This is a long summary...",
            "sources": "http://example.com",
        }

        persistence.save_plan("complex-test", todo_list, artifacts)
        loaded = persistence.load_plan("complex-test")

        assert loaded["todo_list"] == todo_list
        assert loaded["artifacts"] == artifacts

    def test_overwrite_existing_plan(self, tmp_path, monkeypatch):
        """Saving to an existing thread should overwrite."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        thread_id = "overwrite-test"

        # Save initial plan
        persistence.save_plan(thread_id, [{"version": 1}], {})

        # Overwrite with new plan
        persistence.save_plan(thread_id, [{"version": 2}], {"new": "data"})

        loaded = persistence.load_plan(thread_id)
        assert loaded["todo_list"] == [{"version": 2}]
        assert loaded["artifacts"] == {"new": "data"}

    def test_unicode_content(self, tmp_path, monkeypatch):
        """Unicode content should be handled correctly."""
        from agent import persistence

        monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))

        todo_list = [{"title": "研究テーマ", "emoji": "🔬🧪"}]
        artifacts = {"summary": "日本語のサマリー"}

        persistence.save_plan("unicode-test", todo_list, artifacts)
        loaded = persistence.load_plan("unicode-test")

        assert loaded["todo_list"] == todo_list
        assert loaded["artifacts"] == artifacts
