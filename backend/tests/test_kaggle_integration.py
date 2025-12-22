
"""
Unit tests for backend/examples/kaggle_integration.py
"""

import pytest
from unittest.mock import patch, MagicMock
from examples.kaggle_integration import KaggleModelLoader, KaggleHuggingFaceClient, SimpleReActAgent, BaseLLMClient

# =============================================================================
# Tests for KaggleModelLoader
# =============================================================================

class TestKaggleModelLoader:
    def test_download_success(self):
        """Test successful model download."""
        mock_kagglehub = MagicMock()
        mock_kagglehub.model_download.return_value = "/path/to/model"
        with patch.dict("sys.modules", {"kagglehub": mock_kagglehub}):
            path = KaggleModelLoader.download("handle/model")
            assert path == "/path/to/model"
            mock_kagglehub.model_download.assert_called_once_with("handle/model", path=None)

    def test_download_import_error(self):
        """Test ImportError when kagglehub is not installed."""
        # Patch the internal import by mocking the 'builtins' __import__
        # to raise ImportError specifically when 'kagglehub' is requested.
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'kagglehub':
                raise ImportError("Mocked error")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
             with pytest.raises(ImportError, match="Please install 'kagglehub'"):
                 KaggleModelLoader.download("handle/model")

# =============================================================================
# Tests for KaggleHuggingFaceClient
# =============================================================================

class TestKaggleHuggingFaceClient:
    
    @patch("examples.kaggle_integration.KaggleModelLoader")
    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_init_download_and_load(self, mock_model, mock_tokenizer, mock_loader):
        """Test client initialization triggers download and load."""
        mock_loader.download.return_value = "/mock/path"
        
        client = KaggleHuggingFaceClient("handle/model")
        
        mock_loader.download.assert_called_once_with("handle/model")
        mock_tokenizer.from_pretrained.assert_called_once_with("/mock/path")
        mock_model.from_pretrained.assert_called_once()
        assert client.model_path == "/mock/path"

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_generate(self, mock_model_cls, mock_tokenizer_cls):
        """Test generate method."""
        # Setup mocks
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        mock_model_cls.from_pretrained.return_value = mock_model
        
        # Init client with local path to skip download
        with patch("os.path.exists", return_value=True):
            client = KaggleHuggingFaceClient("/local/path")

        # Mock tokenizer call
        inputs = MagicMock()
        inputs.input_ids.shape = [1, 5] # 5 input tokens
        mock_tokenizer.return_value = inputs
        mock_tokenizer.decode.return_value = "new tokens"

        # Mock model generate
        outputs = [MagicMock()] # Fake output tensor
        mock_model.generate.return_value = outputs
        
        # Execute
        result = client.generate("test prompt", temperature=0.5)
        
        # Assert
        assert result == "new tokens"
        mock_model.generate.assert_called_once()
        # Verify kwargs
        call_kwargs = mock_model.generate.call_args[1]
        assert call_kwargs["max_new_tokens"] == 512
        assert call_kwargs["do_sample"] is True
        assert call_kwargs["temperature"] == 0.5


# =============================================================================
# Tests for SimpleReActAgent
# =============================================================================

class MockLLM(BaseLLMClient):
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
    
    def generate(self, prompt, **kwargs):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return "Final Answer: Stop"

class TestSimpleReActAgent:
    
    def test_run_with_tool_use(self):
        """Test agent executing a tool and returning final answer."""
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.invoke.return_value = "Tool Result"
        
        # LLM Responses: Thought/Action -> Observation -> Final Answer
        responses = [
            "Thought: Need tool\nAction: test_tool\nAction Input: test input",
            "Thought: Got result\nFinal Answer: The answer is Tool Result"
        ]
        llm = MockLLM(responses)
        
        agent = SimpleReActAgent(llm, [mock_tool])
        result = agent.run("Query")
        
        assert result == "The answer is Tool Result"
        mock_tool.invoke.assert_called_once_with("test input")

    def test_run_max_steps(self):
        """Test agent hitting iteration limit."""
        llm = MockLLM(["Thought: Loop\nAction: test_tool\nAction Input: input"] * 10)
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.invoke.return_value = "res"
        
        agent = SimpleReActAgent(llm, [mock_tool])
        result = agent.run("Query", max_steps=2)
        
        assert result == "Agent stopped due to iteration limit."
        assert llm.call_count == 2

    def test_run_invalid_action(self):
        """Test agent handles invalid tool name."""
        responses = [
            "Thought: Typo\nAction: bad_tool\nAction Input: input",
            "Thought: Fixed\nFinal Answer: Done"
        ]
        llm = MockLLM(responses)
        agent = SimpleReActAgent(llm, [])
        
        result = agent.run("Query")
        assert result == "Done" 
        # Implicitly checked that it continued after invalid action

    def test_run_tool_exception(self):
        """Test agent handles tool exception."""
        mock_tool = MagicMock()
        mock_tool.name = "error_tool"
        mock_tool.invoke.side_effect = Exception("Tool Failure")
        
        responses = [
            "Thought: Error\nAction: error_tool\nAction Input: input",
            "Thought: Recovered\nFinal Answer: Handled"
        ]
        llm = MockLLM(responses)
        agent = SimpleReActAgent(llm, [mock_tool])
        
        result = agent.run("Query")
        assert result == "Handled"
