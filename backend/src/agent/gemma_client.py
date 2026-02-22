"""Gemma Client Integration

This module contains the client implementations for Google's Gemma models,
supporting various providers like Vertex AI, Ollama, and local execution.
"""

import logging
import os
from typing import Any, Dict, List, Optional
from agent.configuration import Configuration
from config.app_config import config as app_config

logger = logging.getLogger(__name__)

class GemmaClient:
    """Base interface for Gemma clients, conforming to LLMClient standards."""
    
    def invoke(self, prompt: str, **kwargs) -> str:
        """Standard invoke method for compatibility with LangChain-like calls."""
        raise NotImplementedError("Subclasses must implement invoke")

class GoogleGenAIGemmaClient(GemmaClient):
    """Client for Gemma models via Google GenAI API (GEMINI_API_KEY)."""

    def __init__(self, model_name: Optional[str] = None):
        """Initialize Google GenAI client."""
        try:
            from google import genai
        except ImportError:
            logger.error("google-genai not installed.")
            raise ImportError("Please install 'google-genai' to use GoogleGenAIGemmaClient")

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in environment.")
            raise ValueError("GEMINI_API_KEY is required for GoogleGenAIGemmaClient")

        self.client = genai.Client(api_key=self.api_key)
        # Prefer passed model_name, fallback to config
        self.model_name = model_name or app_config.gemma_model_name or "gemma-2-27b-it"

    def invoke(self, prompt: str, **kwargs) -> str:
        """Generate text completion using Google GenAI SDK."""
        try:
            # Map common kwargs to GenAI config if needed
            config = {}
            if "max_tokens" in kwargs:
                config["max_output_tokens"] = kwargs["max_tokens"]
            if "temperature" in kwargs:
                config["temperature"] = kwargs["temperature"]

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Safe access to response text
            try:
                return response.text if response.text else ""
            except (ValueError, AttributeError):
                return ""

        except Exception:
            logger.error("Google GenAI (Gemma) call failed", exc_info=True)
            raise

class VertexAIGemmaClient(GemmaClient):
    """Client for Gemma models deployed on Google Vertex AI."""

    def __init__(self, model_name: Optional[str] = None):
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

        # TODO: Implement model_name to endpoint_id mapping if needed.
        # Currently defaults to configured vertex_endpoint_id.
        if model_name:
            logger.info(f"VertexAIGemmaClient initialized with model_name='{model_name}', but using configured endpoint_id='{self.endpoint_id}'. Mapping logic may be needed.")

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
        except Exception:
            logger.error("Vertex AI prediction failed", exc_info=True)
            raise

class OllamaGemmaClient(GemmaClient):
    """Client for local Gemma models via Ollama API."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize Ollama client.
        """
        import requests
        self.requests = requests
        self.base_url = app_config.ollama_base_url
        self.model_name = model_name or app_config.gemma_model_name or "gemma:7b"
        self.generate_url = f"{self.base_url}/api/generate"

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        Generate text completion.
        """
        # Separate top-level parameters from options
        options = {}
        for key in ["temperature", "top_p", "top_k", "num_predict", "stop", "repeat_penalty"]:
            if key in kwargs:
                options[key] = kwargs[key]

        # Map common keys
        if "max_tokens" in kwargs and "num_predict" not in options:
            options["num_predict"] = kwargs["max_tokens"]

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": options
        }

        try:
            # Add timeout to prevent hanging
            response = self.requests.post(self.generate_url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception:
            logger.error("Ollama call failed", exc_info=True)
            raise

def get_gemma_client(model_name: Optional[str] = None) -> GemmaClient:
    """Factory function to get the configured Gemma client.

    Args:
        model_name: Optional specific model name to use (e.g., passed from app_config model_* settings).
    """
    # Guard against None provider
    provider = (app_config.gemma_provider or "ollama").lower()

    # Priority 1: Google GenAI (explicit config)
    if provider in ("google_genai", "google"):
        return GoogleGenAIGemmaClient(model_name=model_name)

    # Priority 2: Vertex AI
    elif provider == "vertex":
        return VertexAIGemmaClient(model_name=model_name)

    # Priority 3: Ollama
    elif provider == "ollama":
        return OllamaGemmaClient(model_name=model_name)

    else:
        # Fallback Logic - Strict check for API Key before assuming Google GenAI
        if os.getenv("GEMINI_API_KEY"):
             logger.info(f"Gemma provider '{provider}' unknown. Defaulting to Google GenAI (API Key found).")
             return GoogleGenAIGemmaClient(model_name=model_name)

        # Default to Ollama if no API Key found
        logger.warning(f"Unknown provider: {provider} and no GEMINI_API_KEY. Defaulting to Ollama.")
        return OllamaGemmaClient(model_name=model_name)
