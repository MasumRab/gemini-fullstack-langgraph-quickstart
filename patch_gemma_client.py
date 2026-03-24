import re

with open('backend/src/agent/gemma_client.py', 'r') as f:
    content = f.read()

new_class = """class GoogleGenAIGemmaClient(GemmaClient):
    \"\"\"Client for Gemma models via Google GenAI API.\"\"\"

    def __init__(self):
        \"\"\"Initialize Google GenAI client.\"\"\"
        try:
            from google import genai
        except ImportError:
            logger.error("google-genai not installed.")
            raise ImportError("Please install 'google-genai' to use GoogleGenAIGemmaClient")

        import os
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY environment variable is missing.")
            raise ValueError("GEMINI_API_KEY is required for GoogleGenAIGemmaClient")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = app_config.gemma_model_name

    def invoke(self, prompt: str, **kwargs) -> str:
        \"\"\"Generate text completion.\"\"\"
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Google GenAI generation failed: {e}")
            raise e

"""

# Insert before get_gemma_client
content = content.replace("def get_gemma_client() -> GemmaClient:", new_class + "def get_gemma_client() -> GemmaClient:")

# Update factory method
factory_replacement = """def get_gemma_client() -> GemmaClient:
    \"\"\"Factory function to get the configured Gemma client.\"\"\"
    provider = (app_config.gemma_provider or "ollama").lower()
    if provider == "vertex":
        return VertexAIGemmaClient()
    elif provider == "ollama":
        return OllamaGemmaClient()
    elif provider == "google_genai":
        return GoogleGenAIGemmaClient()
    else:
        logger.warning(f"Unknown or unsupported Gemma provider: {provider}. Defaulting to Ollama.")
        return OllamaGemmaClient()"""

content = re.sub(r'def get_gemma_client\(\) -> GemmaClient:.*?return OllamaGemmaClient\(\)', factory_replacement, content, flags=re.DOTALL)

with open('backend/src/agent/gemma_client.py', 'w') as f:
    f.write(content)
