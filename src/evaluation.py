"""Comprehensive evaluation framework for ZentroMart AI Customer Support Agent.

Measures:
- Correctness of answers based on must_include and must_not_include constraints.
- Policy grounding and retrieval quality (Recall@K, Hit Rate).
- Abstention accuracy on unanswerable questions.
- Tool selection, caller verification enforcement, and ticket creation.
"""
import re
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from src.config import REPORTS_DIR, OUTPUTS_DIR

def safe_print(*args, **kwargs):
    """Print safely to stdout without crashing on unencodable characters (e.g. cp1252 console)."""
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    sanitized = []
    for a in args:
        if isinstance(a, str):
            sanitized.append(a.encode(enc, errors="replace").decode(enc))
        else:
            sanitized.append(str(a).encode(enc, errors="replace").decode(enc))
    try:
        print(*sanitized, **kwargs)
    except Exception:
        pass

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

GENERIC_ABSTENTION_PATTERNS = [
    r"don't have enough information",
    r"do not have enough information",
    r"not have enough information in our official documents",
    r"sorry,?\s+i don't have enough information",
    r"sorry,?\s+i do not have enough information",
    r"connect you with a support executive",
    r"connect you with our support team",
    r"connect you to a colleague",
    r"connect you to a human",
    r"human support",
    r"support executive",
    r"जानकारी नहीं है",
    r"jaankari nahi hai",
    r"pata nahi",
    r"सहयोगी से जोड़",
]

