import pytest
from unittest.mock import Mock
from tenacity import wait_none
from src.agent.llm_client import call_llm_robust

# Disable wait for tests to speed them up
call_llm_robust.retry.wait = wait_none()

class TestLLMClient:
    def test_invoke_interface(self):
        """Test client with .invoke() method (LangChain style)"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = "response content"
        mock_client.invoke.return_value = mock_response

        result = call_llm_robust(mock_client, "prompt")

        assert result == "response content"
        mock_client.invoke.assert_called_once_with("prompt")

    def test_invoke_interface_string_response(self):
        """Test client with .invoke() returning string directly"""
        mock_client = Mock()
        mock_client.invoke.return_value = "direct response"

        result = call_llm_robust(mock_client, "prompt")

        assert result == "direct response"

    def test_generate_interface(self):
        """Test client with .generate() method (Gemini style)"""
        mock_client = Mock()
        # Mocking hasattr to ensure it picks the right path
        del mock_client.invoke

        mock_response = Mock()
        mock_response.text = "generated text"
        mock_client.generate.return_value = mock_response

        result = call_llm_robust(mock_client, "prompt")

        assert result == "generated text"
        mock_client.generate.assert_called_once_with("prompt")

    def test_callable_interface(self):
        """Test client as a callable"""
        mock_client = Mock()
        del mock_client.invoke
        del mock_client.generate

        mock_response = Mock()
        mock_response.content = "callable content"
        mock_client.side_effect = lambda x, **kwargs: mock_response

        result = call_llm_robust(mock_client, "prompt")

        assert result == "callable content"

    def test_retry_logic_success_after_failure(self):
        """Test that it retries on exception"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = "success"

        # Fail twice, then succeed
        mock_client.invoke.side_effect = [Exception("Fail 1"), Exception("Fail 2"), mock_response]

        result = call_llm_robust(mock_client, "prompt")

        assert result == "success"
        assert mock_client.invoke.call_count == 3

    def test_retry_logic_failure_max_attempts(self):
        """Test that it raises exception after max retries"""
        mock_client = Mock()
        mock_client.invoke.side_effect = Exception("Persistent Fail")

        with pytest.raises(Exception) as excinfo:
            call_llm_robust(mock_client, "prompt")

        assert "Persistent Fail" in str(excinfo.value)
        # Should be called 3 times (default stop_after_attempt(3))
        assert mock_client.invoke.call_count == 3
