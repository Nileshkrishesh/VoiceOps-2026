
"""LLM Agent for ZentroMart AI Customer Support.

Supports Gemini, OpenAI-compatible providers, and offline fallback.
Provides a basic customer-support agent without document retrieval.
"""

import os
import re
import time
from typing import Optional

from src.config import (
    LLM_PROVIDER,
    LLM_MODEL,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    REFERENCE_DATE_STR,
)


ZENTROMART_SYSTEM_PROMPT = f"""You are the official AI Customer Support Assistant for ZentroMart, an Indian online store selling groceries and electronics.
Today's reference date is {REFERENCE_DATE_STR}. All timelines must be calculated relative to this date.

Core Guidelines:
1. On the very first customer-facing response, introduce yourself as ZentroMart's AI assistant.
2. Maintain a polite, helpful, professional tone in English, Hindi, or Hinglish as requested.
3. Only use verified company policies or retrieved evidence.
4. If information is insufficient, say so and offer to connect the customer to a human support executive.
5. Never claim to have checked, modified, cancelled, or refunded an order unless a tool call actually succeeded.
6. Politely refuse requests that violate company policy.
7. Keep answers concise, clear, and easy to understand.
"""


class LLMClient:
    """Multi-provider LLM interface with offline fallback."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = (
            provider or os.getenv("LLM_PROVIDER") or "gemini"
        ).lower()

        self.model = (
            model
            or os.getenv("LLM_MODEL")
            or (
                "gemini-2.5-flash"
                if self.provider in ("gemini", "google")
                else "gpt-4o-mini"
            )
        )

        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or ""
        )

        self._client = None
        self._init_backend()

    def _init_backend(self):
        """Initialize the selected provider backend."""

        # 1. Google Gemini
        if self.provider in ("gemini", "google"):
            gemini_key = (
                self.api_key
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
            )

            if gemini_key and not gemini_key.startswith("YOUR_"):
                try:
                    from google import genai

                    self._client = genai.Client(api_key=gemini_key)
                    self.provider = "gemini_genai"
                    return
                except Exception as e:
                    print(
                        f"[LLM INIT ERROR] Gemini GenAI: "
                        f"{type(e).__name__}: {e}"
                    )

                try:
                    import google.generativeai as genai_legacy

                    genai_legacy.configure(api_key=gemini_key)
                    self._client = genai_legacy.GenerativeModel(self.model)
                    self.provider = "gemini_legacy"
                    return
                except Exception as e:
                    print(
                        f"[LLM INIT ERROR] Gemini Legacy: "
                        f"{type(e).__name__}: {e}"
                    )

        # 2. OpenAI / Groq / OpenRouter
        if (
            self.provider in ("openai", "groq", "openrouter")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GROQ_API_KEY")
        ):
            key = (
                self.api_key
                or os.getenv("GROQ_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
            base_url = None

            if self.provider == "groq" or (
                not os.getenv("OPENAI_API_KEY")
                and os.getenv("GROQ_API_KEY")
            ):
                base_url = "https://api.groq.com/openai/v1"
                key = os.getenv("GROQ_API_KEY") or key

                if not os.getenv("LLM_MODEL"):
                    self.model = "qwen/qwen3.8-27b"

            elif self.provider == "openrouter":
                base_url = "https://openrouter.ai/api/v1"

            if key and not key.startswith("YOUR_"):
                try:
                    from openai import OpenAI

                    self._client = OpenAI(
                        api_key=key,
                        base_url=base_url,
                    )
                    self.provider = "openai_compatible"
                    return
                except Exception as e:
                    print(
                        f"[LLM INIT ERROR] OpenAI-compatible: "
                        f"{type(e).__name__}: {e}"
                    )

        # 3. Offline fallback
        self.provider = "offline_fallback"
        self._client = None
        print("[LLM WARNING] No live provider initialized; using offline fallback.")

    def is_live(self) -> bool:
        """Return whether a cloud-provider client is initialized."""
        return (
            self.provider != "offline_fallback"
            and self._client is not None
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = ZENTROMART_SYSTEM_PROMPT,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        """Generate a response, logging provider failures before fallback."""

        if not prompt or not prompt.strip():
            return (
                "Hello! I am ZentroMart's AI customer support assistant. "
                "How can I help you with your order, delivery, or returns today?"
            )

        # 1. Gemini GenAI Client with 429 backoff retry
        if self.provider == "gemini_genai" and self._client:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    full_contents = (
                        f"{system_prompt}\n\nCustomer Message: {prompt}"
                    )

                    response = self._client.models.generate_content(
                        model=self.model,
                        contents=full_contents,
                    )

                    if response and getattr(response, "text", None):
                        return response.text.strip()

                    print("[LLM WARNING] Gemini GenAI returned an empty response.")
                    break

                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                        delay_match = re.search(r"retry\s+in\s+([\d\.]+)\s*s", err_msg, re.IGNORECASE)
                        delay = float(delay_match.group(1)) + 1.0 if delay_match else (attempt + 1) * 5.0
                        delay = min(max(delay, 2.0), 30.0)
                        print(f"[LLM 429 RATE LIMIT] Waiting {delay:.1f}s before retry ({attempt+1}/{max_retries})...")
                        time.sleep(delay)
                        continue
                    else:
                        print(
                            f"[LLM ERROR] Gemini GenAI: "
                            f"{type(e).__name__}: {e}"
                        )
                        break

        # 2. Gemini Legacy
        if self.provider == "gemini_legacy" and self._client:
            try:
                chat = self._client.start_chat()
                response = chat.send_message(
                    f"System: {system_prompt}\nCustomer: {prompt}"
                )

                if response and getattr(response, "text", None):
                    return response.text.strip()

                print("[LLM WARNING] Gemini Legacy returned an empty response.")

            except Exception as e:
                print(
                    f"[LLM ERROR] Gemini Legacy: "
                    f"{type(e).__name__}: {e}"
                )

        # 3. OpenAI-compatible Client
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

                content = completion.choices[0].message.content

                if content and content.strip():
                    return content.strip()

                print("[LLM WARNING] OpenAI-compatible provider returned an empty response.")

            except Exception as e:
                print(
                    f"[LLM ERROR] OpenAI-compatible: "
                    f"{type(e).__name__}: {e}"
                )

        # 4. Offline fallback
        # If this prompt is for RAG evidence grounding, return empty string so RAGAgent synthesizes from evidence
        if "OFFICIAL RETRIEVED EVIDENCE" in prompt:
            print("[LLM WARNING] Live LLM call failed for RAG prompt; falling back to grounded synthesis.")
            return ""

        print("[LLM WARNING] Using offline baseline response.")
        return self._generate_offline_baseline(prompt, system_prompt)

    def _generate_offline_baseline(
        self,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """Conservative fallback that does not invent company policies."""

        p_lower = prompt.lower()

        if any(
            word in p_lower
            for word in (
                "midnight",
                "drone",
                "crypto",
                "bitcoin",
                "hire",
                "job",
                "lottery",
            )
        ):
            return (
                "Hello! I am ZentroMart's AI customer support assistant. "
                "I don't have information about that in our official "
                "company policies. Would you like me to connect you "
                "with our support team?"
            )

        return (
            "Hello! I am ZentroMart's AI customer support assistant. "
            "I would be glad to help you with your inquiry. "
            "Could you please tell me more about what you need assistance with?"
        )


class BasicLLMAgent:
    """Step 1 agent: LLM customer support without document retrieval."""

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

        # Refuse direct cash compensation requests.
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

        # Introduce the AI on the first customer-facing reply.
        if self.is_first_turn:
            self.is_first_turn = False

            ai_intro_markers = (
                "ai assistant",
                "ai customer support",
                "zentromart's ai",
                "ai support assistant",
            )

            if not any(
                marker in raw_reply.lower()
                for marker in ai_intro_markers
            ):
                raw_reply = (
                    "Hello! I am ZentroMart's AI customer support assistant. "
                    + raw_reply
                )

        return raw_reply
