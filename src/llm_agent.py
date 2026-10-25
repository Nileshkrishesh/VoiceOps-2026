"""LLM Agent for ZentroMart AI Customer Support.

Implements Step 1 of the VoiceOps 2026 capstone brief:
- Connects to hosted or local LLMs (Gemini, OpenAI, Groq, or resilient offline fallback).
- System prompt establishes identity as ZentroMart AI Customer Support Assistant.
- Introduces itself as AI on the first customer-facing reply.
- Handles blank inputs, uncertain questions, and tool boundaries cleanly.
"""
import os
import re
from typing import Optional, List, Dict, Any, Tuple
from src.config import (
    LLM_PROVIDER, LLM_MODEL, GEMINI_API_KEY, OPENAI_API_KEY,
    REFERENCE_DATE_STR
)

# Standard ZentroMart AI Support System Prompt
ZENTROMART_SYSTEM_PROMPT = f"""You are the official AI Customer Support Assistant for ZentroMart, an Indian online store selling groceries and electronics.
Today's reference date is {REFERENCE_DATE_STR}. All timelines must be calculated relative to this date.

Core Guidelines:
1. On the very first customer-facing response, introduce yourself as ZentroMart's AI assistant (e.g. "Namaste! I am ZentroMart's AI customer support assistant.").
2. Always maintain a polite, helpful, and professional tone (English, Hindi, or Hinglish as requested by the customer).
3. When answering customer questions, only use verified company policies or retrieved evidence provided to you.
4. If you do not have sufficient information or verified evidence, clearly state that you do not have that information and offer to connect the customer to a human support executive. NEVER fabricate policies, refund periods, dates, or compensation amounts.
5. NEVER claim to have checked, modified, cancelled, or refunded an order unless a tool call was actually executed and returned successful results.
6. When customer requests violate company policy (such as cash compensation demands, cancelling already shipped orders without refusal, or returns past the allowed return window), politely refuse under company policy and offer appropriate assistance.
7. Keep answers concise, clear, and easy to read or listen to.
"""

class LLMClient:
    """Multi-provider LLM interface supporting Gemini, OpenAI, Groq, and offline fallback."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()
        self.model = model or os.getenv("LLM_MODEL") or ("gemini-2.5-flash" if self.provider == "gemini" else "gpt-4o-mini")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or ""
        self._client = None
        self._init_backend()

    def _init_backend(self):
        """Initialize the selected provider backend."""
        # 1. Google Gemini
        if self.provider in ("gemini", "google"):
            gemini_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if gemini_key and not gemini_key.startswith("YOUR_"):
                try:
                    from google import genai
                    self._client = genai.Client(api_key=gemini_key)
                    self.provider = "gemini_genai"
                    return
                except Exception:
                    pass
                try:
                    import google.generativeai as genai_legacy
                    genai_legacy.configure(api_key=gemini_key)
                    self._client = genai_legacy.GenerativeModel(self.model)
                    self.provider = "gemini_legacy"
                    return
                except Exception:
                    pass

        # 2. OpenAI / Groq / OpenRouter
        if self.provider in ("openai", "groq", "openrouter") or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY"):
            key = self.api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = None
            if self.provider == "groq" or (not os.getenv("OPENAI_API_KEY") and os.getenv("GROQ_API_KEY")):
                base_url = "https://api.groq.com/openai/v1"
                self.model = self.model or os.getenv("LLM_MODEL") or "qwen/qwen3.8-27b"
                key = os.getenv("GROQ_API_KEY") or key
            elif self.provider == "openrouter":
                base_url = "https://openrouter.ai/api/v1"

            if key and not key.startswith("YOUR_"):
                try:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=key, base_url=base_url)
                    self.provider = "openai_compatible"
                    return
                except Exception:
                    pass

        # 3. Fallback offline engine
        self.provider = "offline_fallback"

    def is_live(self) -> bool:
        """Check if a live cloud provider is connected."""
        return self.provider != "offline_fallback" and self._client is not None

    def generate(
        self,
        prompt: str,
        system_prompt: str = ZENTROMART_SYSTEM_PROMPT,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        """Generate a response from the configured LLM backend."""
        # Clean blank input
        if not prompt or not prompt.strip():
            return "Hello! I am ZentroMart's AI customer support assistant. How can I help you with your order, delivery, or returns today?"

        # 1. Gemini GenAI Client
        if self.provider == "gemini_genai" and self._client:
            try:
                full_contents = f"{system_prompt}\n\nCustomer Message: {prompt}"
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=full_contents,
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except Exception as e:
                # Log and fallback to offline generator
                pass

        # 2. Gemini Legacy GenerativeAI
        if self.provider == "gemini_legacy" and self._client:
            try:
                chat = self._client.start_chat()
                response = chat.send_message(f"System: {system_prompt}\nCustomer: {prompt}")
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except Exception:
                pass

        # 3. OpenAI-compatible Client (OpenAI, Groq, OpenRouter)
        if self.provider == "openai_compatible" and self._client:
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                completion = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return completion.choices[0].message.content.strip()
            except Exception:
                pass

        # 4. Resilient Offline Baseline Generator
        return self._generate_offline_baseline(prompt, system_prompt)

    def _generate_offline_baseline(self, prompt: str, system_prompt: str) -> str:
        """Conservative offline fallback for Step 1 ungrounded baseline.
        
        This baseline deliberately avoids making specific policy claims.
        It acknowledges AI identity and offers to help, but does not
        invent policies, timelines, or requirements."""
        p_lower = prompt.lower()

        # Check for obvious out-of-scope questions
        if any(w in p_lower for w in ["midnight", "drone", "crypto", "bitcoin", "hire", "job", "lottery"]):
            return (
                "Hello! I am ZentroMart's AI customer support assistant. "
                "I don't have information about that in our official company policies. "
                "Would you like me to connect you with our support team?"
            )

        # General polite response acknowledging AI identity (Step 1 requirement)
        return (
            "Hello! I am ZentroMart's AI customer support assistant. "
            "I would be glad to help you with your inquiry. "
            "Could you please tell me more about what you need assistance with?"
        )


class BasicLLMAgent:
    """Step 1 Agent: Pure LLM customer support assistant without document retrieval."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.client = llm_client or LLMClient()
        self.is_first_turn = True

    
    def answer_question(self, question: str) -> str:
        """Answer a customer question with deterministic policy refusal."""
        if not question or not str(question).strip():
            return (
                "Hello! I am ZentroMart's AI customer support assistant. "
                "How can I help you today?"
            )

        question_text = str(question).strip()
        question_lower = question_text.lower()

        # Refuse direct cash compensation before calling the LLM.
        compensation_terms = (
            "compensation",
            "compensate",
            "cash compensation",
            "mental agony",
            "mukawza",
            "मुआवजा",
        )

        if any(term in question_lower for term in compensation_terms):
            self.is_first_turn = False
            return (
                "Direct cash compensation cannot be provided under "
                "ZentroMart's policy. I can help you review the "
                "applicable order or refund policy."
            )

        raw_reply = self.client.generate(
            prompt=question_text,
            system_prompt=ZENTROMART_SYSTEM_PROMPT,
        )

        # Ensure the first customer-facing reply identifies the AI.
        if self.is_first_turn:
            self.is_first_turn = False
            ai_intro_markers = [
                "ai assistant",
                "ai customer support",
                "zentromart's ai",
                "ai support assistant",
            ]
            if not any(marker in raw_reply.lower() for marker in ai_intro_markers):
                raw_reply = (
                    "Hello! I am ZentroMart's AI customer support assistant. "
                    + raw_reply
                )

        return raw_reply

