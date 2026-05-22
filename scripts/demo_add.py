import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_base import KnowledgeManager


def main() -> None:
    manager = KnowledgeManager()
    sample_path = ROOT / "data" / "samples" / "sample_documents.json"
    samples = json.loads(sample_path.read_text(encoding="utf-8"))
    for item in samples:
        result = manager.addKnowledge(item["text"], metadata={"source_id": item["id"]})
        metadata = result["metadata"]
        print(
            f"added {result['id']} domain={metadata['business_domain']} "
            f"type={metadata['knowledge_type']} confidence={metadata['confidence']}"
        )
    print(f"total active documents: {len(manager.list_knowledge())}")


if __name__ == "__main__":
    main()
