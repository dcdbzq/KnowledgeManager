from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass
class KnowledgeMetadata:
    business_domain: str = "general"
    knowledge_type: str = "document"
    importance: str = "medium"
    expire_at: str | None = None
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0
    needs_review: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "KnowledgeMetadata":
        if not data:
            return cls()
        known = {
            "business_domain": data.get("business_domain", "general"),
            "knowledge_type": data.get("knowledge_type", "document"),
            "importance": data.get("importance", "medium"),
            "expire_at": data.get("expire_at"),
            "tags": list(data.get("tags", [])),
            "summary": data.get("summary", ""),
            "confidence": float(data.get("confidence", 0.0)),
            "needs_review": bool(data.get("needs_review", False)),
        }
        extra = {key: value for key, value in data.items() if key not in known}
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "business_domain": self.business_domain,
            "knowledge_type": self.knowledge_type,
            "importance": self.importance,
            "expire_at": self.expire_at,
            "tags": self.tags,
            "summary": self.summary,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
        }
        result.update(self.extra)
        return result


@dataclass
class KnowledgeRecord:
    id: str
    logical_id: str
    version: int
    text: str
    metadata: KnowledgeMetadata
    status: str = "active"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass
class RetrievalHit:
    id: str
    logical_id: str
    version: int
    text: str
    metadata: KnowledgeMetadata
    vector_score: float = 0.0
    keyword_score: float = 0.0
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "logical_id": self.logical_id,
            "version": self.version,
            "score": round(self.score, 4),
            "vector_score": round(self.vector_score, 4),
            "keyword_score": round(self.keyword_score, 4),
            "metadata": self.metadata.to_dict(),
            "text": self.text,
        }
