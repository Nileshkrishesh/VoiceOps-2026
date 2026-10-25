# VoiceOps 2026 — 2-Minute Demonstration Recording Script

This script provides exact instructions and spoken lines for recording the required 2-minute demonstration video (`demo.mp4`) showcasing the **ZentroMart AI Customer Support Agent**.

---

## 1. Video Recording Setup (Under 2 Minutes)

- **Recording Tool:**
  - **Windows:** Press `Win + Alt + R` (Windows Game Bar screen recorder) or use [OBS Studio](https://obsproject.com/).
  - **Mac/Linux:** Use QuickTime Player or OBS Studio.
- **Audio:** Microphone active for customer voice; desktop audio active for Kaveri's TTS voice (or CLI display).
- **Command to run in terminal:**
  ```cmd
  cd "C:\Users\Nilesh gupta\.gemini\antigravity\scratch\voiceops2026"
  python chat.py
  ```

---

## 2. Demonstration Dialogue (3 Multi-Turn Steps)

### Step 1: Policy Question Answered from Company Documents (0:00 - 0:35)
*Goal: Show accurate RAG policy retrieval and clear synthesized voice output.*

- **Customer:**
  > *"SoundPulse Neckband wapas bhejna hai, kitne din bache hain?"*  
  *(or English: "I want to return the SoundPulse Neckband, what is the return window?")*
- **ZentroMart AI (Audio & Text):**
  > *"Electronics have a 7-day return window from delivery (10 days if delivered before 1 August 2026)."*
- **Evidence / Policy Grounded:** `kb/pol_returns_v4.md` (Section `[RET-2]`).

---

### Step 2: Multi-Turn Order Follow-Up with Security Gating (0:35 - 1:15)
*Goal: Show contextual memory across turns, caller security challenge, and order status unlocking.*

- **Customer:**
  > *"Mera order check karo, Order ID 69520867 hai."*  
  *(or English: "Can you check my order? My Order ID is 69520867.")*
- **ZentroMart AI:**
  > *"I can help with order 6952 0867. For your security, provide either the last 4 digits of your registered phone number or your 6-digit delivery pincode."*  
  *(Tool Executed: `lookup_order(69520867)` — order details masked)*
- **Customer (Spoken Numeral Verification):**
  > *"My registered number ends with zero one zero one."*
- **ZentroMart AI:**
  > *"Your order 6952 0867 is currently 'shipped'. Its promised delivery date is 2026-10-23."*  
  *(Tool Executed: `lookup_order(69520867, verification_value=0101)` — verified)*

---

### Step 3: Polite Policy Refusal & Human Handover / Escalation (1:15 - 1:50)
*Goal: Show strict policy boundary enforcement (no cash compensation) and automatic ticket dispatch to human support.*

- **Customer:**
  > *"My order is delayed. I want ₹500 cash compensation right now."*
- **ZentroMart AI:**
  > *"Direct cash compensation cannot be provided under ZentroMart company policy. However, I have created a support ticket and will connect you with a senior support representative."*  
  *(Tool Executed: `create_ticket(summary="Customer requested compensation for delayed order 69520867")`)*
- **Customer:**
  > *"Thank you, that's fine."*
- **ZentroMart AI:**
  > *"Thank you for calling ZentroMart. Have a wonderful day!"*

---

## 3. Saving & Submitting the Video

1. Save the recorded file as **`demo.mp4`** in the project root.
2. Check that the duration is $\le$ 120 seconds (2 minutes).
3. Confirm that audio is clear and video shows the agent processing the 3 turns.
