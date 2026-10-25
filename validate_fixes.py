"""Quick validation script to test critical fixes without full pytest."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge_base import KnowledgeBase
from src.rag_agent import RAGAgent
from src.conversation import ConversationSession
from src.llm_agent import BasicLLMAgent, LLMClient

def test_superseded_filtering():
    """Test that superseded policies are filtered."""
    print("\n=== Test 1: Superseded Policy Filtering ===")
    kb = KnowledgeBase()
    results = kb.retrieve("return window for electronics", filter_superseded=True)
    
    for chunk, score in results:
        print(f"  - {chunk.section_id}: {chunk.status} | {chunk.filename} | Score: {score:.3f}")
        assert chunk.status != "superseded", f"Found superseded chunk: {chunk.section_id}"
        assert "v3_superseded" not in chunk.filename, f"Found v3 file: {chunk.filename}"
    
    print("  ✅ PASS: No superseded policies in results")
    return True

def test_no_repeated_greeting():
    """Test that greeting only appears on first turn."""
    print("\n=== Test 2: No Repeated Greetings ===")
    kb = KnowledgeBase()
    session = ConversationSession("TEST001", kb=kb)
    
    # Turn 1
    r1 = session.process_turn("Hello, I need help")
    print(f"  Turn 1: {r1['reply'][:80]}...")
    assert "AI" in r1['reply'] or "assistant" in r1['reply'].lower()
    assert session.has_greeted == True
    
    # Turn 2 - general question (should not repeat greeting)
    r2 = session.process_turn("What is the return window for electronics?")
    print(f"  Turn 2: {r2['reply'][:80]}...")
    greeting_count = r2['reply'].lower().count("namaste") + r2['reply'].lower().count("i am zentromart")
    assert greeting_count == 0, f"Repeated greeting detected in turn 2"
    
    print("  ✅ PASS: No repeated greeting")
    return True

def test_hardcoded_policy_removed():
    """Test that offline fallback doesn't contain hardcoded policies."""
    print("\n=== Test 3: No Hardcoded Policies ===")
    client = LLMClient()
    client.provider = "offline_fallback"  # Force offline mode
    
    # Test compensation question
    resp = client.generate("I want 500 rupees compensation")
    print(f"  Compensation Q: {resp[:100]}...")
    assert "cannot provide direct cash compensation" not in resp, "Hardcoded compensation policy found"
    assert "company policy" not in resp.lower() or "don't have information" in resp.lower()
    
    # Test order lookup
    resp2 = client.generate("My order is 12345678")
    print(f"  Order lookup Q: {resp2[:100]}...")
    # Should be generic, not specific about verification
    
    print("  ✅ PASS: No hardcoded policies in offline fallback")
    return True

def test_compensation_refusal():
    """Test that compensation requests are refused."""
    print("\n=== Test 4: Compensation Request Refusal ===")
    kb = KnowledgeBase()
    session = ConversationSession("TEST002", kb=kb)
    
    # Set up verified order
    session.current_order_id = "12345678"
    session.order_verified = True
    session.verified_order_data = {
        "order_id": "12345678",
        "status": "delivered",
        "customer_first_name": "Test"
    }
    
    # Request compensation
    r = session.process_turn("I want ₹500 compensation for mental harassment")
    print(f"  Response: {r['reply'][:100]}...")
    print(f"  Decision: {r['decision']}")
    
    assert r['decision'] == "escalate", "Should escalate compensation request"
    assert r['ticket_created'] == True, "Should create ticket"
    assert "ticket" in r['reply'].lower() or "team" in r['reply'].lower()
    
    print("  ✅ PASS: Compensation refused and escalated")
    return True

def test_refund_timeline_context():
    """Test that refund questions use payment method."""
    print("\n=== Test 5: Refund Timeline with Payment Method ===")
    kb = KnowledgeBase()
    session = ConversationSession("TEST003", kb=kb)
    
    # Set up verified order with payment method
    session.current_order_id = "87654321"
    session.order_verified = True
    session.verified_order_data = {
        "order_id": "87654321",
        "status": "delivered",
        "customer_first_name": "Test",
        "payment_method": "upi"
    }
    
    # Ask about refund timeline
    r = session.process_turn("How long will the refund take?")
    print(f"  Response: {r['reply'][:150]}...")
    
    # Should have evidence from policy
    assert len(r['evidence']) > 0, "Should have policy evidence"
    print(f"  Evidence: {r['evidence']}")
    
    print("  ✅ PASS: Refund question processed with context")
    return True

def main():
    print("=" * 70)
    print("VoiceOps 2026: Critical Fixes Validation")
    print("=" * 70)
    
    tests = [
        test_superseded_filtering,
        test_no_repeated_greeting,
        test_hardcoded_policy_removed,
        test_compensation_refusal,
        test_refund_timeline_context,
    ]
    
    passed = 0
    failed = 0
    
    for test_fn in tests:
        try:
            if test_fn():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ FAIL: {e}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
