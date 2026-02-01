"""Gemma Model Integration Scaffolding.

This module provides reference implementations for integrating Gemma models
via various providers (Vertex AI, Ollama, LlamaCpp).

These classes are designed to be adapted into the main `llm_client.py`
or used as standalone clients for specific nodes.
"""

from typing import Dict, List

# ============================================================================
# 1. Google Vertex AI (Cloud)
# ============================================================================


class VertexAIGemmaClient:
    """Client for Gemma models deployed on Google Vertex AI."""

    def __init__(self, project_id: str, location: str, endpoint_id: str):
        """Initialize Vertex AI client.

        Args:
            project_id: GCP Project ID.
            location: GCP Region (e.g., 'us-central1').
            endpoint_id: Vertex AI Endpoint ID.
        """
        try:
            from google.cloud import aiplatform
            from google.protobuf import json_format
            from google.protobuf.struct_pb2 import Value
        except ImportError:
            raise ImportError(
                "Please install 'google-cloud-aiplatform' to use VertexAIGemmaClient"
            )

        self.project_id = project_id
        self.location = location
        self.endpoint_id = endpoint_id

        self.api_endpoint = f"{location}-aiplatform.googleapis.com"
        client_options = {"api_endpoint": self.api_endpoint}
        self.client = aiplatform.gapic.PredictionServiceClient(
            client_options=client_options
        )
        self.endpoint_path = self.client.endpoint_path(
            project=project_id, location=location, endpoint=endpoint_id
        )

        # Imports for use in methods
        self._json_format = json_format
        self._Value = Value

    def predict(self, prompt: str, max_tokens: int = 256, **kwargs) -> str:
        """Send prediction request to Vertex AI Endpoint.
        """
        instance_dict = {"inputs": prompt, "max_tokens": max_tokens, **kwargs}

        # Convert dictionary to Protobuf Struct
        instance_value = self._Value()
        self._json_format.ParseDict(instance_dict, instance_value)
        instances = [instance_value]

        # Parameters (usually empty for custom trained models unless specified)
        parameters_dict = {}
        parameters = self._Value()
        self._json_format.ParseDict(parameters_dict, parameters)

        response = self.client.predict(
            endpoint=self.endpoint_path, instances=instances, parameters=parameters
        )

        # Parse response (structure depends on model signature, typically response.predictions[0])
        # For Gemma, it usually returns the generated text.
        return response.predictions[0]


# ============================================================================
# 2. Ollama (Local Service)
# ============================================================================


class OllamaGemmaClient:
    """Client for local Gemma models via Ollama API."""

    def __init__(
        self, model_name: str = "gemma:7b", base_url: str = "http://localhost:11434"
    ):
        """Initialize Ollama client.

        Args:
            model_name: Name of the model to use (e.g., 'gemma:7b').
            base_url: URL of the Ollama server.
        """
        import requests

        self.requests = requests
        self.base_url = base_url
        self.model_name = model_name
        self.generate_url = f"{base_url}/api/generate"
        self.chat_url = f"{base_url}/api/chat"

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """Generate text completion.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            **kwargs,
        }
        if system:
            payload["system"] = system

        response = self.requests.post(self.generate_url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Chat completion.

        Args:
            messages: List of dicts with 'role' and 'content'.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            **kwargs,
        }

        response = self.requests.post(self.chat_url, json=payload)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")


# ============================================================================
# 3. LlamaCpp (Local Embedded)
# ============================================================================


class LlamaCppGemmaClient:
    """Client for embedded local inference using llama-cpp-python."""

    def __init__(self, model_path: str, n_gpu_layers: int = -1, **kwargs):
        """Initialize LlamaCpp client.

        Args:
            model_path: Path to the .gguf model file.
            n_gpu_layers: Number of layers to offload to GPU (-1 for all).
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "Please install 'llama-cpp-python' to use LlamaCppGemmaClient.\n"
                "See: https://github.com/abetlen/llama-cpp-python"
            )

        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            chat_format="gemma",  # Important for Gemma models
            verbose=False,
            **kwargs,
        )

    def generate(self, prompt: str, max_tokens: int = 256, **kwargs) -> str:
        """Generate text.
        """
        output = self.llm(prompt, max_tokens=max_tokens, **kwargs)
        return output["choices"][0]["text"]

    def create_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Chat completion using built-in chat formatting.
        """
        output = self.llm.create_chat_completion(messages=messages, **kwargs)
        return output["choices"][0]["message"]["content"]


# ============================================================================
# 4. Google Colab Setup (Snippet)
# ============================================================================

COLAB_SETUP_SNIPPET = """
# Run this in a Google Colab cell to setup Gemma environment

# 1. Install Keras NLP
!pip install -U keras-nlp keras>=3.3.3

# 2. Setup Credentials (assuming stored in Colab Secrets)
import os
from google.colab import userdata

os.environ["KAGGLE_USERNAME"] = userdata.get('KAGGLE_USERNAME')
os.environ["KAGGLE_KEY"] = userdata.get('KAGGLE_KEY')
os.environ["KERAS_BACKEND"] = "jax"  # Use JAX for best performance

# 3. Load Model
import keras_nlp
import keras

# Mixed precision for efficiency
keras.config.set_floatx("bfloat16")

gemma_lm = keras_nlp.models.GemmaCausalLM.from_preset("gemma2_2b_en")
print("Model loaded successfully")
"""
