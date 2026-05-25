import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_base import KnowledgeManager
from knowledge_base.config import Settings, load_dotenv
from knowledge_base.llm.client import LLMClient


RESULTS_DIR = ROOT / "data" / "eval_results"
QUESTIONS = [
    {
        "question": "大额纸质专票多久寄出？",
        "expected_internal_fact": "金额超过10万元的纸质专票通常3个工作日内寄出。",
    },
    {
        "question": "API 返回 401 应该怎么处理？",
        "expected_internal_fact": "401通常表示访问令牌无效或已过期，应重新获取token并检查Authorization格式。",
    },
    {
        "question": "合同到期前什么时候提醒客户经理？",
        "expected_internal_fact": "系统会在合同到期前60天、30天和7天提醒客户经理。",
    },
]


def parse_sleep() -> float:
    if "--sleep" not in sys.argv:
        return 3.0
    index = sys.argv.index("--sleep")
    return float(sys.argv[index + 1])


def main() -> None:
    load_dotenv()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["KB_DB_PATH"] = str(RESULTS_DIR / "rag_comparison.sqlite")
    os.environ["KB_VECTOR_PATH"] = str(RESULTS_DIR / "rag_comparison_vectors.json")

    for path in [RESULTS_DIR / "rag_comparison.sqlite", RESULTS_DIR / "rag_comparison_vectors.json"]:
        path.unlink(missing_ok=True)

    # Build the local index with fallback logic so this comparison only spends API calls on answering.
    old_enable_llm = os.environ.get("ENABLE_LLM")
    os.environ["ENABLE_LLM"] = "false"
    manager = KnowledgeManager()
    samples = json.loads((ROOT / "data" / "samples" / "sample_documents.json").read_text(encoding="utf-8"))
    for item in samples:
        manager.addKnowledge(item["text"], metadata={"source_id": item["id"]})

    if old_enable_llm is None:
        os.environ.pop("ENABLE_LLM", None)
    else:
        os.environ["ENABLE_LLM"] = old_enable_llm

    answer_llm = LLMClient(Settings())
    sleep_seconds = parse_sleep()
    rows = []
    for item in QUESTIONS:
        question = item["question"]
        retrieval = manager.query(question, top_k=5)
        direct_answer = answer_llm.answer_direct(question)
        time.sleep(sleep_seconds)
        rag_answer = answer_llm.answer_with_prompt(retrieval["prompt"])
        time.sleep(sleep_seconds)
        rows.append(
            {
                "question": question,
                "expected_internal_fact": item["expected_internal_fact"],
                "direct_llm_answer": direct_answer,
                "rag_answer": rag_answer,
                "retrieved_sources": [hit["metadata"].get("source_id") for hit in retrieval["hits"]],
                "used_tokens_estimate": retrieval["used_tokens_estimate"],
                "manual_direct_llm_score": None,
                "manual_rag_score": None,
                "notes": "Scores are left for human review; use 0-5 for factual correctness.",
            }
        )

    report = {
        "mode": "llm_api" if answer_llm.enabled else "llm_disabled",
        "comparison_count": len(rows),
        "rows": rows,
    }
    (RESULTS_DIR / "rag_comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
