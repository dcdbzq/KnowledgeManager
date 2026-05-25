import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_base import KnowledgeManager


QUERIES = [
    ("大额纸质专票多久寄出？", "sample-004"),
    ("API 返回 401 应该怎么处理？", "sample-005"),
    ("客户忘记管理员密码怎么办？", "sample-015"),
    ("免费版接口限流是多少？", "sample-024"),
    ("合同到期前什么时候提醒客户经理？", "sample-014"),
    ("数据库连接超时怎么排查？", "sample-012"),
]

RESULTS_DIR = ROOT / "data" / "eval_results"


def reset_data() -> None:
    for path in [RESULTS_DIR / "retrieval_eval.sqlite", RESULTS_DIR / "retrieval_eval_vectors.json"]:
        path.unlink(missing_ok=True)
    chroma_path = ROOT / "data" / "chroma"
    if chroma_path.exists():
        shutil.rmtree(chroma_path)


def main() -> None:
    if "--fallback" in sys.argv:
        os.environ["LLM_API_KEY"] = ""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["KB_DB_PATH"] = str(RESULTS_DIR / "retrieval_eval.sqlite")
    os.environ["KB_VECTOR_PATH"] = str(RESULTS_DIR / "retrieval_eval_vectors.json")
    reset_data()
    manager = KnowledgeManager()
    samples = json.loads((ROOT / "data" / "samples" / "sample_documents.json").read_text(encoding="utf-8"))
    for item in samples:
        manager.addKnowledge(item["text"], metadata={"source_id": item["id"]})

    hit_at_1 = 0
    hit_at_3 = 0
    rows = []
    for question, expected_source in QUERIES:
        result = manager.query(question, top_k=5)
        sources = [hit["metadata"].get("source_id") for hit in result["hits"]]
        hit_at_1 += int(bool(sources) and sources[0] == expected_source)
        hit_at_3 += int(expected_source in sources[:3])
        rows.append(
            {
                "question": question,
                "expected": expected_source,
                "top_sources": sources[:5],
                "hit@1": bool(sources) and sources[0] == expected_source,
                "hit@3": expected_source in sources[:3],
                "elapsed_ms": result["elapsed_ms"],
            }
        )

    report = {
        "documents": len(samples),
        "mode": "fallback" if not manager.llm.enabled else "llm_api",
        "queries": len(QUERIES),
        "hit@1": round(hit_at_1 / len(QUERIES), 3),
        "hit@3": round(hit_at_3 / len(QUERIES), 3),
        "rows": rows,
        "metrics_events": manager.metrics.events[-5:],
    }
    (RESULTS_DIR / "retrieval_eval.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manager.metrics.export_json(str(RESULTS_DIR / "metrics_events.json"))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
