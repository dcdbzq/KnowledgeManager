from typing import Any

from .config import Settings, load_dotenv
from .llm.client import LLMClient
from .models import KnowledgeMetadata
from .observability.metrics import MetricsRecorder
from .retrieval.hybrid_retriever import HybridRetriever
from .retrieval.prompt_builder import PromptBuilder
from .retrieval.reranker import Reranker
from .storage.document_store import DocumentStore
from .storage.vector_store import VectorStore


class KnowledgeManager:
    def __init__(self, settings: Settings | None = None):
        load_dotenv()
        self.settings = settings or Settings()
        self.llm = LLMClient(self.settings)
        self.documents = DocumentStore(self.settings.db_path)
        self.vectors = VectorStore(self.settings.vector_path)
        self.metrics = MetricsRecorder()
        self.retriever = HybridRetriever(
            self.documents,
            self.vectors,
            self.llm,
            vector_weight=self.settings.vector_weight,
            keyword_weight=self.settings.keyword_weight,
        )
        self.reranker = Reranker(self.llm)
        self.prompt_builder = PromptBuilder(self.settings.token_limit)

    def addKnowledge(self, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.add_knowledge(text, metadata)

    def add_knowledge(self, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("knowledge text cannot be empty")
        with self.metrics.timer() as timer:
            classified = self.llm.classify(text)
            embedding = self.llm.embed(text)
            conflict = self._detect_conflict(text, embedding)
            merged = {**classified, **(metadata or {})}
            if conflict["has_conflict"]:
                merged["conflict_warning"] = conflict
            knowledge_metadata = KnowledgeMetadata.from_dict(merged)
            record = self.documents.add(text=text.strip(), metadata=knowledge_metadata)
            self.vectors.upsert(record.id, embedding)
        self.metrics.record(
            "add_knowledge",
            record_id=record.id,
            confidence=knowledge_metadata.confidence,
            needs_review=knowledge_metadata.needs_review,
            conflict_detected=conflict["has_conflict"],
            elapsed_ms=timer.elapsed_ms,
        )
        return {
            "id": record.id,
            "logical_id": record.logical_id,
            "version": record.version,
            "metadata": knowledge_metadata.to_dict(),
            "conflict": conflict,
            "elapsed_ms": timer.elapsed_ms,
        }

    def update_knowledge(self, logical_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        classified = self.llm.classify(text)
        merged = {**classified, **(metadata or {})}
        knowledge_metadata = KnowledgeMetadata.from_dict(merged)
        record = self.documents.update(logical_id=logical_id, text=text.strip(), metadata=knowledge_metadata)
        self.vectors.upsert(record.id, self.llm.embed(text))
        return {"id": record.id, "logical_id": record.logical_id, "version": record.version}

    def delete_knowledge(self, logical_id: str) -> None:
        self.documents.delete(logical_id)

    def query(self, question: str, top_k: int | None = None) -> dict[str, Any]:
        if not question or not question.strip():
            raise ValueError("question cannot be empty")
        top_k = top_k or self.settings.top_k
        with self.metrics.timer() as timer:
            hits, debug = self.retriever.retrieve(question, top_k=top_k)
            reranked = self.reranker.rerank(question, hits)
            prompt_data = self.prompt_builder.build(question, reranked)
        self.metrics.record(
            "query",
            question=question,
            hit_count=len(reranked),
            elapsed_ms=timer.elapsed_ms,
            used_tokens_estimate=prompt_data["used_tokens_estimate"],
        )
        return {
            "question": question,
            "hits": [hit.to_dict() for hit in reranked],
            "prompt": prompt_data["prompt"],
            "context": prompt_data["context"],
            "used_tokens_estimate": prompt_data["used_tokens_estimate"],
            "debug": debug,
            "elapsed_ms": timer.elapsed_ms,
        }

    def list_knowledge(self) -> list[dict[str, Any]]:
        return [
            {
                "id": record.id,
                "logical_id": record.logical_id,
                "version": record.version,
                "metadata": record.metadata.to_dict(),
                "text": record.text,
            }
            for record in self.documents.list_active()
        ]

    def _detect_conflict(self, text: str, embedding: list[float]) -> dict[str, Any]:
        if not self.settings.enable_conflict_check:
            return {"has_conflict": False, "severity": "none", "conflicting_ids": [], "reason": ""}
        active_records = self.documents.list_active()
        if not active_records:
            return {"has_conflict": False, "severity": "none", "conflicting_ids": [], "reason": ""}
        active_ids = {record.id for record in active_records}
        record_map = {record.id: record for record in active_records}
        candidates = []
        for record_id, score in self.vectors.search(embedding, active_ids, top_k=5):
            record = record_map.get(record_id)
            if not record:
                continue
            candidates.append(
                {
                    "id": record.id,
                    "summary": record.metadata.summary,
                    "text": record.text,
                    "score": round(score, 4),
                }
            )
        conflict = self.llm.detect_conflict(text, candidates)
        conflict["candidate_count"] = len(candidates)
        return conflict
