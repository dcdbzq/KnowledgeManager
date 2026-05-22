import json
import math
import os


class VectorStore:
    def __init__(self, path: str):
        self.path = path
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.vectors = self._load()

    def upsert(self, record_id: str, vector: list[float]) -> None:
        self.vectors[record_id] = vector
        self._save()

    def delete(self, record_id: str) -> None:
        self.vectors.pop(record_id, None)
        self._save()

    def search(self, query_vector: list[float], candidate_ids: set[str] | None = None, top_k: int = 5) -> list[tuple[str, float]]:
        results = []
        for record_id, vector in self.vectors.items():
            if candidate_ids is not None and record_id not in candidate_ids:
                continue
            results.append((record_id, cosine_similarity(query_vector, vector)))
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def _load(self) -> dict[str, list[float]]:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return {key: list(map(float, value)) for key, value in data.items()}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(self.vectors, file, ensure_ascii=False)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
