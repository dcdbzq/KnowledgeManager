import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_base import KnowledgeManager


RESULTS_DIR = ROOT / "data" / "eval_results"

EXPECTED = {
    "sample-001": {"business_domain": "customer_service"},
    "sample-002": {"business_domain": "product"},
    "sample-003": {"business_domain": "hr"},
    "sample-004": {"business_domain": "finance"},
    "sample-005": {"business_domain": "technical"},
    "sample-006": {"business_domain": "sales"},
    "sample-007": {"business_domain": "operations"},
    "sample-008": {"business_domain": "customer_service"},
    "sample-009": {"business_domain": "product"},
    "sample-010": {"business_domain": "finance"},
    "sample-011": {"business_domain": "policy"},
    "sample-012": {"business_domain": "technical"},
    "sample-013": {"business_domain": "hr"},
    "sample-014": {"business_domain": "sales"},
    "sample-015": {"business_domain": "customer_service", "knowledge_type": "faq"},
    "sample-016": {"business_domain": "technical"},
    "sample-017": {"business_domain": "product"},
    "sample-018": {"business_domain": "finance"},
    "sample-019": {"business_domain": "policy"},
    "sample-020": {"business_domain": "customer_service"},
    "sample-021": {"business_domain": "product"},
    "sample-022": {"business_domain": "operations"},
    "sample-023": {"business_domain": "hr"},
    "sample-024": {"business_domain": "technical"},
}


def reset_data() -> None:
    for path in [RESULTS_DIR / "classification_eval.sqlite", RESULTS_DIR / "classification_eval_vectors.json"]:
        path.unlink(missing_ok=True)
    chroma_path = ROOT / "data" / "chroma"
    if chroma_path.exists():
        shutil.rmtree(chroma_path)


def main() -> None:
    if "--fallback" in sys.argv:
        os.environ["LLM_API_KEY"] = ""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["KB_DB_PATH"] = str(RESULTS_DIR / "classification_eval.sqlite")
    os.environ["KB_VECTOR_PATH"] = str(RESULTS_DIR / "classification_eval_vectors.json")
    reset_data()
    manager = KnowledgeManager()
    samples = json.loads((ROOT / "data" / "samples" / "sample_documents.json").read_text(encoding="utf-8"))

    rows = []
    domain_correct = 0
    type_checked = 0
    type_correct = 0
    for item in samples:
        result = manager.addKnowledge(item["text"], metadata={"source_id": item["id"]})
        metadata = result["metadata"]
        expected = EXPECTED[item["id"]]
        domain_hit = metadata["business_domain"] == expected["business_domain"]
        domain_correct += int(domain_hit)

        type_hit = None
        if "knowledge_type" in expected:
            type_checked += 1
            type_hit = metadata["knowledge_type"] == expected["knowledge_type"]
            type_correct += int(type_hit)

        rows.append(
            {
                "source_id": item["id"],
                "expected_domain": expected["business_domain"],
                "actual_domain": metadata["business_domain"],
                "domain_hit": domain_hit,
                "expected_type": expected.get("knowledge_type"),
                "actual_type": metadata["knowledge_type"],
                "type_hit": type_hit,
                "confidence": metadata["confidence"],
                "needs_review": metadata["needs_review"],
            }
        )

    report = {
        "documents": len(samples),
        "mode": "fallback" if not manager.llm.enabled else "llm_api",
        "domain_accuracy": round(domain_correct / len(samples), 3),
        "type_accuracy_on_labeled": round(type_correct / type_checked, 3) if type_checked else None,
        "rows": rows,
    }
    (RESULTS_DIR / "classification_eval.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manager.metrics.export_json(str(RESULTS_DIR / "classification_metrics.json"))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