def check_clarification(reply: str, question_row: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate that when expected_decision='clarify', the reply actually asks a clarifying
    question relevant to the missing information, rather than generically abstaining or handing off.
    """
    if not reply or not str(reply).strip():
        return False, ["Empty response; expected a clarifying question."]

    reply_str = str(reply).strip()
    reply_lower = reply_str.lower()
    missing_issues = []

    # 1. Reject generic insufficient-information statement or canned handoff
    has_generic_abstention = any(
        re.search(pat, reply_lower) for pat in GENERIC_ABSTENTION_PATTERNS
    )
    if has_generic_abstention:
        if any(term in reply_lower for term in [
            "don't have enough information in our official documents",
            "do not have enough information in our official documents",
            "would you like me to connect you with a support executive",
            "connect you with a support executive",
        ]):
            missing_issues.append("Generic insufficient-information or handoff response is not a valid clarification")

    # 2. Check for question or clarification request indicators
    has_question_mark = "?" in reply_str
    clarify_request_terms = [
        "which", "what", "could you", "can you", "please tell", "please share",
        "please specify", "please clarify", "please provide", "let me know",
        "how did you", "how was", "kaun sa", "kaun si", "kaunsa", "kaunsi",
        "bataiye", "batayein", "kripya", "kripya bata",
        "कौन सा", "कौन सी", "कौनसा", "कौनसी", "क्या आप", "कृपया बताएं", "कृपया बता",
        "बताइए", "बताएं", "पूछें", "दीजिए", "शेयर करें"
    ]
    has_clarify_indicator = has_question_mark or any(term in reply_lower for term in clarify_request_terms)

    if not has_clarify_indicator:
        missing_issues.append("Response must ask a clarifying question or request missing information")

    # 3. Check relevance to the missing information described in reference_answer
    ref_answer = str(question_row.get("reference_answer", "")).lower()

    # Product/item domain (e.g. PQ0018: "कौन सा सामान है, यह पूछें")
    product_domain_keywords = [
        "सामान", "आइटम", "प्रोडक्ट", "चीज़", "वस्तु", "product", "item", "category", "goods", "merchandise", "cheez", "saman"
    ]
    ref_mentions_product = any(k in ref_answer for k in ["सामान", "product", "item", "category", "goods", "cheez", "saman"])

    # Payment/refund method domain (e.g. PQ0051: "Ask how the customer paid (or for the order ID)")
    payment_domain_keywords = [
        "paid", "pay", "payment", "method", "mode", "order id", "order", "upi", "card", "bank", "net banking", "wallet",
        "भुगतान", "पेमेंट", "ऑर्डर आईडी", "ऑर्डर", "पे"
    ]
    ref_mentions_payment = any(k in ref_answer for k in ["paid", "pay", "payment", "method", "mode", "order id", "भुगतान", "पेमेंट"])

    if ref_mentions_product:
        if not any(k in reply_lower for k in product_domain_keywords):
            missing_issues.append("Clarification must ask which product/item/category the customer is inquiring about")
    elif ref_mentions_payment:
        if not any(k in reply_lower for k in payment_domain_keywords):
            missing_issues.append("Clarification must ask for payment method or Order ID")
    else:
        stopwords = {
            "ask", "the", "customer", "because", "is", "a", "an", "or", "for", "to", "it", "this", "that", "of",
            "in", "how", "what", "which", "when", "where", "who", "why", "depends", "on", "timeline", "window",
            "यह", "वह", "पूछें", "करें", "है", "होगा", "की", "का", "के", "में", "से"
        }
        ref_tokens = [w for w in re.findall(r"\w+", ref_answer) if w not in stopwords and len(w) > 2]
        if ref_tokens and not any(t in reply_lower for t in ref_tokens):
            missing_issues.append(f"Clarification must be relevant to expected missing info: {ref_tokens[:3]}")

    passed = (len(missing_issues) == 0)
    return passed, missing_issues

def evaluate_answer(reply: str, question_row: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single generated reply against dataset ground truth."""
    must_include_rule = question_row.get("must_include")
    must_not_include_rule = question_row.get("must_not_include")
    expected_decision = str(question_row.get("expected_decision", "answer")).strip().lower()
    answerable = str(question_row.get("answerable", "True")).strip().lower() == "true"
    
    inc_passed, missing = check_must_include(reply, must_include_rule)
    not_inc_passed, violations = check_must_not_include(reply, must_not_include_rule)
    
    is_correct = inc_passed and not_inc_passed

    # Decision-specific evaluation
    if expected_decision == "clarify":
        clarify_passed, clarify_issues = check_clarification(reply, question_row)
        if not clarify_passed:
            is_correct = False
            missing.extend(clarify_issues)
        # When clarification is expected, a generic abstention is NOT correct abstention
        abstention_correct = clarify_passed
    elif expected_decision == "refuse":
        # For refusal cases (e.g. privacy of other customers), must not disclose forbidden info and must refuse
        refusal_markers = [
            "cannot", "can't", "not allowed", "privacy", "policy",
            "refuse", "not share", "don't share", "do not share",
            "नहीं", "साझा नहीं", "निजी", "सॉरी", "sorry"
        ]
        reply_lower = str(reply).lower()
        has_refusal = any(m in reply_lower for m in refusal_markers)
        if not has_refusal and not inc_passed:
            is_correct = False
            missing.append("Expected refusal to share restricted/private information")
        abstention_correct = is_correct
    elif not answerable:
        # Genuinely unanswerable questions (answerable == False)
        abstention_markers = [
            "don't have", "do not have", "not sure", "no information",
            "cannot find", "can't find", "not covered", "pata nahi", "jaankari nahi",
            "जानकारी नहीं", "human support", "connect you", "support executive"
        ]
        reply_lower = str(reply).lower()
        abstention_correct = any(m in reply_lower for m in abstention_markers)
        if not abstention_correct:
            is_correct = False
    else:
        # Standard answerable question: if it generically abstains instead of answering, that's incorrect
        reply_lower = str(reply).lower()
        is_generic_abstain = any(re.search(pat, reply_lower) for pat in GENERIC_ABSTENTION_PATTERNS)
        if is_generic_abstain:
            abstention_correct = False
            is_correct = False
            missing.append("Generic abstention given for answerable policy question")
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

def run_questions_evaluation(
    agent,
    questions_df: pd.DataFrame,
    step_name: str = "step1",
    pacing_delay: float = 4.2,
    resume: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Run evaluation on practice/questions.csv with rate-limiting, resume, and checkpointing."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_csv = REPORTS_DIR / f"{step_name}_questions_evaluation.csv"
    summary_json = REPORTS_DIR / f"{step_name}_summary.json"

    existing_results: Dict[str, Dict[str, Any]] = {}
    if resume and report_csv.exists():
        try:
            prev_df = pd.read_csv(report_csv, dtype=str)
            for _, r in prev_df.iterrows():
                qid = str(r.get("question_id", ""))
                # Only keep prior results if they succeeded
                if qid and str(r.get("is_correct", "")).lower() == "true":
                    existing_results[qid] = r.to_dict()
            if existing_results:
                safe_print(f"   [RESUME] Found {len(existing_results)} previously passed questions in checkpoint.")
        except Exception:
            existing_results = {}

    results = []
    total_q = len(questions_df)
    is_live_agent = hasattr(agent, "client") and getattr(agent.client, "is_live", lambda: False)()

    for idx, row in questions_df.iterrows():
        qid = str(row["id"])
        question = row["question"]
        ref_answer = row.get("reference_answer", "")
        expected_decision = row.get("expected_decision", "")

        # Check if already passed in checkpoint
        if qid in existing_results:
            results.append(existing_results[qid])
            safe_print(f"[{idx+1}/{total_q}] {qid}: [SKIPPED] (already passed in checkpoint)")
            continue

        # Rate-limit pacing when live API is active
        if is_live_agent and pacing_delay > 0 and len(results) > 0:
            time.sleep(pacing_delay)

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
        is_correct = eval_metrics["is_correct"]

        if hasattr(agent, "last_generation_source") and agent.last_generation_source != "unknown":
            source = agent.last_generation_source
        elif getattr(agent, "last_abstained", False):
            source = "abstention"
        elif is_live_agent:
            source = "live_llm"
        else:
            source = "grounded_synthesis"

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
            "generation_source": source,
            **eval_metrics
        }
        results.append(res_record)

        status_icon = "[PASSED]" if is_correct else "[FAILED]"
        safe_print(f"[{idx+1}/{total_q}] {qid}: {status_icon} | {question[:45]}...")
        if not is_correct and eval_metrics.get("missing_facts"):
            safe_print(f"        Missing: {eval_metrics['missing_facts']}")

        # Incremental checkpoint save to disk
        try:
            pd.DataFrame(results).to_csv(report_csv, index=False, encoding="utf-8")
        except Exception:
            pass

    res_df = pd.DataFrame(results)

    # Calculate summary metrics
    correct_count = (res_df["is_correct"].astype(str).str.lower() == "true").sum()
    must_include_acc = (res_df["must_include_passed"].astype(str).str.lower() == "true").mean() * 100
    safe_claim_acc = (res_df["must_not_include_passed"].astype(str).str.lower() == "true").mean() * 100
    overall_acc = (correct_count / total_q) * 100

    summary = {
        "step": step_name,
        "total_questions": total_q,
        "correct_answers": int(correct_count),
        "overall_accuracy_pct": round(overall_acc, 2),
        "must_include_accuracy_pct": round(must_include_acc, 2),
        "safe_claims_pct": round(safe_claim_acc, 2),
    }

    # Final artifacts flush
    res_df.to_csv(report_csv, index=False, encoding="utf-8")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return res_df, summary
