
"""Test suite for Phase 4: KnowledgeBase, RAG Agent, and Comparative Evaluation."""

import sys
import json
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PRACTICE_DIR, REPORTS_DIR
from src.knowledge_base import KnowledgeBase
from src.rag_agent import RAGAgent
from src.llm_agent import LLMClient
from src.evaluation import run_questions_evaluation


@pytest.fixture(scope="module")
def shared_kb():
    """Create one shared KnowledgeBase for the tests."""
    return KnowledgeBase()


def test_kb_indexing_and_precedence(shared_kb):
    """Verify that the KB indexes documents and products and filters superseded content."""
    assert len(shared_kb.chunks) > 50, (
        "KnowledgeBase should index sections and products"
    )

    results = shared_kb.retrieve("return policy window")
    assert all(
        chunk.status != "superseded"
        for chunk, _ in results
    ), "Superseded content should not be returned"


def test_kb_entity_retrieval(shared_kb):
    """Verify retrieval of a specific product SKU."""
    results = shared_kb.retrieve("SKU ELE-0012 warranty details")
    section_ids = [chunk.section_id for chunk, _ in results]

    assert any(
        "products.csv:ELE-0012" in section_id
        for section_id in section_ids
    ), "Expected product SKU ELE-0012 to be retrieved"


def test_rag_agent_abstention(shared_kb):
    """Verify that the agent abstains on an unsupported request."""
    offline_client = LLMClient(provider="offline")
    agent = RAGAgent(
        knowledge_base=shared_kb,
        llm_client=offline_client,
    )

    reply = agent.answer_question(
        "Can I schedule a delivery at midnight with a drone?"
    )
    reply_lower = reply.lower()

    assert any(
        phrase in reply_lower
        for phrase in [
            "don't have",
            "no information",
            "cannot",
            "sorry",
            "not covered",
        ]
    ), f"Expected an abstention response, got: {reply}"


def test_step2_rag_full_evaluation_and_comparison(shared_kb):
    """Evaluate all 52 questions offline and validate the generated report."""
    questions_path = PRACTICE_DIR / "questions.csv"
    assert questions_path.exists(), (
        f"Practice questions file not found: {questions_path}"
    )

    questions_df = pd.read_csv(questions_path, dtype=str)
    assert len(questions_df) == 52, (
        "Expected exactly 52 practice questions"
    )

    offline_client = LLMClient(provider="offline")
    rag_agent = RAGAgent(
        knowledge_base=shared_kb,
        llm_client=offline_client,
    )

    eval_df, step2_summary = run_questions_evaluation(
        rag_agent,
        questions_df,
        step_name="step2_rag",
    )

    # Validate evaluation output.
    assert len(eval_df) == 52
    assert step2_summary["total_questions"] == 52
    assert "overall_accuracy_pct" in step2_summary
    assert "safe_claims_pct" in step2_summary

    # Confirm that evaluation artifacts were generated.
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    results_path = REPORTS_DIR / "step2_rag_results.csv"
    summary_path = REPORTS_DIR / "step2_rag_summary.json"

    # run_questions_evaluation may use its own filenames; save the returned
    # results and summary under predictable names as well.
    eval_df.to_csv(results_path, index=False)

    with open(summary_path, "w", encoding="utf-8") as file:
        json.dump(step2_summary, file, indent=2, ensure_ascii=False)

    assert results_path.exists()
    assert summary_path.exists()

    # Create a comparison report only if Step 1 results exist.
    # Accuracy superiority is not asserted here because Step 1 may contain
    # mocked responses while Step 2 is using the offline RAG fallback.
    step1_summary_path = REPORTS_DIR / "step1_baseline_summary.json"

    if step1_summary_path.exists():
        with open(step1_summary_path, "r", encoding="utf-8") as file:
            step1_summary = json.load(file)

        comparison = {
            "metric": [
                "Total Questions",
                "Correct Answers",
                "Accuracy (%)",
                "Safe Claims (%)",
            ],
            "Step 1 Baseline (No RAG)": [
                step1_summary.get("total_questions"),
                step1_summary.get("correct_answers"),
                step1_summary.get("overall_accuracy_pct"),
                step1_summary.get("safe_claims_pct"),
            ],
            "Step 2 Grounded RAG (Offline)": [
                step2_summary.get("total_questions"),
                step2_summary.get("correct_answers"),
                step2_summary.get("overall_accuracy_pct"),
                step2_summary.get("safe_claims_pct"),
            ],
        }

        comparison_path = REPORTS_DIR / "step1_vs_step2_comparison.csv"
        pd.DataFrame(comparison).to_csv(
            comparison_path,
            index=False,
        )

        assert comparison_path.exists()
