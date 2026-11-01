# VoiceOps 2026 — 2-Minute Software Demonstration Video Specification

This document details the exact scene breakdown, visual storyboards, and spoken narration scripts used to produce the official **1080p Capstone Demonstration Video (`demo.mp4`)** for the **ZentroMart AI Customer Support Agent**.

The final video strictly adheres to the official Capstone Brief requirements:
- **Duration:** 109.62 seconds (1 minute 49 seconds, strictly $\le$ 120 seconds).
- **Resolution:** 1920 × 1080 Full HD (H.264 video, AAC audio, 25 fps).
- **Visual Aesthetic:** Modern enterprise dark navy (`#0A0F1D`), blue, and white technology theme.
- **Audio:** Professional English narration (Windows SAPI) + subtle low-volume ambient background pad (-28 dB).
- **Real Project Artifacts:** Actual VS Code terminal execution, multi-turn PC002 dialogue, real Gnani TTS audio playback (`PC002_turn1_reply.wav`, `PC002_turn2_reply.wav`), and verifiable JSON outputs (`batch_summary.json`).

---

## Video Structure & Spoken Narration Script

### Scene 1: Project Introduction (0:00 – 0:14.5)
- **Title Banner:** `"VoiceOps 2026 – ZentroMart AI Customer Support Agent"`
- **Subtitle:** Consulting & Analytics Club, IIT Guwahati × Gnani.ai | Final Capstone Demonstration
- **Visual Display:** Enterprise mission overview, e-commerce support domain (orders, returns, refunds, SLAs), zero-hallucination mandate, and 4 capstone milestone cards (Steps 1–4).
- **Spoken Narration:**
  > *"Hello everyone. Today, I am presenting our VoiceOps 2026 capstone project, ZentroMart AI Customer Support Agent, an AI-powered voice-based customer support solution designed to automate customer interactions."*

---

### Scene 2: System Architecture (0:14.5 – 0:28.0)
- **Visual Display:** Codebase tree structure (`src/`: `voice_agent.py`, `conversation.py`, `rag_agent.py`, `knowledge_base.py`, `llm_agent.py`, `tools_adapter.py`) and side-by-side highlights of the 6 core components:
  1. **Gnani.ai Speech-to-Text (`src/voice_agent.py`)**
  2. **AI Conversation Management (`src/conversation.py`)**
  3. **Retrieval-Augmented Generation (`src/rag_agent.py`, `src/knowledge_base.py`)**
  4. **Customer Verification (`src/conversation.py`)**
  5. **Order Lookup (`src/tools_adapter.py`)**
  6. **Gnani.ai Text-to-Speech (`src/voice_agent.py`)**
- **Spoken Narration:**
  > *"The system combines speech recognition, intelligent conversation management, information retrieval, secure customer verification, and speech synthesis into one workflow."*

---

### Scene 3: Live Project Execution (0:28.0 – 0:47.5)
- **Visual Display:** VS Code integrated terminal running:
  `python run.py --input-dir ".\sample_audio" --output-dir ".\outputs"`
- **Verifiable Outputs Shown:**
  - 2 WAV files processed (`PC002_turn1.wav`, `PC002_turn2.wav`).
  - Gnani STT speech transcription.
  - Decision classification: `clarify` (Turn 1) and `answer` (Turn 2).
  - Gnani TTS synthesis output paths.
  - Batch summary metrics: 2 processed, 2 successful, 0 failed.
- **Spoken Narration:**
  > *"Here, we are processing customer audio recordings. The system first converts speech into text, understands the request, and generates an appropriate response."*

---

### Scene 4: Multi-turn Customer Conversation (0:47.5 – 1:07.0)
- **Visual Display:** Turn-by-turn dialogue inspection of real session PC002:
  - **Turn 1 (Order Ingestion & Security Challenge):**
    - Customer: *"hello i want to check my order status my order id is six nine five two zero eight six seven please confirm the order id before proceeding"*
    - AI Agent: *"I can help with order 6952 0867. For your security, provide either the last 4 digits of your registered phone number or your 6-digit delivery pincode."*
    - Security Action: Customer unverified; order status withheld; PII protected.
  - **Turn 2 (Identity Verification & Order Resolution):**
    - Customer: *"yes that is my correct order id the last four digits of my register phone number is zero one zero one please check my order status"*
    - AI Agent: *"Your order 6952 0867 is currently 'shipped'. Its promised delivery date is 2026-10-23."*
    - Security Action: Spoken numeral parsed (`"zero one zero one"` $\to$ `0101`); caller verified; order status unlocked.
- **Spoken Narration:**
  > *"The agent supports multi-turn conversations. It first requests verification before accessing order information. Once verification succeeds, it retrieves the relevant order details and responds to the customer."*

---

### Scene 5: Voice Response Demonstration (1:07.0 – 1:32.6)
- **Visual Display:** High-fidelity audio player cards with active multi-channel digital waveform visualizations and playback progress indicators.
- **Audio Track Playback Sequence:**
  1. Narration introduction (0.0s – 8.96s).
  2. **Real Audio Playback 1 (`sample_outputs/PC002_turn1_reply.wav`)**: 9.76s of actual Gnani TTS audio (Kaveri voice profile).
  3. 0.4s pause.
  4. **Real Audio Playback 2 (`sample_outputs/PC002_turn2_reply.wav`)**: 4.48s of actual Gnani TTS audio (Kaveri voice profile).
  5. 1.0s outro transition.
- **Spoken Narration:**
  > *"Using Gnani.ai Text-to-Speech, the system converts its responses into natural speech, creating a complete voice-based customer support experience."*

---

### Scene 6: Output Inspection & Conclusion (1:32.6 – 1:49.6)
- **Visual Display:**
  - Left: Syntax-highlighted actual JSON results from `sample_outputs/batch_summary.json` & `PC002_turn2_result.json`.
  - Right: Verified execution metrics dashboard:
    - WAV Files Processed: 2 / 2
    - Successful: 2 | Failed: 0
    - STT & TTS Processing: Completed Successfully
    - Step 2 RAG Evaluation: 52 / 52 (100% Evaluated Accuracy)
    - Automated Tests: 44 / 44 Passed (0 Failed)
  - Deliverables Checklist: `report.pdf` (4 pages), `demo.mp4` (1080p), `run.py`, `src/`, `tests/`.
- **Spoken Narration:**
  > *"This demonstration successfully processes two customer audio recordings, handles verification, retrieves order information, and generates voice responses. Thank you for watching our VoiceOps 2026 project demonstration."*

---

## Programmatic Video Reproduction

To regenerate `demo.mp4` programmatically at any time:
```cmd
python build_official_demo.py
```
This renders all 6 HD slides, synthesizes narration, mixes ambient music, and exports the final `demo.mp4`.
