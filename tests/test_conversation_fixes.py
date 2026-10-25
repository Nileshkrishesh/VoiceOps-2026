
"""Tests for conversation fixes: greeting, duplicate tickets, refund accuracy."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.conversation import ConversationSession
from src.knowledge_base import KnowledgeBase


def make_verified_session(conversation_id, order_id="69520867",
                          status="delivered", payment_method="upi"):
    """Create a session with a verified test order."""
    kb = KnowledgeBase()
    session = ConversationSession(conversation_id, kb=kb)
    session.current_order_id = order_id
    session.order_verified = True
    session.verified_order_data = {
        "order_id": order_id,
        "status": status,
        "customer_first_name": "Test",
        "payment_method": payment_method,
    }
    return session


def test_greeting_once_per_conversation():
    """AI should greet once, not repeat its introduction."""
    kb = KnowledgeBase()
    session = ConversationSession("TEST_GREETING", kb=kb)

    r1 = session.process_turn("Hello, I need help")
    assert session.has_greeted is True

    greeting_markers = [
        "namaste",
        "ai assistant",
        "zentromart's ai",
    ]
    assert any(
        marker in r1["reply"].lower()
        for marker in greeting_markers
    ), f"Turn 1 should include greeting. Got: {r1['reply']}"

    r2 = session.process_turn("My order is 69520867")
    assert not any(
        marker in r2["reply"].lower()
        for marker in greeting_markers
    ), f"Turn 2 should not repeat greeting. Got: {r2['reply']}"

    r3 = session.process_turn("Last four digits are 0101")
    assert "namaste" not in r3["reply"].lower(), (
        f"Turn 3 should not repeat greeting. Got: {r3['reply']}"
    )

    r4 = session.process_turn("Can I cancel it?")
    assert "ai assistant" not in r4["reply"].lower(), (
        f"Turn 4 should not repeat introduction. Got: {r4['reply'][:200]}"
    )


def test_no_duplicate_tickets():
    """Cash compensation is refused; repeated handover reuses its ticket."""
    session = make_verified_session("TEST_DUP_TICKET")

    # Cash compensation must be refused under company policy.
    r1 = session.process_turn("I want 500 Rs cash compensation!")

    assert r1["decision"] == "refuse", (
        f"Expected refusal, got: {r1.get('decision')}"
    )

    # A refusal should not itself create a ticket.
    assert session.ticket_created is False, (
        "Compensation refusal alone should not create an escalation ticket"
    )

    # Request human assistance.
    r2 = session.process_turn("Connect me to a human agent")

    assert session.ticket_created is True, (
        "Human handover should create an escalation ticket"
    )

    first_ticket_id = session.last_ticket_id
    assert first_ticket_id, "Expected a valid ticket ID"

    # Repeating the handover should not create another ticket.
    r3 = session.process_turn("Connect me to a human agent")

    assert session.last_ticket_id == first_ticket_id, (
        f"Duplicate ticket detected: {first_ticket_id} "
        f"became {session.last_ticket_id}"
    )


def test_refund_timeline_from_policy():
    """Refund answers should include relevant REF policy evidence."""
    session = make_verified_session(
        "TEST_REFUND",
        payment_method="upi",
    )

    result = session.process_turn("How long will the refund take?")

    assert result["evidence"], "Expected policy evidence"
    assert any(
        "REF" in str(item) for item in result["evidence"]
    ), f"Expected REF policy evidence, got: {result['evidence']}"

    reply = result["reply"].lower()
    has_timeline = any(
        phrase in reply
        for phrase in ("1 to 3", "1-3", "one to three", "1 - 3")
    )
    assert has_timeline, (
        f"Expected UPI refund timeline of 1–3 days. Got: {result['reply']}"
    )


def test_business_day_clarification():
    """Refund answers for card payments should include policy evidence."""
    session = make_verified_session(
        "TEST_BIZDAY",
        order_id="12345678",
        payment_method="credit_card",
    )

    result = session.process_turn("When will my refund arrive?")

    assert result["evidence"], "Expected policy evidence"
    assert any(
        "REF" in str(item) for item in result["evidence"]
    ), f"Expected REF policy evidence, got: {result['evidence']}"


def test_cancellation_shipped_order():
    """Shipped-order cancellation should explain available options."""
    session = make_verified_session(
        "TEST_CANCEL",
        status="shipped",
        payment_method="upi",
    )
    session.verified_order_data["customer_first_name"] = "Naveen"

    result = session.process_turn("Can I cancel it?")

    assert result["evidence"], "Expected cancellation policy evidence"
    assert any(
        "CAN" in str(item) for item in result["evidence"]
    ), f"Expected CAN policy evidence, got: {result['evidence']}"

    reply = result["reply"].lower()
    assert "ship" in reply or "shipped" in reply, (
        f"Expected mention of shipped status. Got: {result['reply'][:300]}"
    )
    assert any(
        term in reply for term in ("refuse", "door", "return")
    ), f"Expected a return/refusal option. Got: {result['reply'][:300]}"


def test_verification_before_order_details():
    """Order details should not be disclosed before verification."""
    kb = KnowledgeBase()
    session = ConversationSession("TEST_VERIFY", kb=kb)

    r1 = session.process_turn("My order is 89782837")

    assert session.order_verified is False
    assert (
        "verification" in r1["reply"].lower()
        or "last 4" in r1["reply"].lower()
    )
    assert "customer" not in r1["reply"].lower()

    r2 = session.process_turn("Last four digits are 4533")

    assert session.order_verified is True
    assert session.verified_order_data is not None
    assert (
        "status" in r2["reply"].lower()
        or "delivered" in r2["reply"].lower()
    )


def test_failed_verification():
    """Failed verification must not disclose order details."""
    kb = KnowledgeBase()
    session = ConversationSession("TEST_FAIL_VERIFY", kb=kb)

    session.process_turn("My order is 89782837")
    result = session.process_turn("Last four digits are 9999")

    assert session.order_verified is False
    assert (
        "did not match" in result["reply"].lower()
        or "failed" in result["reply"].lower()
    )
    assert session.verified_order_data is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
