# Configuration for the transaction categorization pipeline
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class CategorizerConfig:
    default_llm: str = os.getenv("CATEGORIZER_DEFAULT_LLM", "gemini").lower()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("CATEGORIZER_GEMINI_MODEL", "gemini-2.5-flash-lite")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("CATEGORIZER_GROQ_MODEL", "llama-3.3-70b-versatile")
    batch_size: int = int(os.getenv("CATEGORIZER_BATCH_SIZE", "20"))
    retry_wait_sec: int = int(os.getenv("CATEGORIZER_RETRY_WAIT_SEC", "10"))
    max_retries: int = int(os.getenv("CATEGORIZER_MAX_RETRIES", "3"))
    worker_interval_sec: int = int(os.getenv("CATEGORIZER_WORKER_INTERVAL_SEC", "30"))
    batch_delay_sec: int = int(os.getenv("CATEGORIZER_BATCH_DELAY_SEC", "2"))


config = CategorizerConfig()
