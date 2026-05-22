import json
import os
import shutil
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_base import KnowledgeManager


RESULTS_DIR = ROOT / "data" / "eval_results"
QUERY = "API 返回 401 应该怎么处理？"


def reset_data() -> None:
    for path in [ROOT / "data" / "kb.sqlite", ROOT / "data" / "vectors.json"]:
        path.unlink(missing_ok=True)
    chroma_path = ROOT / "data" / "chroma"
    if chroma_path.exists():
        shutil.rmtree(chroma_path)


def parse_copies() -> int:
    if "--copies" not in sys.argv:
        return 20
    index = sys.argv.index("--copies")
    return int(sys.argv[index + 1])


def main() -> None:
    # Benchmarks can create hundreds of documents; default to fallback to avoid unexpected API usage.
    if "--use-api" not in sys.argv:
        os.environ["LLM_API_KEY"] = ""

    copies = parse_copies()
    reset_data()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manager = KnowledgeManager()
    samples = json.loads((ROOT / "data" / "samples" / "sample_documents.json").read_text(encoding="utf-8"))

    started = perf_counter()
    total_docs = 0
    for copy_index in range(copies):
        for item in samples:
            manager.addKnowledge(
                f"{item['text']}\n批次编号：{copy_index + 1}",
                metadata={"source_id": f"{item['id']}-copy-{copy_index + 1}"},
            )
            total_docs += 1
    ingest_ms = round((perf_counter() - started) * 1000, 2)

    query_results = []
    for _ in range(10):
        result = manager.query(QUERY, top_k=5)
        query_results.append(result["elapsed_ms"])

    report = {
        "mode": "fallback" if not manager.llm.enabled else "llm_api",
        "source_documents": len(samples),
        "copies": copies,
        "total_documents": total_docs,
        "ingest_elapsed_ms": ingest_ms,
        "avg_ingest_ms_per_doc": round(ingest_ms / total_docs, 3),
        "query_runs": len(query_results),
        "avg_query_elapsed_ms": round(sum(query_results) / len(query_results), 3),
        "max_query_elapsed_ms": max(query_results),
        "prompt_token_limit": manager.settings.token_limit,
    }
    (RESULTS_DIR / "benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manager.metrics.export_json(str(RESULTS_DIR / "benchmark_metrics.json"))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
