import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    db_path: str = os.getenv("KB_DB_PATH", "data/kb.sqlite")
    vector_path: str = os.getenv("KB_VECTOR_PATH", "data/vectors.json")
    vector_dimensions: int = int(os.getenv("KB_VECTOR_DIMENSIONS", "256"))
    top_k: int = int(os.getenv("KB_TOP_K", "5"))
    token_limit: int = int(os.getenv("KB_PROMPT_TOKEN_LIMIT", "1800"))
    vector_weight: float = float(os.getenv("KB_VECTOR_WEIGHT", "0.65"))
    keyword_weight: float = float(os.getenv("KB_KEYWORD_WEIGHT", "0.35"))


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            value = line.strip()
            if not value or value.startswith("#") or "=" not in value:
                continue
            key, raw = value.split("=", 1)
            os.environ.setdefault(key.strip(), raw.strip().strip('"').strip("'"))
