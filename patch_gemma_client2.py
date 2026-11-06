import re

with open('backend/src/agent/gemma_client.py', 'r') as f:
    content = f.read()

# Fix the duplicate else block
content = content.replace("""    else:
        logger.warning(f"Unknown or unsupported Gemma provider: {provider}. Defaulting to Ollama.")
        return OllamaGemmaClient()
    else:
        logger.warning(f"Unknown or unsupported Gemma provider: {provider}. Defaulting to Ollama.")
        return OllamaGemmaClient()""", """    else:
        logger.warning(f"Unknown or unsupported Gemma provider: {provider}. Defaulting to Ollama.")
        return OllamaGemmaClient()""")


# Fix GoogleGenAIGemmaClient __init__ where ValueError is raised before setting api_key properly in exception message (not really an issue, but let's make it clean)
class_replacement = """class GoogleGenAIGemmaClient(GemmaClient):
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

        # Use provided model or default to gemini-2.5-flash for free tier if trying to use gemma but not specified correctly
        self.model_name = app_config.gemma_model_name
        if not self.model_name or self.model_name == "gemma:7b":
            self.model_name = "gemini-2.5-flash" # Fallback to gemini if gemma:7b (ollama default) is used

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
            raise e"""

content = re.sub(r'class GoogleGenAIGemmaClient.*?raise e', class_replacement, content, flags=re.DOTALL)


with open('backend/src/agent/gemma_client.py', 'w') as f:
    f.write(content)
