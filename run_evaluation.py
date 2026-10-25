"""Complete evaluation runner for VoiceOps 2026 project.

Runs Step 1 baseline, Step 2 RAG, and conversation evaluation.
Generates reports comparing performance.
"""
import sys
import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PRACTICE_DIR, REPORTS_DIR
from src.llm_agent import BasicLLMAgent
from src.rag_agent import RAGAgent
from src.knowledge_base import KnowledgeBase
from src.conversation import ConversationSession
from src.evaluation import run_questions_evaluation, evaluate_answer

def run_step1_evaluation():
    """Run Step 1: Baseline LLM without RAG."""
    print("\n" + "="*70)
    print("STEP 1: Baseline LLM Evaluation (No RAG)")
    print("="*70)
    
    questions_csv = PRACTICE_DIR / "questions.csv"
    if not questions_csv.exists():
        print(f"❌ ERROR: {questions_csv} not found")
        return None
    
    questions_df = pd.read_csv(questions_csv, dtype=str)
    print(f"Loaded {len(questions_df)} questions from {questions_csv}")
    
    agent = BasicLLMAgent()
    results_df, summary = run_questions_evaluation(
        agent=agent,
        questions_df=questions_df,
        step_name="step1_baseline"
    )
    
    print(f"\n✅ Step 1 Results:")
    print(f"   Total Questions: {summary['total_questions']}")
    print(f"   Correct Answers: {summary['correct_answers']}")
    print(f"   Overall Accuracy: {summary['overall_accuracy_pct']}%")
    print(f"   Safe Claims: {summary['safe_claims_pct']}%")
    
    return summary

def run_step2_evaluation():
    """Run Step 2: RAG-grounded agent."""
    print("\n" + "="*70)
    print("STEP 2: RAG-Grounded Agent Evaluation")
    print("="*70)
    
    questions_csv = PRACTICE_DIR / "questions.csv"
    if not questions_csv.exists():
        print(f"❌ ERROR: {questions_csv} not found")
        return None
    
    questions_df = pd.read_csv(questions_csv, dtype=str)
    print(f"Loaded {len(questions_df)} questions")
    
    print("Initializing knowledge base...")
    kb = KnowledgeBase()
    print(f"   Indexed {len(kb.chunks)} chunks")
    
    agent = RAGAgent(knowledge_base=kb)
    results_df, summary = run_questions_evaluation(
        agent=agent,
        questions_df=questions_df,
        step_name="step2_rag"
    )
    
    print(f"\n✅ Step 2 Results:")
    print(f"   Total Questions: {summary['total_questions']}")
    print(f"   Correct Answers: {summary['correct_answers']}")
    print(f"   Overall Accuracy: {summary['overall_accuracy_pct']}%")
    print(f"   Safe Claims: {summary['safe_claims_pct']}%")
    
    return summary

def run_conversation_evaluation():
    """Run Step 3: Multi-turn conversation evaluation."""
    print("\n" + "="*70)
    print("STEP 3: Conversation Evaluation")
    print("="*70)
    
    conversations_csv = PRACTICE_DIR / "conversations.csv"
    if not conversations_csv.exists():
        print(f"❌ ERROR: {conversations_csv} not found")
        return None
    
    conv_df = pd.read_csv(conversations_csv, dtype=str)
    print(f"Loaded {len(conv_df)} turns across conversations")
    
    kb = KnowledgeBase()
    sessions = {}
    results = []
    
    for idx, row in conv_df.iterrows():
        conv_id = row["conversation_id"]
        turn = int(row["turn"])
        message = row["customer_message"]
        expected_decision = row.get("expected_decision", "")
        expected_tools = row.get("expected_tool_calls", "")
        must_include = row.get("must_include", "")
        must_not_include = row.get("must_not_include", "")
        
        # Get or create session
        if conv_id not in sessions:
            sessions[conv_id] = ConversationSession(conv_id, kb=kb)
        session = sessions[conv_id]
        
        # Process turn
        result = session.process_turn(message)
        reply = result["reply"]
        decision = result["decision"]
        tool_calls = result["tool_calls"]
        
        # Evaluate
        eval_result = evaluate_answer(reply, {
            "must_include": must_include,
            "must_not_include": must_not_include,
            "answerable": "True"
        })
        
        decision_match = (decision == expected_decision) if expected_decision else True
        
        result_record = {
            "conversation_id": conv_id,
            "turn": turn,
            "message": message,
            "reply": reply,
            "decision": decision,
            "expected_decision": expected_decision,
            "decision_correct": decision_match,
            "tool_calls": str(tool_calls),
            "expected_tools": expected_tools,
            **eval_result
        }
        results.append(result_record)
        
        status = "✅" if eval_result["is_correct"] and decision_match else "❌"
        print(f"{status} {conv_id} T{turn}: {decision} | Correct: {eval_result['is_correct']}")
    
    results_df = pd.DataFrame(results)
    
    # Calculate summary
    total_turns = len(results_df)
    correct_turns = results_df["is_correct"].sum()
    decision_correct = results_df["decision_correct"].sum()
    
    summary = {
        "total_turns": total_turns,
        "correct_answers": int(correct_turns),
        "accuracy_pct": round((correct_turns / total_turns) * 100, 2),
        "decision_accuracy_pct": round((decision_correct / total_turns) * 100, 2),
        "unique_conversations": len(sessions)
    }
    
    # Save report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_csv = REPORTS_DIR / "conversations_evaluation.csv"
    summary_json = REPORTS_DIR / "conversations_summary.json"
    
    results_df.to_csv(report_csv, index=False, encoding="utf-8")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ Conversation Results:")
    print(f"   Total Turns: {summary['total_turns']}")
    print(f"   Correct Answers: {summary['correct_answers']}")
    print(f"   Overall Accuracy: {summary['accuracy_pct']}%")
    print(f"   Decision Accuracy: {summary['decision_accuracy_pct']}%")
    
    return summary

def main():
    print("="*70)
    print("VoiceOps 2026: Complete Evaluation Runner")
    print("="*70)
    
    step1_summary = run_step1_evaluation()
    step2_summary = run_step2_evaluation()
    conv_summary = run_conversation_evaluation()
    
    print("\n" + "="*70)
    print("FINAL COMPARISON")
    print("="*70)
    
    if step1_summary and step2_summary:
        print(f"\nStep 1 (Baseline): {step1_summary['correct_answers']}/{step1_summary['total_questions']} = {step1_summary['overall_accuracy_pct']}%")
        print(f"Step 2 (RAG):      {step2_summary['correct_answers']}/{step2_summary['total_questions']} = {step2_summary['overall_accuracy_pct']}%")
        
        improvement = step2_summary['overall_accuracy_pct'] - step1_summary['overall_accuracy_pct']
        print(f"\n📊 RAG Improvement: +{improvement:.2f}% absolute")
        
        if step1_summary['correct_answers'] > 0:
            relative_gain = ((step2_summary['correct_answers'] - step1_summary['correct_answers']) / step1_summary['correct_answers']) * 100
            print(f"   Relative Gain: +{relative_gain:.1f}%")
    
    if conv_summary:
        print(f"\nConversation: {conv_summary['correct_answers']}/{conv_summary['total_turns']} = {conv_summary['accuracy_pct']}%")
    
    print("\n✅ All evaluations complete. Reports saved to:", REPORTS_DIR)
    print("="*70)

if __name__ == "__main__":
    main()
