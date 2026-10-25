"""Simplified chat interface that works without FAISS/embeddings.

This version demonstrates core conversation logic without the RAG component,
bypassing the protobuf/TensorFlow dependency issue.
"""
import sys
import os
from pathlib import Path

# Suppress warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("VoiceOps 2026: ZentroMart AI Support (Simplified Demo)")
print("=" * 70)
print("Note: Running without RAG due to environment dependencies.")
print("This demonstrates conversation flow, verification, and tool execution.")
print("=" * 70)

from src.llm_agent import BasicLLMAgent, LLMClient
from src.tools_adapter import lookup_order, create_ticket

class SimpleConversation:
    """Lightweight conversation without RAG dependency."""
    
    def __init__(self):
        self.llm = BasicLLMAgent()
        self.history = []
        self.current_order_id = None
        self.order_verified = False
        self.verified_order_data = None
        self.verification_attempts = 0
        self.has_greeted = False
        self.ticket_created = False
        self.last_ticket_id = None
        
    def process(self, message):
        """Process one turn."""
        import re
        
        msg = message.strip()
        lower = msg.lower()
        
        # Detect order ID
        order_match = re.search(r"(?<!\d)(\d{4}\s+\d{4}|\d{8})(?!\d)", msg)
        if order_match:
            new_order_id = re.sub(r"\D", "", order_match.group(1))
            if new_order_id != self.current_order_id:
                self.current_order_id = new_order_id
                self.order_verified = False
                self.verified_order_data = None
                self.verification_attempts = 0
        
        # First greeting
        if not self.has_greeted:
            self.has_greeted = True
            if self.current_order_id:
                return f"Namaste! I am ZentroMart's AI customer support assistant. I can help with order {self.format_order(self.current_order_id)}. For your security, please provide either the last 4 digits of your registered phone number or your 6-digit delivery pincode."
            else:
                return "Namaste! I am ZentroMart's AI customer support assistant. Please share your 8-digit Order ID if your question concerns an existing order."
        
        # Handle verification
        if self.current_order_id and not self.order_verified:
            if order_match and self.verification_attempts == 0:
                # Just provided order ID
                try:
                    lookup_order(self.current_order_id)
                    return f"I can help with order {self.format_order(self.current_order_id)}. For your security, provide either the last 4 digits of your registered phone number or your 6-digit delivery pincode."
                except Exception as e:
                    return f"I'm unable to verify your order right now. Error: {e}"
            
            # Check for verification proof
            digits = re.findall(r"(?<!\d)(\d{4}|\d{6})(?!\d)", msg)
            proof = digits[0] if digits else None
            
            if not proof:
                if self.verification_attempts >= 2:
                    return "I couldn't verify your details after multiple attempts. For your security, I cannot disclose order information. Would you like me to connect you to a human support representative?"
                return "Please provide the last 4 digits of your registered phone number or your 6-digit delivery pincode."
            
            # Try verification
            try:
                result = lookup_order(self.current_order_id, verification_value=proof)
                
                if result.get("verified") == True:
                    self.order_verified = True
                    self.verified_order_data = result
                    name = result.get("customer_first_name", "")
                    status = result.get("status", "")
                    return f"Thank you{', ' + name if name else ''}! Your details have been verified. The status of order {self.format_order(self.current_order_id)} is '{status}'. How can I help you?"
                else:
                    self.verification_attempts += 1
                    if self.verification_attempts >= 2:
                        return "Verification failed. For your security, I cannot share order details. Would you like help from a human representative?"
                    return "Those details did not match our records. Please check them and try again."
            except Exception as e:
                return f"I'm unable to verify your details right now. Please try again later. Error: {e}"
        
        # Handle verified conversation
        if self.order_verified and self.verified_order_data:
            # Check compensation request
            if any(word in lower for word in ["compensation", "₹", "rupees", "cash", "mental agony"]):
                try:
                    ticket = create_ticket(
                        summary=f"Verified customer requested compensation for order {self.current_order_id}. Request: {msg}. Status: {self.verified_order_data.get('status')}.",
                        order_id=self.current_order_id,
                        reason="compensation_request"
                    )
                    if ticket.get("created") == True:
                        self.ticket_created = True
                        self.last_ticket_id = ticket["ticket_id"]
                        return f"I understand your frustration. However, under ZentroMart policy, I cannot provide direct cash compensation. I have created support ticket {self.last_ticket_id} for human review. A supervisor will contact you soon."
                except Exception:
                    pass
                return "I understand your concern about compensation. Let me connect you to a human supervisor who can review your case."
            
            # Check human request
            if any(word in lower for word in ["human", "person", "supervisor", "executive", "representative"]):
                try:
                    ticket = create_ticket(
                        summary=f"Verified customer requested human support for order {self.current_order_id}. Issue: {msg}.",
                        order_id=self.current_order_id,
                        reason="customer_escalation"
                    )
                    if ticket.get("created") == True:
                        self.ticket_created = True
                        self.last_ticket_id = ticket["ticket_id"]
                        return f"Your support ticket {self.last_ticket_id} has been created successfully. A human support representative will review your request."
                except Exception:
                    pass
                return "I'll connect you to a human representative. One moment please."
            
            # Order status
            if any(word in lower for word in ["status", "where", "track", "kab", "kahan"]):
                status = self.verified_order_data.get("status", "unknown")
                promised = self.verified_order_data.get("promised_date", "")
                reply = f"Your order {self.format_order(self.current_order_id)} is currently '{status}'."
                if promised:
                    reply += f" The promised delivery date is {promised}."
                return reply
            
            # Cancellation
            if "cancel" in lower:
                status = self.verified_order_data.get("status", "")
                if status in ["shipped", "in_transit"]:
                    return f"Your order status is '{status}'. Shipped orders cannot be cancelled through the app. However, you can refuse the parcel at your doorstep. For prepaid orders, the refund will be initiated once the parcel returns to our warehouse."
                else:
                    return f"Your order status is '{status}'. You can cancel orders that haven't shipped yet by going to My Orders in the ZentroMart app. The refund will be initiated immediately."
            
            # Refund
            if "refund" in lower:
                payment = self.verified_order_data.get("payment_method", "").lower()
                if "wallet" in payment:
                    return "Refunds to ZentroMart Wallet are instant, typically within 2 hours of initiation."
                elif "upi" in payment:
                    return "Refunds to UPI typically take 1 to 3 business days after initiation."
                elif "card" in payment or "credit" in payment or "debit" in payment:
                    return "Refunds to credit/debit cards typically take 5 to 7 business days after initiation."
                else:
                    return "Refund timelines depend on your payment method. For UPI: 1-3 days, Cards: 5-7 days, Wallet: instant."
            
            return f"I can help with your verified order {self.format_order(self.current_order_id)}. Would you like to check its status, cancellation options, or refund information?"
        
        # General query without order
        return self.llm.answer_question(msg)
    
    def format_order(self, order_id):
        """Format order ID for display."""
        oid = str(order_id or "").strip()
        if len(oid) == 8 and oid.isdigit():
            return f"{oid[:4]} {oid[4:]}"
        return oid

def main():
    """Interactive chat loop."""
    session = SimpleConversation()
    
    print("\nType your questions below. Commands:")
    print("  'quit' or 'exit' - Exit")
    print("  'reset' - Start new conversation")
    print("  'status' - Show current state")
    print()
    
    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Thank you for using ZentroMart support.")
                break
            
            if user_input.lower() == 'reset':
                session = SimpleConversation()
                print("✅ Conversation reset.")
                continue
            
            if user_input.lower() == 'status':
                print(f"\n📊 Status:")
                print(f"   Order ID: {session.current_order_id or 'None'}")
                print(f"   Verified: {session.order_verified}")
                print(f"   Ticket Created: {session.ticket_created}")
                if session.last_ticket_id:
                    print(f"   Last Ticket: {session.last_ticket_id}")
                continue
            
            response = session.process(user_input)
            print(f"\n🤖 Agent: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
