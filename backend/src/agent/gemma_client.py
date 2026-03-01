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
        """
        Invoke the Gemma model with the given prompt and optional generation parameters.
        
        Parameters:
            prompt (str): The text prompt to send to the model.
            **kwargs: Optional generation parameters (for example, `max_tokens`, temperature, or other provider-specific options).
        
        Returns:
            str: The generated text response from the model.
        
        Raises:
            NotImplementedError: If a subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement invoke")


class VertexAIGemmaClient(GemmaClient):
    """Client for Gemma models deployed on Google Vertex AI."""

    def __init__(self):
        """
        Initialize a Vertex AI endpoint client using configuration from app_config.
        
        Loads required google-cloud-aiplatform protobuf helpers, reads project, location, and endpoint IDs from app_config, initializes the Vertex AI platform, and constructs an Endpoint instance stored on self. Also preserves protobuf helpers on self as _json_format and _Value for later use.
        
        Raises:
            ImportError: If google-cloud-aiplatform or required protobuf modules are not installed.
            ValueError: If any of vertex_project_id, vertex_location, or vertex_endpoint_id are missing from app_config.
        """
        try:
            from google.cloud import aiplatform
            from google.protobuf import json_format
            from google.protobuf.struct_pb2 import Value
        except ImportError:
            logger.error("google-cloud-aiplatform not installed.")
            raise ImportError(
                "Please install 'google-cloud-aiplatform' to use VertexAIGemmaClient"
            )

        self.project_id = app_config.vertex_project_id
        self.location = app_config.vertex_location
        self.endpoint_id = app_config.vertex_endpoint_id

        if not all([self.project_id, self.location, self.endpoint_id]):
            logger.error(
                "Vertex AI configuration missing: project_id, location, or endpoint_id."
            )
            raise ValueError("Vertex AI configuration missing.")

        aiplatform.init(project=self.project_id, location=self.location)
        self.endpoint = aiplatform.Endpoint(self.endpoint_id)

        self._json_format = json_format
        self._Value = Value

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        Send a text prompt to the configured Vertex AI Endpoint and return the model's prediction.
        
        Parameters:
            max_tokens (int, optional): Maximum number of tokens to generate; passed via kwargs (default 512).
        
        Returns:
            str: The first prediction returned by the endpoint as a string, or an empty string if no predictions are present.
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
        """
        Create an Ollama Gemma client configured for local API calls.
        
        Args:
            timeout (int): Maximum time to wait for HTTP requests to the Ollama API, in seconds.
        """
        import requests

        self.requests = requests
        self.base_url = app_config.ollama_base_url
        self.model_name = app_config.gemma_model_name
        self.generate_url = f"{self.base_url}/api/generate"
        self.timeout = timeout

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        Generate a completion from the configured Ollama model using the provided prompt.
        
        Parameters:
            prompt (str): The input prompt to send to the model.
            **kwargs: Additional generation options that will be merged into the request payload.
                The following keys are ignored if present: "model", "prompt", "stream".
        
        Returns:
            completion (str): The model's response text from the API's "response" field, or an empty string if absent.
        
        Raises:
            TimeoutError: If the HTTP request times out after the configured timeout.
            requests.exceptions.RequestException: If the HTTP request fails for other HTTP/network reasons; this exception is re-raised.
            Exception: Other unexpected exceptions encountered during the call are logged and re-raised.
        """
        # Protect critical payload fields from kwargs override
        PROTECTED_KEYS = {"model", "prompt", "stream"}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in PROTECTED_KEYS}

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            **filtered_kwargs,
        }

        try:
            response = self.requests.post(
                self.generate_url, json=payload, timeout=self.timeout
            )
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
    """
    Obtain the Gemma client instance configured by app_config.gemma_provider.
    
    Supported providers: "vertex" -> VertexAIGemmaClient, "ollama" -> OllamaGemmaClient. If the configured provider is unrecognized, this function defaults to an OllamaGemmaClient and emits a warning.
    
    Returns:
        GemmaClient: An instantiated client matching the configured provider.
    """
    provider = (app_config.gemma_provider or "ollama").lower()
    if provider == "vertex":
        return VertexAIGemmaClient()
    elif provider == "ollama":
        return OllamaGemmaClient()
    else:
        logger.warning(
            f"Unknown or unsupported Gemma provider: {provider}. Defaulting to Ollama."
        )
        return OllamaGemmaClient()
