import os
import unittest
from unittest.mock import MagicMock, patch
import sys

# Ensure backend/src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from observability.config import is_enabled
from observability.langfuse import get_langfuse_handler, observe_span

class TestObservability(unittest.TestCase):

    def test_is_enabled_false_by_default(self):
        # Assuming ENV vars are not set or defaults
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_enabled())

    def test_is_enabled_true_with_keys(self):
        env = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-123",
            "LANGFUSE_SECRET_KEY": "sk-123"
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(is_enabled())

    def test_handler_creation_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            handler = get_langfuse_handler()
            self.assertIsNone(handler)

    def test_handler_creation_enabled(self):
        # If langfuse is installed (which it is in this environment), it should return a handler
        env = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-123",
            "LANGFUSE_SECRET_KEY": "sk-123",
            "LANGFUSE_HOST": "http://localhost:3000"
        }
        with patch.dict(os.environ, env, clear=True):
            handler = get_langfuse_handler()
            self.assertIsNotNone(handler)
            # We verified locally that it returns LangchainCallbackHandler

    def test_observe_span_no_error_when_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            # Should yield None or similar, but definitely not raise
            with observe_span("test_span") as span:
                pass

    @patch("observability.langfuse.observe")
    def test_observe_span_active_when_enabled(self, mock_observe):
        env = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-123",
            "LANGFUSE_SECRET_KEY": "sk-123"
        }

        # Mock context manager behavior
        mock_cm = MagicMock()
        mock_observe.return_value = mock_cm
        mock_span = MagicMock()
        mock_cm.__enter__.return_value = mock_span

        with patch.dict(os.environ, env, clear=True):
            with observe_span("test_span") as span:
                pass

            # Since observe is a decorator/context manager in the real code,
            # calling it returns the context manager.
            # with observe(...) -> calls observe(...) -> returns CM -> CM.__enter__

            mock_observe.assert_called_with(name="test_span")
            mock_cm.__enter__.assert_called()
            mock_cm.__exit__.assert_called()

    @patch("observability.langfuse.observe")
    def test_observe_span_propagates_exceptions(self, mock_observe):
        """Ensure that exceptions in the user code are not swallowed."""
        env = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-123",
            "LANGFUSE_SECRET_KEY": "sk-123"
        }

        # Mock context manager behavior
        mock_cm = MagicMock()
        mock_observe.return_value = mock_cm
        mock_span = MagicMock()
        mock_cm.__enter__.return_value = mock_span
        # Standard context manager behavior: __exit__ returns False/None to propagate exception
        mock_cm.__exit__.return_value = None

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                with observe_span("test_span"):
                    raise ValueError("Oops")

if __name__ == "__main__":
    unittest.main()
