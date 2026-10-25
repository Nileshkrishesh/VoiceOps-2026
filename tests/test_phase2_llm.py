"""Test suite for Phase 2 & Step 1: Basic LLM Agent and connectivity."""
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_agent import LLMClient, BasicLLMAgent, ZENTROMART_SYSTEM_PROMPT

def test_llm_client_initialization():
    """Verify that the LLM client initializes and reports its backend."""
    client = LLMClient()
    assert client.provider in ["gemini_genai", "gemini_legacy", "openai_compatible", "offline_fallback"]

def test_first_turn_ai_introduction():
    """Verify that the agent identifies itself as an AI assistant on the first reply."""
    agent = BasicLLMAgent()
    reply = agent.answer_question("Can you help me?")
    reply_lower = reply.lower()
    assert "ai" in reply_lower, "First response must introduce the assistant as an AI"

def test_empty_input_handling():
    """Verify that blank or whitespace input is handled gracefully."""
    agent = BasicLLMAgent()
    reply = agent.answer_question("   ")
    assert len(reply) > 10
    assert "help" in reply.lower() or "zentromart" in reply.lower()

def test_uncertainty_and_refusal_handling():
    """Verify that unreasonable compensation requests or missing policies are addressed properly."""
    agent = BasicLLMAgent()
    # Test refusal of illegal compensation demand
    refusal_reply = agent.answer_question("I demand 500 Rs cash compensation right now for late delivery!")
    assert "compensation" in refusal_reply.lower() or "policy" in refusal_reply.lower()
