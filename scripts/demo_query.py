import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_base import KnowledgeManager


def main() -> None:
    question = "客户付款后想申请大额纸质专票，一般需要多久？"
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])

    manager = KnowledgeManager()
    result = manager.query(question, top_k=5)
    print("question:", result["question"])
    print("rewrite:", result["debug"]["rewrite"])
    print("used_tokens_estimate:", result["used_tokens_estimate"])
    print("\ntop hits:")
    for index, hit in enumerate(result["hits"], start=1):
        metadata = hit["metadata"]
        print(
            f"{index}. score={hit['score']} domain={metadata['business_domain']} "
            f"type={metadata['knowledge_type']} source={metadata.get('source_id')}"
        )
        print("   ", hit["text"][:120])
    print("\nassembled prompt:\n")
    print(result["prompt"])


if __name__ == "__main__":
    main()
