from ..llm.client import LLMClient
from ..models import RetrievalHit
from ..storage.document_store import DocumentStore
from ..storage.keyword_index import KeywordIndex
from ..storage.vector_store import VectorStore


class HybridRetriever:
    def __init__(
        self,
        document_store: DocumentStore,
        vector_store: VectorStore,
        llm: LLMClient,
        vector_weight: float,
        keyword_weight: float,
    ):
        self.document_store = document_store
        self.vector_store = vector_store
        self.llm = llm
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def retrieve(self, question: str, top_k: int) -> tuple[list[RetrievalHit], dict[str, object]]:
        rewrite = self.llm.rewrite_query(question)
        retrieval_query = str(rewrite.get("rewritten_query") or question)
        active_records = self.document_store.list_active()
        active_ids = {record.id for record in active_records}

        keyword_index = KeywordIndex()
        keyword_index.build(active_records)

        query_vector = self.llm.embed(retrieval_query)
        vector_hits = dict(self.vector_store.search(query_vector, active_ids, top_k=top_k * 3))
        keyword_hits = dict(keyword_index.search(retrieval_query + " " + " ".join(rewrite.get("keywords", [])), top_k=top_k * 3))

        merged_ids = set(vector_hits) | set(keyword_hits)
        record_map = {record.id: record for record in active_records}
        hits = []
        for record_id in merged_ids:
            record = record_map.get(record_id)
            if not record:
                continue
            vector_score = max(0.0, vector_hits.get(record_id, 0.0))
            keyword_score = keyword_hits.get(record_id, 0.0)
            score = self.vector_weight * vector_score + self.keyword_weight * keyword_score
            hits.append(
                RetrievalHit(
                    id=record.id,
                    logical_id=record.logical_id,
                    version=record.version,
                    text=record.text,
                    metadata=record.metadata,
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    score=score,
                )
            )
        hits.sort(key=lambda item: item.score, reverse=True)
        debug = {
            "rewrite": rewrite,
            "candidate_count": len(merged_ids),
            "active_document_count": len(active_records),
        }
        return hits[:top_k], debug
