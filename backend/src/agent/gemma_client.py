"""Gemma Client Integration

This module contains the client implementations for Google's Gemma models,
supporting various providers like Vertex AI, Ollama, and local execution.
"""

import logging

from config.app_config import config as app_config

logger = logging.getLogger(__name__)

class GemmaClient:
    """Base interface for Gemma clients, conforming to LLMClient standards."""
    
    def invoke(self, prompt: str, **kwargs) -> str:
        """Standard invoke method for compatibility with LangChain-like calls."""
        raise NotImplementedError("Subclasses must implement invoke")

class VertexAIGemmaClient(GemmaClient):
    """Client for Gemma models deployed on Google Vertex AI."""

    def __init__(self):
        """Initialize Vertex AI client using configuration from app_config.
        """
        try:
            from google.cloud import aiplatform
            from google.protobuf import json_format
            from google.protobuf.struct_pb2 import Value
        except ImportError:
            logger.error("google-cloud-aiplatform not installed.")
            raise ImportError("Please install 'google-cloud-aiplatform' to use VertexAIGemmaClient")

        self.project_id = app_config.vertex_project_id
        self.location = app_config.vertex_location
        self.endpoint_id = app_config.vertex_endpoint_id

        if not all([self.project_id, self.location, self.endpoint_id]):
            logger.error("Vertex AI configuration missing: project_id, location, or endpoint_id.")
            raise ValueError("Vertex AI configuration missing.")

        aiplatform.init(project=self.project_id, location=self.location)
        self.endpoint = aiplatform.Endpoint(self.endpoint_id)

        self._json_format = json_format
        self._Value = Value

    def invoke(self, prompt: str, **kwargs) -> str:
        """Send prediction request to Vertex AI Endpoint.
        """
        max_tokens = kwargs.get("max_tokens", 512)
        instance = {"inputs": prompt, "max_tokens": max_tokens}
        
        try:
            response = self.endpoint.predict(instances=[instance])
            # Vertex AI custom endpoints typically return a list of predictions
            if response.predictions:
                return str(response.predictions[0])
            return ""
        except Exception as e:
            logger.error(f"Vertex AI prediction failed: {e}")
            raise e

class OllamaGemmaClient(GemmaClient):
    """Client for local Gemma models via Ollama API."""

    def __init__(self, timeout: int = 120):
        """Initialize Ollama client.
        
        Args:
            timeout: Request timeout in seconds (default: 120).
        """
        import requests
        self.requests = requests
        self.base_url = app_config.ollama_base_url
        self.model_name = "gemini-1.5-flash" if app_config.gemma_model_name == "gemma:7b" else app_config.gemma_model_name
        self.generate_url = f"{self.base_url}/api/generate"
        self.timeout = timeout

    def invoke(self, prompt: str, **kwargs) -> str:
        """Generate text completion.
        """
        # Protect critical payload fields from kwargs override
        PROTECTED_KEYS = {"model", "prompt", "stream"}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in PROTECTED_KEYS}
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            **filtered_kwargs
        }

        try:
            response = self.requests.post(self.generate_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("response", "")
        except self.requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
        except self.requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise

def get_gemma_client() -> GemmaClient:
    """Factory function to get the configured Gemma client."""
    provider = (app_config.gemma_provider or "ollama").lower()
    if provider == "vertex":
        return VertexAIGemmaClient()
    elif provider == "ollama":
        return OllamaGemmaClient()
    elif provider == "google_genai":
        return GoogleGenAIGemmaClient()
    else:
        logger.warning(f"Unknown or unsupported Gemma provider: {provider}. Defaulting to Ollama.")
        return OllamaGemmaClient()

class GoogleGenAIGemmaClient(GemmaClient):
    """Client for Gemma models using the Google GenAI SDK (requires GEMINI_API_KEY)."""

    def __init__(self):
        """Initialize Google GenAI client.
        """
        try:
            import os

            from google import genai
        except ImportError:
            logger.error("google-genai not installed.")
            raise ImportError("Please install 'google-genai' to use GoogleGenAIGemmaClient")

        # Will automatically pick up GEMINI_API_KEY from environment
        self.client = genai.Client()
        self.model_name = "gemini-1.5-flash" if app_config.gemma_model_name == "gemma:7b" else app_config.gemma_model_name

        # Basic validation that we have an API key
        if not os.getenv("GEMINI_API_KEY"):
            logger.warning("GEMINI_API_KEY not found in environment. Client initialization may fail.")

    def invoke(self, prompt: str, **kwargs) -> str:
        """Generate text completion using Google GenAI SDK.
        """
        try:
            # We don't want to pass unrecognized kwargs to genai, so we filter out or ignore them
            # For this simple implementation, we just pass the prompt
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Google GenAI request failed: {e}")
            raise e
