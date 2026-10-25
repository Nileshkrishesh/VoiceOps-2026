
"""
VoiceOps 2026 - ZentroMart Conversation Manager

Features:
- Multi-turn conversation state
- Caller verification before order disclosure
- Order lookup using the supplied mock tool
- RAG-based cancellation, refund and return policy answers
- Human escalation with verified ticket creation
- Evidence and tool-call tracking
- No fabricated order dates, payment methods or ticket IDs
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.tools_adapter import lookup_order, create_ticket
from src.knowledge_base import KnowledgeBase
from src.rag_agent import RAGAgent


def extract_spoken_sequence(text: str) -> Optional[str]:
    """Extract eight consecutive spoken/numeric digits from text."""
    digit_words = {
        "zero": "0", "oh": "0", "o": "0",
        "one": "1", "two": "2", "three": "3",
        "four": "4", "five": "5", "six": "6",
        "seven": "7", "eight": "8", "nine": "9",
    }
    tokens = re.findall(r"[a-z]+|\d+", (text or "").lower())
    current = ""

    for token in tokens:
        if token.isdigit():
            if len(token) == 8:
                return token
            if 1 <= len(token) <= 4:
                current += token
                if len(current) == 8:
                    return current
                if len(current) > 8:
                    current = token
            else:
                current = ""
        elif token in digit_words:
            current += digit_words[token]
            if len(current) == 8:
                return current
            if len(current) > 8:
                current = digit_words[token]
        else:
            current = ""
    return None


def extract_order_id(text: str) -> Optional[str]:
    """Extract an 8-digit order ID written as digits or spoken digit words."""
    if not text:
        return None

    # Prefer an ID mentioned close to the phrase "order id".
    lower = text.lower()
    order_pos = lower.find("order id")
    if order_pos >= 0:
        candidate = extract_spoken_sequence(text[order_pos + len("order id"):])
        if candidate:
            return candidate

    return extract_spoken_sequence(text)


class ConversationSession:
    """Manages one customer's support conversation."""

    def __init__(
        self,
        conversation_id: str,
        kb: Optional[KnowledgeBase] = None,
    ):
        self.conversation_id = conversation_id
        self.kb = kb if kb is not None else KnowledgeBase()
        self.rag_agent = RAGAgent(knowledge_base=self.kb)

        self.history: List[Dict[str, str]] = []
        self.current_order_id: Optional[str] = None
        self.order_verified = False
        self.verified_order_data: Optional[Dict[str, Any]] = None
        self.verification_attempts = 0
        self.current_issue: Optional[str] = None

        self.ticket_created = False
        self.last_ticket_id: Optional[str] = None
        self.has_greeted = False  # Track if AI introduction already given

    # ---------------------------------------------------------
    # Public interface
    # ---------------------------------------------------------

    def respond(self, message: str) -> str:
        """Compatibility method for chat and voice integrations."""
        return self.process_turn(message)["reply"]

    def process_turn(self, customer_message: str) -> Dict[str, Any]:
        """Process one customer turn and return structured results."""

        msg = (customer_message or "").strip()
        turn_number = len(self.history) + 1

        tools_used: List[str] = []
        evidence: List[Any] = []
        decision = "answer"

        if not msg:
            return self._result(
                turn_number,
                "Please tell me how I can help you.",
                "clarify",
                tools_used,
                evidence,
            )

        lower = msg.lower()

        # Direct cash-compensation demands are refused even before order
        # verification; this does not disclose any order-specific information.
        compensation_demand_terms = (
            "compensation", "compensate", "cash compensation",
            "mental agony", "mukawza", "give me money", "pay me",
            "want money",
        )
        if any(term in lower for term in compensation_demand_terms):
            return self._finish(
                msg,
                turn_number,
                (
                    "I understand your concern. However, direct cash "
                    "compensation cannot be provided under ZentroMart's "
                    "policy. I can help you review the applicable order "
                    "or refund policy."
                ),
                "refuse",
                tools_used,
                evidence,
            )

        # Extract an order ID from numeric digits or STT-spelled digits
        # such as "six nine five two zero eight six seven".
        extracted_id = extract_order_id(msg)
        order_match = re.match(r"\d{8}", extracted_id) if extracted_id else None

        # A new order ID resets the previous order's verification.
        if extracted_id:
            new_order_id = extracted_id
            if new_order_id != self.current_order_id:
                self.current_order_id = new_order_id
                self.order_verified = False
                self.verified_order_data = None
                self.verification_attempts = 0
                self.current_issue = None

        # First interaction.
        if turn_number == 1 and not self.current_order_id:
            self.has_greeted = True
            return self._result(
                turn_number,
                "Namaste! I am ZentroMart's AI customer support "
                "assistant. Please share your 8-digit Order ID "
                "if your question concerns an existing order.",
                "clarify",
                tools_used,
                evidence,
            )

        # Order lookup and caller verification.
        if self.current_order_id and not self.order_verified:
            return self._handle_verification(
                msg=msg,
                lower=lower,
                turn_number=turn_number,
                order_match=order_match,
                tools_used=tools_used,
                evidence=evidence,
            )

        # Verified order conversation.
        if self.order_verified and self.verified_order_data:
            return self._handle_verified_conversation(
                msg=msg,
                lower=lower,
                turn_number=turn_number,
                tools_used=tools_used,
                evidence=evidence,
            )

        # General questions use the knowledge base.
        return self._answer_general_question(
            msg,
            turn_number,
            tools_used,
        )

    # ---------------------------------------------------------
    # Result handling
    # ---------------------------------------------------------

    def _result(
        self,
        turn: int,
        reply: str,
        decision: str,
        tools: List[str],
        evidence: List[Any],
    ) -> Dict[str, Any]:
        """Save history and return a consistent response schema."""

        self.history.append({
            "user": "",
            "agent": reply,
        })

        # The caller replaces the empty user field after this
        # helper returns, using _record_user() below if needed.
        return {
            "turn": turn,
            "reply": reply,
            "decision": decision,
            "tool_calls": list(tools),
            "evidence": list(evidence),
            "order_id": self.current_order_id,
            "verified": self.order_verified,
            "ticket_created": self.ticket_created,
            "ticket_id": self.last_ticket_id,
        }

    def _finish(
        self,
        msg: str,
        turn: int,
        reply: str,
        decision: str,
        tools: List[str],
        evidence: List[Any],
    ) -> Dict[str, Any]:
        """Record the actual customer message and response."""

        result = self._result(
            turn,
            reply,
            decision,
            tools,
            evidence,
        )

        self.history[-1]["user"] = msg
        return result

    # ---------------------------------------------------------
    # Order verification
    # ---------------------------------------------------------

    def _handle_verification(
        self,
        msg: str,
        lower: str,
        turn_number: int,
        order_match: Optional[re.Match],
        tools_used: List[str],
        evidence: List[Any],
    ) -> Dict[str, Any]:

        order_id = self.current_order_id

        # Do not treat the order ID itself as verification proof.
        if order_match:
            lookup_order(order_id)
            tools_used.append(f"lookup_order({order_id})")

            return self._finish(
                msg,
                turn_number,
                f"I can help with order "
                f"{self._format_order(order_id)}. "
                "For your security, provide either the last "
                "4 digits of your registered phone number "
                "or your 6-digit delivery pincode.",
                "clarify",
                tools_used,
                evidence,
            )

        # Stop repeatedly accepting verification attempts.
        if self.verification_attempts >= 2:
            if self._requests_human(lower):
                return self._create_escalation(
                    msg=msg,
                    turn=turn_number,
                    summary=(
                        "Caller could not complete verification "
                        f"for order {order_id} and requested "
                        "human assistance. Do not disclose "
                        "protected order details."
                    ),
                    reason="failed_verification",
                    tools=tools_used,
                    evidence=evidence,
                    verified=False,
                )

            return self._finish(
                msg,
                turn_number,
                "I couldn't verify your details. For your "
                "security, I cannot disclose order information. "
                "You may request assistance from a human "
                "support representative.",
                "refuse",
                tools_used,
                evidence,
            )

        # Accept a standalone 4-digit phone suffix or 6-digit
        # pincode. Leading zeroes are preserved as strings.
        digits = re.findall(r"(?<!\d)(\d{4}|\d{6})(?!\d)", msg)
        proof = digits[0] if digits else None

        if not proof:
            return self._finish(
                msg,
                turn_number,
                "Please provide the last 4 digits of your "
                "registered phone number or your 6-digit "
                "delivery pincode.",
                "clarify",
                tools_used,
                evidence,
            )

        # Validate against the real provided mock tool.
        try:
            result = lookup_order(
                order_id,
                verification_value=proof,
            )
            tools_used.append(
                f"lookup_order({order_id}, verification_value=REDACTED)"
            )
        except Exception:
            return self._finish(
                msg,
                turn_number,
                "I'm unable to verify your details right now. "
                "Please try again later.",
                "error",
                tools_used,
                evidence,
            )

        if not isinstance(result, dict) or result.get("verified") is not True:
            self.verification_attempts += 1

            if self.verification_attempts >= 2:
                reply = (
                    "Verification failed. For your security, "
                    "I cannot share order details. Would you "
                    "like help from a human representative?"
                )
                decision = "refuse"
            else:
                reply = (
                    "Those details did not match our records. "
                    "Please check them and try again."
                )
                decision = "clarify"

            return self._finish(
                msg,
                turn_number,
                reply,
                decision,
                tools_used,
                evidence,
            )

        # Store only the successful tool result.
        self.order_verified = True
        self.verified_order_data = result
        self.current_issue = msg

        name = result.get("customer_first_name")
        status = result.get("status")

        # Damaged-item replacement approval requires human review, even if
        # it is requested in the same turn as successful order verification.
        damage_terms = ("damage", "damaged", "broken", "cracked")
        replacement_terms = ("replacement", "replace", "approve", "approval")
        if (
            any(term in lower for term in damage_terms)
            and any(term in lower for term in replacement_terms)
        ):
            if self.ticket_created and self.last_ticket_id:
                return self._finish(
                    msg,
                    turn_number,
                    (
                        "Your damaged-item replacement request has already "
                        f"been escalated under support ticket {self.last_ticket_id}. "
                        "A human representative will review it; the replacement "
                        "has not been automatically approved."
                    ),
                    "escalate",
                    tools_used,
                    evidence,
                )

            summary = (
                f"Verified customer requests replacement approval for a damaged "
                f"item on order {self.current_order_id}. Customer request: {msg}. "
                "Replacement approval requires human review; no replacement "
                "has been automatically approved."
            )
            return self._create_escalation(
                msg,
                turn_number,
                summary,
                "damaged_item_replacement",
                tools_used,
                evidence,
                verified=True,
            )

        # If the same turn contains an actual inquiry, answer it.
        if self._is_order_inquiry(lower):
            reply, evidence = self._handle_verified_order_inquiry(
                msg,
                result,
            )
            return self._finish(
                msg,
                turn_number,
                reply,
                "answer",
                tools_used,
                evidence,
            )

        greeting = (
            f"Thank you, {name}! "
            if name
            else "Thank you! "
        )

        if status:
            greeting += (
                f"Your details have been verified. "
                f"The status of order {self._format_order(order_id)} "
                f"is '{status}'. How can I help you?"
            )
        else:
            greeting += (
                "Your details have been verified. "
                "What would you like help with?"
            )

        return self._finish(
            msg,
            turn_number,
            greeting,
            "answer",
            tools_used,
            evidence,
        )

    # ---------------------------------------------------------
    # Verified order conversation
    # ---------------------------------------------------------

    def _handle_verified_conversation(
        self,
        msg: str,
        lower: str,
        turn_number: int,
        tools_used: List[str],
        evidence: List[Any],
    ) -> Dict[str, Any]:

        # Direct cash compensation is refused under policy. Refusing this
        # request should not itself create a support ticket; a separate human
        # handover request can create one, and subsequent handovers reuse it.
        compensation_terms = [
            "compensation",
            "compensate",
            "cash compensation",
            "mental agony",
            "mukawza",
            "give me money",
            "pay me",
            "want money",
        ]
        if any(term in lower for term in compensation_terms):
            return self._finish(
                msg,
                turn_number,
                (
                    "I understand your concern. However, direct cash "
                    "compensation cannot be provided under ZentroMart's "
                    "policy. I can help you review the applicable order or "
                    "refund policy. If you would like a human representative "
                    "to review your case, I can connect you with support."
                ),
                "refuse",
                tools_used,
                evidence,
            )

        # Damaged-item replacement approval must be reviewed by a human.
        # Detect it here as well as during verification, because customers
        # commonly make this request in a later turn after verification.
        damage_terms = ("damage", "damaged", "broken", "cracked")
        replacement_terms = ("replacement", "replace", "approve", "approval")
        if (
            any(term in lower for term in damage_terms)
            and any(term in lower for term in replacement_terms)
        ):
            if self.ticket_created and self.last_ticket_id:
                return self._finish(
                    msg,
                    turn_number,
                    (
                        "Your damaged-item replacement request has already "
                        f"been escalated under support ticket {self.last_ticket_id}. "
                        "A human representative will review it; the replacement "
                        "has not been automatically approved."
                    ),
                    "escalate",
                    tools_used,
                    evidence,
                )

            summary = (
                f"Verified customer requests replacement approval for a damaged "
                f"item on order {self.current_order_id}. Customer request: {msg}. "
                "Replacement approval requires human review; no replacement "
                "has been automatically approved."
            )
            return self._create_escalation(
                msg,
                turn_number,
                summary,
                "damaged_item_replacement",
                tools_used,
                evidence,
                verified=True,
            )

        # Human handover takes precedence over other actions.
        if self._requests_human(lower):
            # If ticket already exists, inform customer rather than creating duplicate
            if self.ticket_created and self.last_ticket_id:
                return self._finish(
                    msg,
                    turn_number,
                    f"Your request has already been escalated via support ticket {self.last_ticket_id}. "
                    f"A human representative will contact you shortly to address your concern.",
                    "escalate",
                    tools_used,
                    evidence,
                )
            
            summary = (
                f"Verified customer requested human support "
                f"for order {self.current_order_id}. "
                f"Customer issue: {msg}. "
                f"Current verified order status: "
                f"{self.verified_order_data.get('status', 'not available')}."
            )

            return self._create_escalation(
                msg,
                turn_number,
                summary,
                "customer_escalation",
                tools_used,
                evidence,
                verified=True,
            )

        self.current_issue = msg

        try:
            reply, evidence = self._handle_verified_order_inquiry(
                msg,
                self.verified_order_data,
            )
        except Exception:
            reply = (
                "I'm unable to retrieve the relevant policy "
                "information right now. I don't want to give "
                "you an inaccurate answer."
            )
            decision = "error"
        else:
            decision = "answer"

        return self._finish(
            msg,
            turn_number,
            reply,
            decision,
            tools_used,
            evidence,
        )

    def _handle_verified_order_inquiry(
        self,
        message: str,
        order: Dict[str, Any],
    ) -> Tuple[str, List[Any]]:
        """
        Answer order questions using verified order data and retrieved policy.
        Do not invent order facts or policy details.
        """
        lower = (message or "").lower()
        status = order.get("status")
        order_id = order.get("order_id", self.current_order_id)
        promised_date = order.get("promised_date")
        payment_method = str(order.get("payment_method") or "").strip().lower()

        if not status:
            return (
                "I couldn't verify the current order status. "
                "I don't want to give you incorrect information.",
                [],
            )

        status_text = str(status).strip()
        status_lower = status_text.lower()

        # Cancellation policy must be answered from the knowledge base.
        if any(word in lower for word in ("cancel", "cancellation")):
            policy_question = (
                "According to the CURRENT ZentroMart cancellation policy "
                "(CAN-1, CAN-2), explain the available options for an order "
                f"whose verified status is '{status_text}'. "
                "If the status is 'shipped' or 'in_transit', explain the "
                "doorstep refusal option (CAN-2) clearly. Distinguish "
                "cancellation before shipping from return/refund after shipping. "
                "Do not invent policy details."
            )

            policy_reply, sources = self._ask_policy(policy_question)
            reply_lower = (policy_reply or "").lower()
            generic_greeting = (
                "ai customer support assistant" in reply_lower
                or "could you please tell me more" in reply_lower
                or reply_lower.strip() in ("hello", "hi", "hello!", "hi!")
            )

            if generic_greeting:
                if status_lower in ("shipped", "in_transit", "in transit"):
                    policy_reply = (
                        "Your order has already shipped, so cancellation while "
                        "it is in transit may not be possible. Under the "
                        "applicable CAN-2 policy, you may be able to refuse "
                        "delivery at the doorstep. If the order is delivered, "
                        "check the official return policy for the next steps."
                    )
                else:
                    policy_reply = (
                        "I couldn't retrieve a complete cancellation-policy "
                        "answer. Please check the official ZentroMart "
                        "cancellation policy or contact customer support to "
                        "confirm the available options."
                    )

            return (
                f"Your verified order status is '{status_text}'. {policy_reply}",
                sources,
            )

        # Refund timeline must use the payment method from the verified order.
        refund_terms = (
            "refund",
            "how long",
            "how many days",
            "timeline",
            "kab aayega",
            "kitne din",
            "time",
        )
        if any(term in lower for term in refund_terms):
            refund_context = (
                "According to the CURRENT ZentroMart refund policy (REF-2), "
                "explain the refund timeline after initiation. "
            )

            timeline_hints = {
                "upi": "1 to 3 business days",
                "credit_card": "5 to 7 business days",
                "debit_card": "5 to 7 business days",
                "card": "5 to 7 business days",
                "netbanking": "3 to 5 business days",
                "wallet": "instant, within 2 hours",
                "cod": (
                    "ZentroMart Wallet is instant; bank transfer is "
                    "5 to 7 business days"
                ),
                "cash_on_delivery": (
                    "ZentroMart Wallet is instant; bank transfer is "
                    "5 to 7 business days"
                ),
            }

            if payment_method:
                refund_context += f"Payment method: {payment_method}. "
                # Exact matches prevent 'card' matching 'credit_card' first.
                hint = timeline_hints.get(payment_method)
                if hint:
                    refund_context += f"Expected timeline listed in REF-2: {hint}. "
            else:
                refund_context += (
                    "Payment method is not available in the verified order record. "
                )

            refund_context += (
                f"Verified order status: {status_text}. "
                "Use official policy evidence only. Do not invent timelines."
            )

            policy_reply, sources = self._ask_policy(refund_context)
            reply_lower = (policy_reply or "").lower()
            generic_greeting = (
                "ai customer support assistant" in reply_lower
                or "could you please tell me more" in reply_lower
                or reply_lower.strip() in ("hello", "hi", "hello!", "hi!")
            )

            if generic_greeting:
                timeline = timeline_hints.get(payment_method)
                if payment_method in ("cod", "cash_on_delivery"):
                    policy_reply = (
                        "For cash-on-delivery orders, the refund timeline "
                        "depends on the refund method. Please check REF-2 or "
                        "contact customer support to confirm whether the refund "
                        "will be issued to ZentroMart Wallet or by bank transfer."
                    )
                elif timeline:
                    policy_reply = (
                        "The expected refund timeline listed in the existing "
                        f"REF-2 mapping for {payment_method} payments is "
                        f"{timeline} after refund initiation. Please confirm "
                        "the timeline against the official policy."
                    )
                else:
                    policy_reply = (
                        "I couldn't confirm the refund timeline from the "
                        "available payment details. Please check the official "
                        "refund policy (REF-2) or contact customer support."
                    )

            return policy_reply, sources

        # Return eligibility requires current policy evidence.
        if "return" in lower:
            policy_question = (
                "According to the CURRENT ZentroMart return policy, explain "
                "return eligibility, the applicable time window, and how the "
                "customer can request a return. Do not invent category-specific rules."
            )
            return self._ask_policy(policy_question)

        # Order status and delivery facts must come from the actual order record.
        if any(
            word in lower
            for word in (
                "where",
                "track",
                "status",
                "delivery",
                "arrive",
                "kab",
                "kahan",
            )
        ):
            reply = (
                f"Your order {self._format_order(order_id)} "
                f"is currently '{status_text}'."
            )
            if promised_date:
                reply += f" Its promised delivery date is {promised_date}."
            else:
                reply += (
                    " I couldn't verify a promised delivery date "
                    "from the order record."
                )
            return reply, []

        # Contextual follow-up can use the previous issue as additional context.
        if self.current_issue and any(
            phrase in lower for phrase in ("that", "it", "same", "what about")
        ):
            question = (
                f"The customer's previous issue was: {self.current_issue}. "
                f"The follow-up is: {message}. "
                "Answer using the current ZentroMart policy documents only. "
                "Do not invent details."
            )
            return self._ask_policy(question)

        return (
            f"I can help with your verified order {self._format_order(order_id)}. "
            "Would you like to check its status, cancellation options, "
            "refund policy, or return eligibility?",
            [],
        )

    # ---------------------------------------------------------
    # RAG and evidence
    # ---------------------------------------------------------

    def _ask_policy(
        self,
        question: str,
    ) -> Tuple[str, List[Any]]:
        """
        Call the existing RAG agent and capture its evidence.

        The RAG agent itself must enforce abstention when evidence
        is insufficient. Verify that behavior in rag_agent.py.
        """

        answer = self.rag_agent.answer_question(question)

        raw_evidence = getattr(
            self.rag_agent,
            "last_retrieved_evidence",
            [],
        )

        sources = list(raw_evidence) if raw_evidence else []

        if not isinstance(answer, str) or not answer.strip():
            return (
                "I couldn't verify this information from the "
                "available ZentroMart policy documents.",
                sources,
            )

        if not sources:
            return (
                "I couldn't verify this answer against a retrieved "
                "policy source. I don't want to give you "
                "potentially incorrect information.",
                [],
            )

        return answer.strip(), sources

    def _answer_general_question(
        self,
        msg: str,
        turn: int,
        tools: List[str],
    ) -> Dict[str, Any]:

        try:
            reply = self.rag_agent.answer_question(msg)
            evidence = list(
                getattr(
                    self.rag_agent,
                    "last_retrieved_evidence",
                    [],
                ) or []
            )

            if not evidence:
                reply = (
                    "I couldn't verify a reliable answer from "
                    "the available ZentroMart documents. "
                    "Could you clarify your question?"
                )
                decision = "clarify"
            else:
                decision = "answer"

        except Exception:
            reply = (
                "I'm sorry, I couldn't retrieve the relevant "
                "information right now. Please try again later."
            )
            evidence = []
            decision = "error"

        return self._finish(
            msg,
            turn,
            reply,
            decision,
            tools,
            evidence,
        )

    # ---------------------------------------------------------
    # Ticket creation and escalation
    # ---------------------------------------------------------

    def _create_escalation(
        self,
        msg: str,
        turn: int,
        summary: str,
        reason: str,
        tools: List[str],
        evidence: List[Any],
        verified: bool,
    ) -> Dict[str, Any]:

        try:
            ticket_result = create_ticket(
                summary=summary,
                order_id=self.current_order_id,
                reason=reason,
            )
            tools.append("create_ticket()")

        except Exception:
            ticket_result = {"created": False}

        if (
            isinstance(ticket_result, dict)
            and ticket_result.get("created") is True
            and ticket_result.get("ticket_id")
        ):
            self.ticket_created = True
            self.last_ticket_id = ticket_result["ticket_id"]

            reply = (
                f"Your support ticket {self.last_ticket_id} "
                "has been created successfully. A human support "
                "representative can review your request."
            )
            decision = "escalate"

        else:
            reply = (
                "I couldn't create the support ticket automatically. "
                "I cannot confirm that a human handover has occurred."
            )
            decision = "error"

        return self._finish(
            msg,
            turn,
            reply,
            decision,
            tools,
            evidence,
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _requests_human(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in [
                "human",
                "human support",
                "support executive",
                "representative",
                "supervisor",
                "connect me",
                "talk to someone",
                "talk to a person",
                "escalate",
                "speak to an agent",
            ]
        )

    @staticmethod
    def _is_order_inquiry(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in [
                "cancel", "refund", "return", "status",
                "track", "delivery", "damage", "late",
                "how long", "timeline",
            ]
        )

    @staticmethod
    def _format_order(order_id: Optional[str]) -> str:
        oid = str(order_id or "").strip()

        if len(oid) == 8 and oid.isdigit():
            return f"{oid[:4]} {oid[4:]}"

        return oid
