import os
from dataclasses import dataclass, field


def _env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value else default


def _env_optional_int(key: str) -> int | None:
    value = os.getenv(key)
    return int(value) if value else None


def _env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    llm_api_key: str = field(default_factory=lambda: _env_str("LLM_API_KEY"))
    llm_base_url: str = field(default_factory=lambda: _env_str("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"))
    llm_model: str = field(default_factory=lambda: _env_str("LLM_MODEL", "glm-4.7-flash"))
    embedding_model: str = field(default_factory=lambda: _env_str("EMBEDDING_MODEL", "embedding-3"))
    embedding_dimensions: int | None = field(default_factory=lambda: _env_optional_int("EMBEDDING_DIMENSIONS"))
    db_path: str = field(default_factory=lambda: _env_str("KB_DB_PATH", "data/kb.sqlite"))
    vector_path: str = field(default_factory=lambda: _env_str("KB_VECTOR_PATH", "data/vectors.json"))
    vector_dimensions: int = field(default_factory=lambda: _env_int("KB_VECTOR_DIMENSIONS", 256))
    top_k: int = field(default_factory=lambda: _env_int("KB_TOP_K", 5))
    token_limit: int = field(default_factory=lambda: _env_int("KB_PROMPT_TOKEN_LIMIT", 1800))
    vector_weight: float = field(default_factory=lambda: _env_float("KB_VECTOR_WEIGHT", 0.65))
    keyword_weight: float = field(default_factory=lambda: _env_float("KB_KEYWORD_WEIGHT", 0.35))


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
