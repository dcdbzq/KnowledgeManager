from ..llm.client import LLMClient
from ..models import RetrievalHit


class Reranker:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def rerank(self, question: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        if not hits:
            return []
        candidates = [
            {
                "id": hit.id,
                "summary": hit.metadata.summary,
                "text": hit.text,
                "score": hit.score,
            }
            for hit in hits
        ]
        ranked_ids = self.llm.rerank(question, candidates)
        order = {record_id: index for index, record_id in enumerate(ranked_ids)}
        return sorted(hits, key=lambda hit: (order.get(hit.id, len(order)), -hit.score))
