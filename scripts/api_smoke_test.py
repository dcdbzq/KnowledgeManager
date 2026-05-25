import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_base import KnowledgeManager


RESULTS_DIR = ROOT / "data" / "eval_results"


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["KB_DB_PATH"] = str(RESULTS_DIR / "api_smoke.sqlite")
    os.environ["KB_VECTOR_PATH"] = str(RESULTS_DIR / "api_smoke_vectors.json")
    os.environ["ENABLE_HYDE"] = os.getenv("ENABLE_HYDE", "false")
    os.environ["ENABLE_CONFLICT_CHECK"] = os.getenv("ENABLE_CONFLICT_CHECK", "false")

    for path in [RESULTS_DIR / "api_smoke.sqlite", RESULTS_DIR / "api_smoke_vectors.json"]:
        path.unlink(missing_ok=True)

    manager = KnowledgeManager()
    if not manager.llm.enabled:
        report = {"mode": "skipped", "reason": "LLM API is disabled or LLM_API_KEY is empty"}
        (RESULTS_DIR / "api_smoke_test.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    added = manager.addKnowledge(
        "API接口返回401通常表示访问令牌无效或已过期。调用方应重新获取token，并检查请求头Authorization格式。",
        metadata={"source_id": "api-smoke-001"},
    )
    result = manager.query("API 返回 401 怎么处理？", top_k=1)
    report = {
        "mode": "llm_api",
        "llm_enabled": manager.llm.enabled,
        "metadata": added["metadata"],
        "conflict": added["conflict"],
        "rewrite": result["debug"]["rewrite"],
        "hyde_answer": result["debug"].get("hyde_answer", ""),
        "hit_count": len(result["hits"]),
        "top_hit_source": result["hits"][0]["metadata"].get("source_id") if result["hits"] else None,
        "elapsed_ms": result["elapsed_ms"],
        "metrics_events": manager.metrics.events,
    }
    (RESULTS_DIR / "api_smoke_test.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
