import re

with open('backend/src/agent/rag.py', 'r') as f:
    content = f.read()

adapter_code = """
class LangChainEmbeddingAdapter:
    \"\"\"Adapter to make LangChain embeddings look like sentence-transformers for Chroma.\"\"\"
    def __init__(self, langchain_embeddings):
        self.lc_embeddings = langchain_embeddings

    def __call__(self, texts: List[str]) -> List[List[float]]:
        # This is the interface Chroma expects if passed as embedding_function
        return self.lc_embeddings.embed_documents(texts)

    def encode(self, texts: List[str]) -> List[List[float]]:
        return self.lc_embeddings.embed_documents(texts)
"""

# Insert adapter before DeepSearchRAG
content = content.replace("class DeepSearchRAG:", adapter_code + "\nclass DeepSearchRAG:")

rag_config_replacement = """class _RAGConfig:
    def __init__(self):
        self.enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
        self.enable_fallback = True
        self.max_documents = 5
        self.embedding_provider = os.getenv("RAG_EMBEDDING_PROVIDER", "local").lower() # 'local' or 'google_genai'

rag_config = _RAGConfig()

def is_rag_enabled() -> bool:
    return rag_config.enabled"""

content = re.sub(r'class _RAGConfig:.*?def is_rag_enabled\(\) -> bool:\n    return True', rag_config_replacement, content, flags=re.DOTALL)


# Update __init__ of DeepSearchRAG to use the configured embedder
init_replacement = """    def __init__(self, storage_type: str = "chroma"):
        if not is_rag_enabled():
            return

        self.storage_type = storage_type
        self.max_context_chunks = 20
        self.use_faiss = storage_type == "faiss"
        self.use_chroma = storage_type == "chroma"

        # Load embedding function based on configuration
        self.embedder = None
        embedding_function_for_chroma = None

        if rag_config.embedding_provider == "google_genai":
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                lc_embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
                self.embedder = LangChainEmbeddingAdapter(lc_embeddings)
                embedding_function_for_chroma = self.embedder
                logger.info("Using Google GenAI for RAG embeddings")
            except ImportError:
                logger.warning("langchain-google-genai not found, falling back to local embeddings")
                rag_config.embedding_provider = "local"

        if rag_config.embedding_provider == "local":
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            else:
                logger.warning("SentenceTransformers not available. Embeddings disabled.")

        if self.use_faiss:
            if not FAISS_AVAILABLE:
                logger.warning("FAISS not installed, falling back to Chroma.")
                self.use_faiss = False
                self.use_chroma = True
            elif self.embedder:
                self.doc_store = {}
                self.faiss_index = faiss.IndexFlatL2(384) # 384 is dimension of all-MiniLM-L6-v2, may break for other models if not handled

        if self.use_chroma:
            if not CHROMA_AVAILABLE:
                logger.warning("ChromaDB not available.")
            else:
                self.chroma = ChromaStore(
                    collection_name="deep_search_evidence",
                    persist_path="./chroma_db",
                    embedding_function=embedding_function_for_chroma
                )"""

content = re.sub(r'    def __init__\(self, storage_type: str = "chroma"\):.*?self\.chroma = ChromaStore\(\n                    collection_name="deep_search_evidence",\n                    persist_path="\./chroma_db"\n                \)', init_replacement, content, flags=re.DOTALL)


# Update create_rag_tool logic
create_rag_tool_replacement = """def create_rag_tool(resources):
    \"\"\"
    Returns an instance of DeepSearchRAG configured for tool use.
    \"\"\"
    if not is_rag_enabled():
        logger.warning("RAG is disabled via configuration.")
        return None
    return DeepSearchRAG()"""

content = re.sub(r'def create_rag_tool\(resources\):.*?return None', create_rag_tool_replacement, content, flags=re.DOTALL)


with open('backend/src/agent/rag.py', 'w') as f:
    f.write(content)
