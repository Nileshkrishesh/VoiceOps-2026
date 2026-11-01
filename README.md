# VoiceOps 2026 — ZentroMart AI Customer Support Agent

An LLM-powered customer support agent built for the VoiceOps 2026 Capstone by the Consulting & Analytics Club, IIT Guwahati × Gnani.ai.

**Repository:** [Nileshkrishesh/VoiceOps-2026](https://github.com/Nileshkrishesh/VoiceOps-2026)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/Tests-44%20Passed-brightgreen)
![RAG](https://img.shields.io/badge/RAG-FAISS-blueviolet)
![Voice](https://img.shields.io/badge/Voice-Gnani.ai-orange)

---

## 1. Project Overview

ZentroMart is a fictional Indian e-commerce company selling groceries and electronics. This project implements an AI customer support agent that answers customer questions, retrieves relevant company policies, handles multi-turn conversations, verifies customers before disclosing protected order information, and escalates cases requiring human intervention.

The system combines a configurable large language model (LLM), retrieval-augmented generation (RAG), mock order-management tools, and a voice pipeline integrated with Gnani.ai.

### Key Features

- **LLM-based responses:** Configurable LLM provider with Gemini configuration support.
- **Document-grounded RAG:** Retrieves relevant policy and FAQ sections using FAISS-based vector search.
- **Multi-turn conversations:** Preserves context and handles follow-up questions.
- **Caller verification:** Requires an approved verification detail before disclosing protected order information.
- **Mock order management:** Supports order lookup and support-ticket creation.
- **Policy enforcement:** Handles cancellations, returns, refunds, compensation requests, and human escalation.
- **Voice integration:** Gnani.ai Speech-to-Text (STT) and Text-to-Speech (TTS).
- **Batch processing:** Processes audio recordings and saves structured outputs.

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
      +----------------------+
      |                      |
      v                      v
  RAG / FAISS            Order Tools
Policy Retrieval         Verification
                         Ticket Creation
      |                      |
      +----------+-----------+
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
| Programming Language | Python |
| LLM | Configurable provider; Gemini supported |
| Retrieval | FAISS and embeddings |
| Knowledge Base | Markdown policy and FAQ documents |
| Structured Data | CSV files |
| Voice Input/Output | Gnani.ai STT/TTS |
| Testing | pytest |

## 3. Repository Structure

The exact files may vary by repository revision.

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
├── tests/
├── sample_audio/
├── sample_outputs/
├── reports/
└── practice/
```

## 4. Installation and Setup

### Prerequisites

- Python 3.10 or later
- Git
- Internet access for hosted APIs
- API credentials for the LLM provider and Gnani.ai when using live services

### Step 1 — Clone the repository

```bash
git clone https://github.com/Nileshkrishesh/VoiceOps-2026.git
cd VoiceOps-2026
```

### Step 2 — Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**

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

Copy the example configuration:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**Linux/macOS**

```bash
cp .env.example .env
```

Edit `.env` and add your own credentials. Refer to `.env.example` and `src/config.py` for the supported variable names and settings.

Example configuration:

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

- Gemini credentials: https://aistudio.google.com/
- Gnani.ai credentials: https://app.gnani.ai/voice

**Security:** Never commit `.env`, real API keys, or private customer data to GitHub. `.env.example` must contain placeholder values only.

## 5. Running the Agent

### Batch Audio Processing

Check the supported command-line arguments:

```bash
python run.py --help
```

Run the batch processor:

```powershell
python run.py --input-dir ".\sample_audio" --output-dir ".\outputs"
```

The runner processes audio recordings and generates structured results.

### Expected Outputs

Depending on the implementation and API availability, outputs include:

- Recognized customer transcripts.
- AI-generated text responses.
- Synthesized WAV audio replies.
- Conversation decisions and tool-call metadata.
- Individual JSON result files.
- Batch processing summary.

Inspect the generated files in the output directory to confirm processing results.

## 6. Knowledge Base and RAG

The RAG pipeline retrieves relevant document chunks before generating an answer.

1. Load policy and FAQ documents.
2. Split documents into searchable chunks.
3. Generate embeddings and index them in FAISS.
4. Retrieve relevant chunks for a question.
5. Use retrieved evidence to ground the response.
6. Abstain when available documents do not support an answer.

The intended policy precedence is:

**Current policies → Agent guides → Help articles → FAQs → Marketing material**

Superseded policy versions and historical support logs should not override authoritative current policies.

## 7. Conversation Management and Security

The conversation manager is designed to handle:

- Order ID collection and follow-up questions.
- Caller verification before disclosing protected order details.
- Order status and policy-related questions.
- Cancellation, return, and refund discussions.
- Compensation refusals.
- Human escalation and support-ticket creation.
- Conversation context across consecutive turns.

The agent should confirm a ticket or other action only after the corresponding tool reports success. Sensitive order information must not be disclosed to unverified callers.

## 8. Automated Testing

The project test suite was executed locally using Python 3.13.7.

**Latest shared test result:**

```text
44 passed, 3 warnings in 98.78s
```

Run the tests using:

```bash
python -m pytest -v
```

### Test Coverage

| Test Module | Tests |
|---|---:|
| test_business_days.py | 12 |
| test_conversation_fixes.py | 7 |
| test_evaluation_clarify.py | 4 |
| test_phase1_dataset.py | 5 |
| test_phase2_llm.py | 4 |
| test_phase3_step1_eval.py | 1 |
| test_phase4_rag.py | 4 |
| test_phase5_conversation.py | 4 |
| test_phase6_voice_and_runner.py | 3 |
| **Total** | **44** |

Three SWIG-related deprecation warnings were reported. They did not cause test failures.

## 9. Evaluation Results

The project benchmark compares the Step 1 baseline against the Step 2 RAG-grounded agent on 52 questions in `practice/questions.csv`.

The reported evaluation figures are:

| Metric | Step 1: Baseline | Step 2: Grounded RAG |
|---|---:|---:|
| Total Questions | 52 | 52 |
| Correct Answers | 12/52 | 52/52 |
| Factual Accuracy | 23.08% | 100.00% |
| Safe-Claims Adherence | 100.00% | 100.00% |
| Abstention on Unanswerable Questions | 100.00% | 100.00% |
| Clarification Accuracy | N/A | 100.00% |

**Evaluation caveat:** Local offline runs may use the deterministic `_synthesize_grounded_answer` function when live API network access is unavailable. These results should be labelled as offline deterministic evaluation, not pure live LLM performance. Verify the evaluation CSVs and run configuration before treating the figures as final benchmark results.

## 10. Voice Integration and Live Verification

The project integrates Gnani.ai for speech processing.

### Voice Pipeline

1. Accept a customer audio file.
2. Transcribe it using Gnani.ai STT.
3. Send the recognized text to the conversation agent.
4. Generate a response.
5. Synthesize the response using Gnani.ai TTS.
6. Save the transcript, response, audio, and relevant metadata.

### Live Voice Test — 1 November 2026

A real batch-processing run was successfully completed using two WAV audio files from `sample_audio`.

**Command executed:**

```powershell
python run.py --input-dir ".\sample_audio" --output-dir ".\outputs"
```

**Observed results:**

| Metric | Result |
|---|---|
| WAV files processed | 2 |
| Successful | 2 |
| Failed | 0 |
| STT Language | en-IN |
| TTS Model | timbre-v2.5 |
| TTS Voice | Kaveri |
| Processing time | 18.81 seconds |

### Demonstrated Conversation

**Turn 1 — Customer Request**

The customer requests an order-status update and provides an order ID.

- Gnani.ai STT successfully transcribes the audio.
- The agent identifies the order-status request.
- The conversation manager requests customer verification.
- Decision: `clarify`.

**Turn 2 — Customer Verification**

The customer provides the requested verification information.

- Gnani.ai STT successfully transcribes the second audio.
- The verification workflow completes.
- The order lookup tool is called.
- The agent generates an order-status response.
- Decision: `answer`.

Gnani.ai TTS successfully synthesizes both responses into WAV audio files.

### Generated Output Files

The successful run produced:

```text
outputs/
├── batch_summary.json
├── PC002_turn1_reply.wav
├── PC002_turn1_result.json
├── PC002_turn2_reply.wav
├── PC002_turn2_result.json
└── ...
```

The batch summary reported two successful recordings and zero failures.

**Verification scope:** This live test confirms successful STT and TTS API calls, two-turn audio processing, customer verification flow, order lookup execution, and generation of audio and JSON outputs. It does not independently establish that every RAG, ticket-creation, human-handover, or unsupported-question scenario has been verified through live execution.

**Sample-data note:** The sample order response contained a promised delivery date of 23 October 2026. Treat this as sample dataset information, not a current real-world delivery commitment.

The submission demonstration should be no longer than two minutes and should show the actual application execution and outputs. Where possible, demonstrate a document-grounded answer, follow-up conversation, and a handover or appropriate "I don't know" response.

## 11. Privacy and Responsible Use

- Use synthetic capstone customer data and only recordings you are permitted to use.
- Never commit API keys, `.env` files, or private customer data.
- Verify callers before revealing protected order information.
- Do not invent order statuses, refunds, compensation, ticket IDs, or policy details.
- Escalate cases requiring human review.
- Preserve relevant evidence so responses can be evaluated and debugged.

## 12. Future Improvements

- Improve accuracy on unseen questions.
- Expand multilingual testing for Indian languages and Hinglish.
- Evaluate live STT/TTS reliability and audio quality.
- Improve recovery from unclear or empty audio.
- Add regression tests for edge cases.
- Improve retrieval evidence and response traceability.
- Document reproducible benchmark results and live voice demonstrations.

## 13. Author and Project

**Project:** VoiceOps 2026 — ZentroMart AI Customer Support Agent

**GitHub:** [Nileshkrishesh](https://github.com/Nileshkrishesh)

**Repository:** [VoiceOps-2026](https://github.com/Nileshkrishesh/VoiceOps-2026)

Built as a capstone project focused on LLMs, RAG, conversational AI, and voice-enabled customer support.

---

*VoiceOps 2026 — Intelligence that truly listens.*
