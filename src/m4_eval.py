from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json, math
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _clip_fp(v: float, eps: float = 1e-9) -> float:
    """Cosine similarity có thể ra 1.0000000000000002 do sai số float → kẹp về [0,1].
    Chỉ sửa sai số làm tròn; giá trị lệch thật (hoặc NaN) giữ nguyên để bị phát hiện."""
    if -eps <= v < 0 or 1 < v <= 1 + eps:
        return min(max(v, 0.0), 1.0)
    return v


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation. Errors propagate (no silent empty result); NaN rows are re-run."""
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from datasets import Dataset

    from ragas.run_config import RunConfig
    from langchain_openai import ChatOpenAI
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, EMBEDDING_MODEL

    # Judge LLM = OpenAI LLM_MODEL; embeddings chạy local (bge-m3).
    # strictness=1: 1 câu hỏi sinh ngược/answer thay vì 3 (tiết kiệm chi phí).
    answer_relevancy.strictness = 1
    llm = ChatOpenAI(model=LLM_MODEL, api_key=LLM_API_KEY, base_url=LLM_BASE_URL, temperature=0)
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    def _run(idx: list[int]) -> list[dict]:
        dataset = Dataset.from_dict({"question": [questions[i] for i in idx],
                                     "answer": [answers[i] for i in idx],
                                     "contexts": [contexts[i] for i in idx],
                                     "ground_truth": [ground_truths[i] for i in idx]})
        df = evaluate(dataset,
                      metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                      llm=llm, embeddings=embeddings,
                      run_config=RunConfig(max_workers=4, max_retries=10, max_wait=60)).to_pandas()
        return [{m: _clip_fp(float(r[m])) for m in METRICS} for _, r in df.iterrows()]

    # Job lỗi (429, parse JSON) → NaN. Chấm lại riêng các câu đó thay vì giữ NaN hoặc gán điểm giả.
    scores: list[dict | None] = [None] * len(questions)
    pending = list(range(len(questions)))
    for attempt in range(3):
        for i, s in zip(pending, _run(pending)):
            if all(math.isfinite(v) for v in s.values()):
                scores[i] = s
        pending = [i for i, s in enumerate(scores) if s is None]
        if not pending:
            break
        print(f"  ⚠️  {len(pending)} câu ra NaN, chấm lại (lần {attempt + 2})...")
    if pending:
        raise RuntimeError(f"RAGAS vẫn ra NaN sau 3 lượt cho các index: {pending}")

    per_question = [EvalResult(question=q, answer=a, contexts=list(c), ground_truth=g, **s)
                    for q, a, c, g, s in zip(questions, answers, contexts, ground_truths, scores)]
    aggregate = {m: sum(s[m] for s in scores) / len(scores) for m in METRICS}
    return {**aggregate, "per_question": per_question,
            "metadata": {"evaluator_models": [LLM_MODEL, EMBEDDING_MODEL]}}


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template"),
    }
    rows = []
    for r in eval_results:
        scores = {m: getattr(r, m) for m in METRICS if not math.isnan(getattr(r, m))}
        if not scores:
            continue
        worst = min(scores, key=scores.get)
        diagnosis, fix = diagnostic_tree[worst]
        rows.append({"question": r.question, "answer": r.answer, "ground_truth": r.ground_truth,
                     "contexts_preview": [c[:120] for c in r.contexts],
                     "scores": {m: scores.get(m) for m in METRICS},  # None = RAGAS job lỗi
                     "avg_score": sum(scores.values()) / len(scores),
                     "worst_metric": worst, "score": scores[worst],
                     "diagnosis": diagnosis, "suggested_fix": fix})
    return sorted(rows, key=lambda x: x["avg_score"])[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
