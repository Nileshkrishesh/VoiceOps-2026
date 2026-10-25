"""Interactive CLI Chat with ZentroMart AI Customer Support Agent.

Usage:
    python chat.py
"""
import os
import sys
import warnings

# Suppress noisy TensorFlow and absl logs for clean CLI experience
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Handle UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.conversation import ConversationSession
from src.knowledge_base import KnowledgeBase

def main():
    print("=" * 65)
    print("  Welcome to ZentroMart AI Customer Support (Interactive Chat)")
    print("  Type your message below. Type 'exit' or 'quit' to end.")
    print("=" * 65)
    print("\nLoading Knowledge Base and Agent...")
    
    kb = KnowledgeBase()
    session = ConversationSession(conversation_id="interactive_user", kb=kb)
    
    print("Agent is ready!\n")
    
    # Initial greeting from agent
    initial_res = session.process_turn("Hello")
    print(f"ZentroMart AI: {initial_res['reply']}\n")

    while True:
        try:
            user_input = input("Customer: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nThank you for reaching out to ZentroMart Support. Have a great day!")
                break

            response = session.process_turn(user_input)
            
            # Print agent response
            print(f"\nZentroMart AI: {response['reply']}")
            
            # Optional debug information
            if response.get("tool_calls"):
                print(f"   [Tools Executed: {', '.join(response['tool_calls'])}]")
            if response.get("evidence"):
                print(f"   [Evidence Used: {', '.join(response['evidence'])}]")
            print()

        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat. Goodbye!")
            break

if __name__ == "__main__":
    main()
