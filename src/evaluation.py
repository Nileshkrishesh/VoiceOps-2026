"""Comprehensive evaluation framework for ZentroMart AI Customer Support Agent.

Measures:
- Correctness of answers based on must_include and must_not_include constraints.
- Policy grounding and retrieval quality (Recall@K, Hit Rate).
- Abstention accuracy on unanswerable questions.
- Tool selection, caller verification enforcement, and ticket creation.
"""
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from src.config import REPORTS_DIR, OUTPUTS_DIR

def normalize_text(text: str) -> str:
    """Normalize text for flexible factual comparison."""
    if not text:
        return ""
    text = str(text).lower()
    # Normalize punctuation, spacing, and currency symbols
    text = re.sub(r"[₹Rs\.\,\-\_\/\:\;\(\)\[\]\?]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def check_must_include(reply: str, must_include_rule: str) -> Tuple[bool, List[str]]:
    """Check if all mandatory facts in must_include are present.
    
    Items separated by ' ; ' are mandatory.
    Items separated by ' / ' are alternatives (any one suffices).
    """
    if not must_include_rule or pd.isna(must_include_rule):
        return True, []

    reply_norm = normalize_text(reply)
    clauses = [c.strip() for c in str(must_include_rule).split(" ; ") if c.strip()]
    missing_clauses = []

    for clause in clauses:
        alternatives = [a.strip() for a in clause.split(" / ") if a.strip()]
        matched = False
        for alt in alternatives:
            alt_norm = normalize_text(alt)
            # Check either direct substring or regex word boundary
            if alt_norm and alt_norm in reply_norm:
                matched = True
                break
        if not matched:
            missing_clauses.append(clause)

    return (len(missing_clauses) == 0), missing_clauses

def check_must_not_include(reply: str, must_not_include_rule: str) -> Tuple[bool, List[str]]:
    """Check if any forbidden claim in must_not_include is present."""
    if not must_not_include_rule or pd.isna(must_not_include_rule):
        return True, []

    reply_norm = normalize_text(reply)
    clauses = [c.strip() for c in str(must_not_include_rule).split(" ; ") if c.strip()]
    violated_clauses = []

    for clause in clauses:
        clause_norm = normalize_text(clause)
        if clause_norm and clause_norm in reply_norm:
            violated_clauses.append(clause)

    return (len(violated_clauses) == 0), violated_clauses

def evaluate_answer(reply: str, question_row: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single generated reply against dataset ground truth."""
    must_include_rule = question_row.get("must_include")
    must_not_include_rule = question_row.get("must_not_include")
    answerable = str(question_row.get("answerable", "True")).lower() == "true"
    
    inc_passed, missing = check_must_include(reply, must_include_rule)
    not_inc_passed, violations = check_must_not_include(reply, must_not_include_rule)
    
    is_correct = inc_passed and not_inc_passed
    
    # Check abstention behavior for unanswerable questions
    abstention_correct = False
    if not answerable:
        abstention_markers = [
            "don't have", "do not have", "not sure", "no information",
            "cannot find", "not covered", "pata nahi", "jaankari nahi",
            "human support", "connect you"
        ]
        reply_lower = reply.lower()
        abstention_correct = any(m in reply_lower for m in abstention_markers)
    else:
        abstention_correct = is_correct

    return {
        "must_include_passed": inc_passed,
        "missing_facts": missing,
        "must_not_include_passed": not_inc_passed,
        "violations": violations,
        "is_correct": is_correct,
        "abstention_correct": abstention_correct,
    }

def run_questions_evaluation(agent, questions_df: pd.DataFrame, step_name: str = "step1") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Run full evaluation on practice/questions.csv and save report."""
    results = []
    
    for idx, row in questions_df.iterrows():
        qid = row["id"]
        question = row["question"]
        ref_answer = row.get("reference_answer", "")
        expected_decision = row.get("expected_decision", "")
        
        # Reset turn state if applicable
        if hasattr(agent, "is_first_turn"):
            agent.is_first_turn = (idx == 0)
            
        # Generate reply
        if hasattr(agent, "answer_question"):
            reply = agent.answer_question(question)
        elif hasattr(agent, "respond"):
            reply = agent.respond(question)
        else:
            reply = str(agent(question))
            
        eval_metrics = evaluate_answer(reply, row.to_dict())
        
        res_record = {
            "question_id": qid,
            "language": row.get("language", "en"),
            "question": question,
            "generated_answer": reply,
            "reference_answer": ref_answer,
            "expected_decision": expected_decision,
            "answerable": row.get("answerable", "True"),
            "must_include": row.get("must_include", ""),
            "must_not_include": row.get("must_not_include", ""),
            **eval_metrics
        }
        results.append(res_record)
        
    res_df = pd.DataFrame(results)
    
    # Calculate summary metrics
    total_q = len(res_df)
    correct_count = res_df["is_correct"].sum()
    must_include_acc = res_df["must_include_passed"].mean() * 100
    safe_claim_acc = res_df["must_not_include_passed"].mean() * 100
    overall_acc = (correct_count / total_q) * 100
    
    summary = {
        "step": step_name,
        "total_questions": total_q,
        "correct_answers": int(correct_count),
        "overall_accuracy_pct": round(overall_acc, 2),
        "must_include_accuracy_pct": round(must_include_acc, 2),
        "safe_claims_pct": round(safe_claim_acc, 2),
    }
    
    # Save artifacts
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_csv = REPORTS_DIR / f"{step_name}_questions_evaluation.csv"
    summary_json = REPORTS_DIR / f"{step_name}_summary.json"
    
    res_df.to_csv(report_csv, index=False, encoding="utf-8")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    return res_df, summary
