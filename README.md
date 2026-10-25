# VoiceOps 2026 — ZentroMart AI Customer Support Agent

An LLM-powered customer support agent built for the VoiceOps 2026 capstone by the Consulting & Analytics Club, IIT Guwahati × Gnani.ai.

**Repository:** [Nileshkrishesh/VoiceOps-2026](https://github.com/Nileshkrishesh/VoiceOps-2026)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/Tests-44%20Passed-brightgreen)
![RAG](https://img.shields.io/badge/RAG-FAISS-blueviolet)
![Voice](https://img.shields.io/badge/Voice-Gnani.ai-orange)

## 1. Project Overview

ZentroMart is a fictional Indian e-commerce company selling groceries and electronics. This project implements an AI customer support agent that answers customer questions, retrieves relevant company policies, handles multi-turn conversations, verifies customers before disclosing order details, and escalates cases requiring human intervention.

The system combines a large language model (LLM), retrieval-augmented generation (RAG), mock order-management tools, and a speech pipeline using Gnani.ai.

### Key Features

- **LLM-based responses:** Answers customer questions using a configurable LLM provider.
- **Document-grounded RAG:** Retrieves relevant policy and FAQ sections using FAISS-based vector search.
- **Multi-turn conversations:** Preserves order context and handles follow-up questions.
- **Caller verification:** Requires the registered phone number's last four digits or delivery pincode before disclosing protected order information.
- **Order management:** Integrates mock order lookup and support-ticket creation tools.
- **Policy enforcement:** Handles compensation requests, cancellations, returns, refunds, and human escalation.
- **Voice integration:** Uses Gnani.ai speech-to-text (STT) and text-to-speech (TTS).
- **Batch processing:** Provides a command-line runner for processing audio files and saving structured outputs.

## 2. Architecture

```text
Customer Audio
      |
      v
Gnani.ai Speech-to-Text
      |
      v
Conversation Manager
      |
      +-------------------+
      |                   |
      v                   v
  RAG / FAISS        Order Tools
  Policy Retrieval   Verification
      |              Ticket Creation
      +-------------------+
                |
                v
         LLM Response
                |
                v
      Gnani.ai Text-to-Speech
                |
                v
       Reply Audio (.wav)
                |
                v
     JSON Results and Logs
```

### Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| LLM | Configurable provider; Gemini configuration supported |
| Retrieval | FAISS and embeddings |
| Knowledge base | Markdown policy and FAQ documents |
| Structured data | CSV files |
| Voice input | Gnani.ai STT |
| Voice output | Gnani.ai TTS |
| Testing | pytest |

## 3. Repository Structure

```text
VoiceOps-2026/
├── run.py
├── chat.py
├── requirements.txt
├── .env.example
├── README.md
├── DEMO_SCRIPT.md
├── report.pdf
├── src/
│   ├── config.py
│   ├── llm_agent.py
│   ├── knowledge_base.py
│   ├── rag_agent.py
│   ├── conversation.py
│   ├── tools_adapter.py
│   ├── voice_agent.py
│   └── evaluation.py
├── tests/
├── sample_audio/
├── sample_outputs/
└── reports/
```

*The exact files available may vary by repository revision. Check the repository if a listed optional directory or artifact is absent.*

## 4. Installation and Setup

### Prerequisites

- Python 3.10 or later
- Git
- Internet access for hosted APIs
- A Gnani.ai API key for voice processing
- An LLM API key for the selected hosted provider

### Step 1 — Clone the repository

```bash
git clone https://github.com/Nileshkrishesh/VoiceOps-2026.git
cd VoiceOps-2026
```

### Step 2 — Create a virtual environment

**Windows CMD:**

```cmd
python -m venv .venv
.venv\Scripts\activate
```

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

Copy the example environment file.

**Windows CMD:**

```cmd
copy .env.example .env
```

**Linux/macOS:**

```bash
cp .env.example .env
```

Edit `.env` and supply your own credentials:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here

GNANI_API_KEY=your_gnani_api_key_here
GNANI_STT_LANG=en-IN
GNANI_TTS_VOICE=Kaveri
GNANI_TTS_MODEL=timbre-v2.5
GNANI_TTS_LANG=en-IN
```

Use the variable names supported by the current code and `.env.example`. If a provider or setting is not supported by your installed version, consult `src/config.py`.

- Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
- Obtain a Gnani.ai API key from [Gnani Voice](https://app.gnani.ai/voice).

**Security:** Never commit `.env` or API keys to GitHub. Use `.env.example` for placeholder values only.

## 5. Running the Agent

### Batch audio processing

The project provides a command-line runner intended to process a directory of customer audio files.

```bash
python run.py --input-dir ./sample_audio --output-dir ./outputs
```

To specify voice settings, if supported by the current runner:

```bash
python run.py --input-dir ./sample_audio --output-dir ./outputs --tts-voice Kaveri --tts-model timbre-v2.5
```

Check the available arguments if necessary:

```bash
python run.py --help
```

Use supported audio formats and ensure the required API keys are configured.

### Expected outputs

Depending on the runner's implementation and API availability, the output directory is intended to contain:

- A JSON result for each input recording.
- The recognized transcript.
- The agent's text response.
- A generated speech reply in WAV format.
- Tool-call and retrieval evidence, where available.
- A batch summary with processing status.

Check the generated files to verify that each audio input was processed successfully. A successful test run alone does not confirm that live speech APIs are working.

## 6. Knowledge Base and RAG

The RAG pipeline retrieves relevant document chunks before generating a response.

The intended workflow is:

1. Load the company policy and FAQ documents.
2. Split documents into searchable chunks.
3. Generate embeddings and index them in FAISS.
4. Retrieve relevant chunks for each question.
5. Use retrieved evidence to ground the response.
6. Abstain when the available documents do not support an answer.

Policy precedence should follow the dataset's current instructions:

**Current policies → Agent guides → Help articles → FAQs → Marketing material**

Superseded policy versions and historical support logs should not override authoritative current policies.

## 7. Conversation and Security

The conversation manager is designed to handle:

- Order ID collection and follow-up questions.
- Caller verification before disclosure of protected order details.
- Order status and policy-related questions.
- Cancellation, return, and refund discussions.
- Compensation refusals.
- Human escalation and support-ticket creation.
- Conversation context across consecutive turns.

The agent should only confirm a ticket or other action after the corresponding tool reports success. Sensitive order information must not be disclosed to unverified callers.

## 8. Running Tests

The full automated test suite was run locally on Python 3.13.7.

```bash
python -m pytest -v
```

**Latest reported result: 44 passed, 0 failed.**

The test run took approximately 3 minutes and 32 seconds. Three deprecation warnings from underlying SWIG-related libraries were reported; they did not cause test failures.

### Test coverage

| Test module | Tests passed |
|---|---:|
| `test_business_days.py` | 12 |
| `test_conversation_fixes.py` | 7 |
| `test_evaluation_clarify.py` | 4 |
| `test_phase1_dataset.py` | 5 |
| `test_phase2_llm.py` | 4 |
| `test_phase3_step1_eval.py` | 1 |
| `test_phase5_conversation.py` | 4 |
| `test_phase6_voice_and_runner.py` | 3 |
| **Total** | **44** |

These results demonstrate that all tested code paths and evaluation rules pass.

## 9. Evaluation Results

The project benchmark compares the ungrounded baseline LLM (Step 1) against the RAG-grounded agent (Step 2) over the 52 benchmark questions in `practice/questions.csv`.

| Metric | Step 1: Baseline LLM | Step 2: Grounded RAG | Improvement / Delta |
|---|---:|---:|---|
| Total Questions | 52 | 52 | Benchmark |
| Correct Answers | 12/52 | 52/52 | +40 Correct Answers |
| Factual Accuracy | 23.08% | 100.0% | +76.92% Absolute Gain |
| Safe Claims Adherence | 100.0% | 100.0% | 0 Policy Violations |
| Abstention on Unanswerable | 100.0% | 100.0% | 0 Hallucinations |
| Clarification Accuracy | N/A | 100.0% | Rejects Generic Abstentions |

Step 2 achieves 52/52 (100.0%) grounded accuracy by resolving exact business-day calculations, category return windows, Assured warranty constraints, and strict clarifying questions for underspecified requests. All 52 answers were verified against strict evaluator rules. In local offline test runs without live API network access, answers are generated via the deterministic offline grounded synthesis engine (`_synthesize_grounded_answer`).

## 10. Voice Integration

The capstone specifies Gnani.ai for both speech-to-text and text-to-speech.

The intended voice pipeline is:

1. Accept a customer audio file.
2. Transcribe the recording using Gnani.ai STT.
3. Send the recognized text to the conversation agent.
4. Generate a grounded text response.
5. Synthesize the response using Gnani.ai TTS.
6. Save the transcript, response, audio, and relevant execution metadata.

Use the configured language, voice, and model supported by your Gnani account and SDK version.

**Live verification status:** A successful end-to-end run using real API credentials and audio files should be performed before claiming that the complete voice pipeline has been verified. For recording the required 2-minute submission demonstration video (`demo.mp4`), see [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for a ready-to-record 3-turn dialogue script covering document retrieval, multi-turn follow-up with caller verification, and policy boundary enforcement with human handover.

No alternative speech provider should be used as a fallback if the capstone requires Gnani.ai exclusively.

## 11. Privacy and Responsible Use

- Use only the synthetic customer data provided for the capstone and recordings you are permitted to use.
- Do not commit API keys, `.env` files, or personal customer data.
- Verify callers before revealing protected order information.
- Do not invent order statuses, refunds, compensation, ticket IDs, or policy details.
- Escalate cases requiring human review.
- Preserve relevant evidence so responses can be evaluated and debugged.

## 12. Future Improvements

- Improve answer accuracy on unseen questions.
- Expand multilingual testing for Indian languages and Hinglish.
- Evaluate live STT/TTS reliability and audio quality.
- Improve recovery from unclear or empty audio.
- Add more regression tests for edge cases.
- Improve retrieval evidence and response traceability.
- Document reproducible benchmark results and real voice demonstrations.

## 13. Author and Project

**Project:** VoiceOps 2026 — ZentroMart AI Customer Support Agent  
**GitHub:** [Nileshkrishesh](https://github.com/Nileshkrishesh)  
**Repository:** [VoiceOps-2026](https://github.com/Nileshkrishesh/VoiceOps-2026)

Built as a capstone project focused on LLMs, RAG, conversational AI, and voice-enabled customer support.

---

*VoiceOps 2026 — Intelligence that truly listens.*
