
"""Test suite for Phase 5: Multi-turn Conversation Handling,
Caller Verification, and Tool Execution."""

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PRACTICE_DIR, REPORTS_DIR
from src.conversation import ConversationSession
from src.knowledge_base import KnowledgeBase


@pytest.fixture(scope="module")
def shared_kb():
    """Create a shared KnowledgeBase for the tests."""
    return KnowledgeBase()


def test_conversation_pc002_full_sequence(shared_kb):
    """Test the complete 4-turn workflow of conversation PC002."""
    session = ConversationSession(conversation_id="PC002", kb=shared_kb)

    # Turn 1: Greeting
    t1 = session.process_turn(
        "Hello, mujhe order ke baare mein help chahiye."
    )
    assert t1["decision"] == "clarify"
    assert any(
        phrase in t1["reply"].lower()
        for phrase in ["ai", "assistant", "एआई"]
    )
    assert (
        "8-digit" in t1["reply"]
        or "order id" in t1["reply"].lower()
    )

    # Turn 2: Order ID provided
    t2 = session.process_turn("Order number hai 8978 2837.")
    assert t2["decision"] == "clarify"
    assert "lookup_order(89782837)" in t2["tool_calls"]
    assert any(
        phrase in t2["reply"].lower()
        for phrase in ["last 4", "pincode", "verification"]
    )
    assert session.order_verified is False

    # Turn 3: Caller verification proof
    t3 = session.process_turn("Last four digits 4533 hain.")
    assert t3["decision"] == "answer"
    assert (
        "lookup_order(89782837, verification_value=REDACTED)"
        in t3["tool_calls"]
    )
    assert session.order_verified is True
    assert session.verified_order_data is not None

    # Turn 4: Damaged item / replacement approval request
    t4 = session.process_turn(
        "Maine Zentro Vista 43-inch 4K Smart TV damage report kiya tha. "
        "Abhi replacement approve kar do na?"
    )
    assert t4["decision"] == "escalate"
    assert "create_ticket()" in t4["tool_calls"]
    assert session.ticket_created is True
    assert session.last_ticket_id is not None
    assert (
        "ticket" in t4["reply"].lower()
        or "team" in t4["reply"].lower()
    )



def test_compensation_demand_refusal(shared_kb):
    """Direct cash compensation demands must be refused under policy."""
    session = ConversationSession(
        conversation_id="TEST_REFUSE",
        kb=shared_kb,
    )

    result = session.process_turn(
        "I want ₹500 compensation right now for the delay!"
    )

    assert result["decision"] == "refuse"
    assert (
        "compensation" in result["reply"].lower()
        or "policy" in result["reply"].lower()
    )



def test_failed_verification_security(shared_kb):
    """Verify protected order details aren't revealed on failed verification."""
    session = ConversationSession(
        conversation_id="TEST_SEC",
        kb=shared_kb,
    )

    # Turn 1: Order provided
    session.process_turn("Order 8978 2837")

    # Turn 2: Incorrect verification value
    result = session.process_turn("Last 4 digits are 0000")

    assert session.order_verified is False
    assert "items" not in result["reply"].lower()
    assert "status" not in result["reply"].lower()


def test_all_practice_conversations_evaluation(shared_kb):
    """Evaluate all 96 turns across the 23 practice conversations."""
    conversations_path = PRACTICE_DIR / "conversations.csv"
    assert conversations_path.exists(), (
        f"Practice conversations file not found: {conversations_path}"
    )

    conv_df = pd.read_csv(conversations_path, dtype=str)
    assert len(conv_df) == 96

    results = []
    sessions = {}

    for _, row in conv_df.iterrows():
        conversation_id = row["conversation_id"]
        turn_number = int(row["turn"])
        message = row["customer_message"]
        expected_decision = row.get("expected_decision", "")
        expected_tools = str(row.get("expected_tool_calls", ""))

        if conversation_id not in sessions:
            sessions[conversation_id] = ConversationSession(
                conversation_id=conversation_id,
                kb=shared_kb,
            )

        session = sessions[conversation_id]
        output = session.process_turn(message)

        decision_match = output["decision"] == expected_decision
        tools_match = True

        if expected_tools and expected_tools.lower() != "nan":
            if (
                "lookup_order" in expected_tools
                and not any(
                    "lookup_order" in tool
                    for tool in output["tool_calls"]
                )
            ):
                tools_match = False

            if (
                "create_ticket" in expected_tools
                and not any(
                    "create_ticket" in tool
                    for tool in output["tool_calls"]
                )
            ):
                tools_match = False

        results.append(
            {
                "conversation_id": conversation_id,
                "turn": turn_number,
                "message": message,
                "expected_decision": expected_decision,
                "actual_decision": output["decision"],
                "decision_match": decision_match,
                "expected_tool_calls": expected_tools,
                "actual_tool_calls": " ; ".join(
                    output["tool_calls"]
                ),
                "tools_match": tools_match,
                "verified": output["verified"],
                "reply": output["reply"],
            }
        )

    results_df = pd.DataFrame(results)

    decision_accuracy = results_df["decision_match"].mean() * 100
    tool_accuracy = results_df["tools_match"].mean() * 100

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "conversations_evaluation.csv"
    results_df.to_csv(
        report_path,
        index=False,
        encoding="utf-8",
    )

    assert len(results_df) == 96
    assert decision_accuracy >= 70.0, (
        f"Decision accuracy {decision_accuracy:.1f}% below expectation"
    )
    assert tool_accuracy >= 75.0, (
        f"Tool accuracy {tool_accuracy:.1f}% below expectation"
    )
