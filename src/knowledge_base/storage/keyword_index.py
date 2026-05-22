import math
import re
from collections import Counter, defaultdict

from ..models import KnowledgeRecord


class KeywordIndex:
    def __init__(self) -> None:
        self.doc_terms: dict[str, Counter[str]] = {}
        self.doc_freq: Counter[str] = Counter()
        self.doc_count = 0

    def build(self, records: list[KnowledgeRecord]) -> None:
        self.doc_terms.clear()
        self.doc_freq.clear()
        self.doc_count = len(records)
        for record in records:
            terms = Counter(tokenize(record.text + " " + " ".join(record.metadata.tags)))
            self.doc_terms[record.id] = terms
            for term in terms:
                self.doc_freq[term] += 1

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        query_terms = tokenize(query)
        if not query_terms or not self.doc_terms:
            return []
        scores: defaultdict[str, float] = defaultdict(float)
        for term in query_terms:
            idf = math.log((self.doc_count + 1) / (self.doc_freq.get(term, 0) + 1)) + 1
            for doc_id, terms in self.doc_terms.items():
                tf = terms.get(term, 0)
                if tf:
                    scores[doc_id] += (1 + math.log(tf)) * idf
        if not scores:
            return []
        max_score = max(scores.values()) or 1.0
        results = [(doc_id, score / max_score) for doc_id, score in scores.items()]
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    words = re.findall(r"[a-z0-9_\-]+|[\u4e00-\u9fff]{2,}", lowered)
    tokens: list[str] = []
    for word in words:
        if re.fullmatch(r"[\u4e00-\u9fff]+", word):
            tokens.extend(word[i : i + 2] for i in range(max(1, len(word) - 1)))
            if len(word) <= 6:
                tokens.append(word)
        else:
            tokens.append(word)
    stopwords = {"the", "and", "for", "with", "如何", "什么", "是否", "这个", "一个"}
    return [token for token in tokens if len(token) >= 2 and token not in stopwords]
