"""Gemma Client Integration

This module contains the client implementations for Google's Gemma models,
supporting various providers like Vertex AI, Ollama, and local execution.
"""

import logging
from typing import Any, Dict, List, Optional
from agent.configuration import Configuration
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
        """
        Initialize Vertex AI client using configuration from app_config.
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
        """
        Send prediction request to Vertex AI Endpoint.
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

    def __init__(self):
        """
        Initialize Ollama client.
        """
        import requests
        self.requests = requests
        self.base_url = app_config.ollama_base_url
        self.model_name = app_config.gemma_model_name
        self.generate_url = f"{self.base_url}/api/generate"

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        Generate text completion.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }

        try:
            response = self.requests.post(self.generate_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise e

def get_gemma_client() -> GemmaClient:
    """Factory function to get the configured Gemma client."""
    provider = app_config.gemma_provider.lower()
    if provider == "vertex":
        return VertexAIGemmaClient()
    elif provider == "ollama":
        return OllamaGemmaClient()
    else:
        logger.warning(f"Unknown or unsupported Gemma provider: {provider}. Defaulting to Ollama.")
        return OllamaGemmaClient()
