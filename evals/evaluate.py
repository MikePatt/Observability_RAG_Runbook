"""obs-rag Ragas Evaluation."""

import json
import os
from pathlib import Path

import mlflow
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from src.pipeline import initialize_pipeline, query
from src.settings import get_settings

EVAL_QUESTIONS = [
    {
        "question": "What are the first steps when the forecasting service triggers an OOM alert?",
        "ground_truth": "Check memory utilization dashboard, identify the offending pod, restart the pod if safe, and escalate to on-call lead if OOM persists across multiple pods.",
    },
    {
        "question": "How do I reduce alert fatigue from the anomaly detection pipeline?",
        "ground_truth": "Tune the Prophet confidence interval threshold, apply signal smoothing using rolling averages, and adjust the alert suppression window to at least 5 minutes for non-critical services.",
    },
    {
        "question": "What is the rollback procedure for a bad model deployment?",
        "ground_truth": "Identify the previous stable model version in Azure ML, redeploy the versioned artifact to the REST endpoint, and verify the health check endpoint returns 200 before closing the incident.",
    },
]


def run_evaluation(log_to_mlflow: bool = True) -> dict:
    settings = get_settings()
    chain = initialize_pipeline(
        model=settings.openai_model,
        embedding_model=settings.embedding_model,
        persist_path=settings.persist_path,
        force_rebuild=settings.force_rebuild,
        top_k=settings.top_k,
    )

    questions, answers, contexts, ground_truths = [], [], [], []

    for item in EVAL_QUESTIONS:
        result = query(chain, item["question"])
        questions.append(item["question"])
        answers.append(result["answer"])
        contexts.append(result["contexts"])
        ground_truths.append(item["ground_truth"])

    eval_dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
    )

    results = evaluate(eval_dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])

    scores = {
        "faithfulness": round(float(results["faithfulness"]), 4),
        "answer_relevancy": round(float(results["answer_relevancy"]), 4),
        "context_precision": round(float(results["context_precision"]), 4),
        "context_recall": round(float(results["context_recall"]), 4),
    }

    output_path = Path("evals/results.json")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps({"model": settings.openai_model, "scores": scores}, indent=2), encoding="utf-8")

    if log_to_mlflow:
        with mlflow.start_run(run_name=f"ragas-eval-{settings.openai_model}"):
            mlflow.log_param("model", settings.openai_model)
            mlflow.log_metrics(scores)
            mlflow.log_artifact(str(output_path))

    return scores


if __name__ == "__main__":
    run_evaluation(log_to_mlflow=os.getenv("LOG_TO_MLFLOW", "true").lower() == "true")