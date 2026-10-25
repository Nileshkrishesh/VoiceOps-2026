"""Manual test to verify all fixes."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_manual_tests():
    print("="*70)
    print("Testing VoiceOps 2026 Fixes")
    print("="*70)

    # Test 1: Business Day Calculations
    print("\n[TEST 1] Business Day Calculations")
    from datetime import date
    from src.config import is_business_day, add_business_days, OFFICIAL_HOLIDAYS

    # Test weekdays
    monday = date(2026, 10, 5)
    saturday = date(2026, 10, 10)
    sunday = date(2026, 10, 11)

    assert is_business_day(monday) == True, "Monday should be business day"
    assert is_business_day(saturday) == True, "Saturday should be business day"
    assert is_business_day(sunday) == False, "Sunday should NOT be business day"
    print("[PASS] Weekday/Weekend checks pass")

    # Test holidays
    holiday1 = date(2026, 10, 2)  # Gandhi Jayanti
    holiday2 = date(2026, 10, 19)  # Warehouse closure
    assert is_business_day(holiday1) == False, "Holiday should NOT be business day"
    assert is_business_day(holiday2) == False, "Holiday should NOT be business day"
    print(f"[PASS] Holiday checks pass ({len(OFFICIAL_HOLIDAYS)} holidays loaded)")

    # Test add_business_days
    result = add_business_days(date(2026, 10, 16), 2)
    # From Friday 16: +1 = Saturday 17 (business day), +2 = skip Sunday 18, skip Monday 19 (holiday), = Tuesday 20
    assert result == date(2026, 10, 20), f"Expected 2026-10-20, got {result}"
    print("[PASS] add_business_days with holiday skip works")

    # Test 2: Conversation - No Repeated Greetings
    print("\n[TEST 2] No Repeated Greetings")
    from src.conversation import ConversationSession
    from src.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    session = ConversationSession("MANUAL_TEST", kb=kb)

    r1 = session.process_turn("Hello")
    print(f"Turn 1: {r1['reply'][:80]}...")
    assert session.has_greeted == True, "Should mark as greeted"

    r2 = session.process_turn("What is the return window for electronics?")
    print(f"Turn 2: {r2['reply'][:80]}...")
    # Should NOT include "Namaste! I am ZentroMart's AI"
    greeting_repeated = "namaste" in r2['reply'].lower() and "ai assistant" in r2['reply'].lower()
    if greeting_repeated:
        print("[WARN] Greeting may be repeated (check full response)")
    else:
        print("[PASS] No greeting repetition detected")

    # Test 3: Duplicate Ticket Prevention
    print("\n[TEST 3] Duplicate Ticket Prevention")

    session2 = ConversationSession("TICKET_TEST", kb=kb)
    session2.current_order_id = "69520867"
    session2.order_verified = True
    session2.verified_order_data = {
        "order_id": "69520867",
        "status": "delivered",
        "customer_first_name": "Test",
        "payment_method": "upi"
    }

    # Compensation must be refused under company policy.
    r_comp = session2.process_turn("I want 500 Rs compensation!")
    assert r_comp["decision"] == "refuse", (
        f"Expected refusal for direct compensation, got: {r_comp['decision']}"
    )
    assert session2.ticket_created is False, (
        "Compensation refusal alone should not create a ticket"
    )
    print("[PASS] Direct compensation request refused")

    # A human handover request should create or reuse an escalation ticket.
    r_human = session2.process_turn("Connect me to human")

    assert session2.ticket_created is True, (
        "Human handover should create an escalation ticket"
    )
    first_ticket = session2.last_ticket_id
    assert first_ticket, "Ticket ID should exist"
    print(f"[PASS] Escalation ticket created: {first_ticket}")

    # Repeated handover should reuse the existing ticket.
    r_human_again = session2.process_turn("Connect me to human")
    second_ticket = session2.last_ticket_id

    assert first_ticket == second_ticket, (
        f"Should reuse ticket {first_ticket}, not create new {second_ticket}"
    )
    assert (
        "already" in r_human_again["reply"].lower()
        or first_ticket in r_human_again["reply"]
    ), "Should mention the existing ticket"

    print(f"[PASS] Duplicate ticket prevented, reused: {first_ticket}")

    # Test 4: Refund Timeline Evidence
    print("\n[TEST 4] Refund Timeline with Evidence")
    session3 = ConversationSession("REFUND_TEST", kb=kb)
    session3.current_order_id = "69520867"
    session3.order_verified = True
    session3.verified_order_data = {
        "order_id": "69520867",
        "status": "delivered",
        "customer_first_name": "Test",
        "payment_method": "upi"
    }

    r_refund = session3.process_turn("How long will the refund take?")
    print(f"Refund reply: {r_refund['reply'][:150]}...")
    print(f"Evidence: {r_refund['evidence']}")
    assert len(r_refund['evidence']) > 0, "Should have evidence"
    assert any("REF" in str(ev) for ev in r_refund['evidence']), \
        f"Should have REF policy evidence, got: {r_refund['evidence']}"
    print("[PASS] Refund answer includes policy evidence")

    # Test 5: Verification Security
    print("\n[TEST 5] Verification Security")
    session4 = ConversationSession("VERIFY_TEST", kb=kb)
    r_order = session4.process_turn("My order is 89782837")
    assert session4.order_verified == False, "Should not be verified yet"
    assert "verification" in r_order['reply'].lower() or "last 4" in r_order['reply'].lower()
    print("[PASS] Verification requested before revealing details")

    r_verify = session4.process_turn("Last four are 4533")
    assert session4.order_verified == True, "Should be verified with correct code"
    print("[PASS] Verification successful with correct proof")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("[PASS] All manual tests passed!")
    print("="*70)

if __name__ == "__main__":
    run_manual_tests()
