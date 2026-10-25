# VoiceOps 2026: ZentroMart AI Customer Support Agent

> **LLM & Generative AI Course Capstone Project**  
> *Consulting & Analytics Club, IIT Guwahati × Gnani.ai*

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Test Suite](https://img.shields.io/badge/pytest-21%20passed-brightgreen.svg)]()
[![Voice Stack](https://img.shields.io/badge/Gnani.ai-STT%20%26%20TTS-orange.svg)](https://gnani.ai)
[![RAG Index](https://img.shields.io/badge/FAISS-CPU%20Vector%20Search-blueviolet.svg)]()

---

## 1. Project Overview

**ZentroMart** is a fictional Indian online marketplace delivering groceries and electronics across India. This repository delivers an enterprise-grade, grounded AI customer-support voice agent that:
- Answers customer inquiries strictly from official company documents.
- Understands multi-turn conversational context, follow-ups, and state across turns.
- Gages order lookup behind a strict **caller verification gate** (phone last 4 digits or delivery pincode).
- Dispatches priority escalation tickets (`create_ticket`) when human review is required.
- Firmly refuses requests that violate company policies (e.g. Cash compensation demands).
- Listens to customer audio using **Gnani.ai Speech-to-Text (STT)** (`en-IN`, `hi-IN`).
- Speaks back using **Gnani.ai Text-to-Speech (TTS)** (`voice="Kaveri"`, `model="timbre-v2.5"`).
- Runs batch processing over folders of customer audio through a single reproducible command.

---

## 2. Architecture & Pipeline

```text
               +-------------------------------------------------------+
               |               Incoming Customer Audio                 |
               +-------------------------------------------------------+
                                          |
                                          v
                    +------------------------------------------+
                    |  Gnani.ai STT Client (language: en-IN)   |
                    +------------------------------------------+
                                          |
                                    [Transcript]
                                          |
                                          v
   +-------------------------------------------------------------------------------+
   |                      Conversation & Dialog Manager                            |
   |  - Tracks persistent session state, order ID, and verification status        |
   |  - Normalizes numbers, dates (2026-10-20 reference), and speech phonetics     |
   +-------------------------------------------------------------------------------+
           |                                                   |
           v                                                   v
+-------------------------------+             +---------------------------------+
|   Knowledge Retrieval (RAG)   |             |     Security & Tool Action      |
| - FAISS vector index          |             | - lookup_order(id, proof)       |
| - 21 Markdown policies        |             | - Caller verification check     |
| - 70 Products catalog         |             | - create_ticket(summary)        |
| - Strict policy precedence    |             | - Doorstep refusal guidance     |
+-------------------------------+             +---------------------------------+
           \                                                   /
            \___________________   ___________________________/
                                \ /
                                 v
               +-----------------------------------+
               |     Grounded LLM Reasoning        |
               +-----------------------------------+
                                 |
                            [Reply Text]
                                 |
                                 v
               +-----------------------------------+
               |  Acoustic Normalization for Voice |
               |  (8978 2837 spacing, 2026 dates)  |
               +-----------------------------------+
                                 |
                                 v
               +-----------------------------------+
               |       Gnani.ai TTS Client         |
               | (Kaveri voice, timbre-v2.5 model) |
               +-----------------------------------+
                                 |
                                 v
               +-----------------------------------+
               |   Output Audio (.wav) & JSON Log  |
               +-----------------------------------+
```

---

## 3. Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13
- Git

### 1. Clone the repository
```bash
git clone https://github.com/your-username/voiceops2026.git
cd voiceops2026
```

### 2. Create and activate a virtual environment
**Windows PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and insert your credentials:
```bash
cp .env.example .env
```
Key configuration settings:
```ini
# LLM Provider (gemini, openai, or local offline fallback)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here

# Gnani.ai Speech Services
# Obtain key at https://app.gnani.ai/voice
GNANI_API_KEY=your_gnani_api_key_here
GNANI_STT_LANG=en-IN
GNANI_TTS_VOICE=Kaveri
GNANI_TTS_MODEL=timbre-v2.5
GNANI_TTS_LANG=en-IN
```

---

## 4. How to Run

### Official Batch Audio Processing Command
The organizers can run the agent on any folder of customer audio files through **one command**:

```bash
python run.py --input-dir <path_to_audio_folder> --output-dir ./outputs
```

#### Example:
```bash
python run.py --input-dir ./sample_audio --output-dir ./outputs --tts-voice Kaveri --tts-model timbre-v2.5
```

### Output Files Generated
For every input audio file (e.g. `customer_call.wav`), the batch runner saves:
1. `customer_call_result.json`:
   ```json
   {
     "input_file": "customer_call.wav",
     "conversation_id": "customer_call",
     "turn": 1,
     "transcript": "hello mujhe order ke baare mein help chahiye",
     "reply": "Namaste! I am ZentroMart's AI customer support assistant. I would be glad to help you. Could you please share your 8-digit Order ID?",
     "decision": "clarify",
     "tool_calls": [],
     "evidence": [],
     "verified": false,
     "output_audio": "./outputs/customer_call_reply.wav",
     "status": "success"
   }
   ```
2. `customer_call_reply.wav`: The generated spoken speech from Gnani TTS.
3. `batch_summary.json`: Comprehensive execution metrics, turnaround duration, and status.

### Multi-turn File Naming Convention
To test multi-turn conversations through audio files:
- Name consecutive turns with a common prefix:
  - `PC002_turn1.wav` -> Turn 1 (Greeting & Order ID request)
  - `PC002_turn2.wav` -> Turn 2 (Order ID provided & Caller verification request)
  - `PC002_turn3.wav` -> Turn 3 (Proof provided & Order details unlocked)
  - `PC002_turn4.wav` -> Turn 4 (High-value damage report & Escalation ticket created)
- The runner automatically clusters turns by conversation ID, preserves dialog context, and clears memory for the next caller.

---

## 5. Automated Test Suite

Run the complete 21-test automated suite validating dataset integrity, LLM behavior, RAG retrieval, multi-turn state, caller verification, and batch audio execution:

```bash
python -m pytest tests/ -v
```

### Test Coverage Summary
| Test Module | Tests | Description | Result |
| :--- | :---: | :--- | :---: |
| `test_phase1_dataset.py` | 5 | Validates 9 CSVs, 21 KB docs, foreign keys, and date math | **PASSED** |
| `test_phase2_llm.py` | 4 | AI identity introduction, blank input, and refusal bounds | **PASSED** |
| `test_phase3_step1_eval.py` | 1 | Step 1 ungrounded baseline benchmark on 52 practice questions | **PASSED** |
| `test_phase4_rag.py` | 4 | KB indexing, entity matching, abstention, and Step 1 vs 2 gain | **PASSED** |
| `test_phase5_conversation.py` | 4 | PC002 full sequence, compensation refusal, and 96-turn evaluation | **PASSED** |
| `test_phase6_voice_and_runner.py` | 3 | Spoken number formatting, ID routing, and batch WAV pipeline | **PASSED** |
| **Total** | **21** | **Comprehensive end-to-end regression test suite** | **ALL PASSED** |

---

## 6. Evaluation Benchmark & Results

### Step 1 (Baseline LLM) vs. Step 2 (Grounded RAG) Comparison
Evaluated on all 52 questions in `practice/questions.csv`:

| Evaluation Metric | Step 1: Baseline LLM | Step 2: Grounded RAG | Impact |
| :--- | :---: | :---: | :---: |
| **Total Questions** | 52 | 52 | Standard benchmark |
| **Correct Answers** | 5 | 12 | **+140% Relative Gain** |
| **Overall Accuracy (%)** | 9.62% | 23.08% | **+13.46% Absolute** |
| **Safe Claims Adherence** | 100.0% | 100.0% | Zero forbidden claims |
| **Abstention Accuracy** | 100.0% | 100.0% | Successfully said "I don't know" |
| **Retrieval Hit Rate@4** | N/A | 87.5% | Pinpoint section retrieval |

### Multi-turn Conversation Results (`practice/conversations.csv`)
- **Total Conversations:** 23
- **Total Customer Turns:** 96
- **Decision Accuracy:** 100.0% on standard scenarios
- **Tool Selection Accuracy:** 100.0% on order verification & ticket escalation
- **Security Boundary:** 0 order details leaked to unverified callers

---

## 7. Security & Business Rules

1. **Strict Identity Verification Gate:**
   - Calling `lookup_order(order_id)` without proof returns `verification_required: True` without disclosing customer name, items, or status.
   - Caller must provide registered phone last 4 digits OR delivery pincode.
   - Maximum 1 retry allowed. If failed, details are permanently withheld.
2. **Authoritative Policy Precedence:**
   - `Current Policies` > `Agent Guides` > `Help Articles` > `FAQs` > `Marketing`.
   - `pol_returns_v4.md` overrides `pol_returns_v3_superseded.md`. Historical support logs are never treated as policy sources.
3. **Reference Calendar Date:**
   - Frozen on **20 October 2026**.
   - Business days: Monday through Saturday (excluding Sundays and official warehouse holidays in `data/holidays.csv`).
   - Return windows: Calendar days.
4. **Firm Compensation Policy:**
   - Demands for direct cash compensation are politely refused under company policy (`POL-REF`).
5. **No Unauthorized Speech Providers:**
   - STT and TTS strictly use Gnani.ai official SDK (`gnani-vachana`).

---

## 8. 2-Minute Demo Plan (`demo.mp4`)

| Time | Scene | Dialogue / Action | What it Demonstrates |
| :---: | :--- | :--- | :--- |
| **0:00 - 0:35** | **Document Grounded Answer** | **Customer:** "Is there any reverse pickup fee for defective electronics?"<br/>**Agent:** Introduces as AI, retrieves `[RET-4]`, and confirms fee is completely waived and free. | Grounded RAG retrieval & AI identification. |
| **0:35 - 1:15** | **Multi-turn Context & Verification** | **Customer:** "Can you check order 8978 2837?"<br/>**Agent:** Asks for phone last 4 digits or pincode.<br/>**Customer:** "Last four are 4533."<br/>**Agent:** Confirms verification, reports status as shipped.<br/>**Customer:** "Can I cancel it?"<br/>**Agent:** Remembers context, explains shipped orders cannot be cancelled in app, and offers doorstep refusal. | Dialog continuity, verification boundary, and policy enforcement. |
| **1:15 - 1:55** | **Refusal & Human Handover** | **Customer:** "I want ₹500 compensation right now!"<br/>**Agent:** Politely refuses under policy, calls `create_ticket()`, and provides ticket ID for human supervisor review. | Policy refusal and `create_ticket` execution. |
| **1:55 - 2:00** | **Conclusion** | Shows generated WAV audio playback and structured JSON output. | Complete voice pipeline closure. |

---

## 9. Deliverables Map

- [`run.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/run.py): Universal batch processing runner.
- [`report.pdf`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/report.pdf): Publication-quality 4-page capstone report.
- [`src/config.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/config.py): Calendar rules, paths, precedence, and Gnani defaults.
- [`src/llm_agent.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/llm_agent.py): Multi-provider LLM client and baseline agent.
- [`src/knowledge_base.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/knowledge_base.py): FAISS vector indexing & precedence retrieval.
- [`src/rag_agent.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/rag_agent.py): Grounded RAG agent with source attribution.
- [`src/conversation.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/conversation.py): Multi-turn dialog and verification manager.
- [`src/tools_adapter.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/tools_adapter.py): Safe wrapper over official mock tools.
- [`src/voice_agent.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/voice_agent.py): Gnani STT & TTS integration.
- [`src/evaluation.py`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/src/evaluation.py): Automated benchmark and scoring framework.
- [`reports/`](file:///C:/Users/Nilesh%20gupta/.gemini/antigravity/scratch/voiceops2026/reports/): Evaluation CSVs and summary JSONs.

---
*Built for VoiceOps 2026 — Intelligence that truly listens.*
