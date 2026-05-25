import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "data" / "eval_results"

QUESTIONS = [
    "大额纸质专票多久寄出？",
    "API 返回 401 应该怎么处理？",
    "合同到期前什么时候提醒客户经理？",
]


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "description": "Fill direct_llm_answer and rag_answer after running the same questions with and without retrieved context.",
        "questions": [
            {
                "question": question,
                "direct_llm_answer": "",
                "rag_answer": "",
                "expected_internal_fact": "",
                "direct_llm_score": None,
                "rag_score": None,
                "notes": "",
            }
            for question in QUESTIONS
        ],
    }
    (RESULTS_DIR / "rag_comparison_template.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
