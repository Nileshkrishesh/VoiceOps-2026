# VoiceOps 2026 — ZentroMart AI Customer Support Agent

An LLM-powered customer support agent built for the VoiceOps 2026 capstone by the Consulting & Analytics Club, IIT Guwahati × Gnani.ai.

**Repository:** [Nileshkrishesh/VoiceOps-2026](https://github.com/Nileshkrishesh/VoiceOps-2026)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/Tests-44%20Passed-brightgreen)
![RAG](https://img.shields.io/badge/RAG-FAISS-blueviolet)
![Voice](https://img.shields.io/badge/Voice-Gnani.ai-orange)

## 1. Project Overview

ZentroMart is a fictional Indian e-commerce company selling groceries and electronics. This project implements an AI customer support agent that answers customer questions, retrieves relevant company policies, handles multi-turn conversations, verifies customers before disclosing protected order information, and escalates cases requiring human intervention.

The system combines a configurable large language model (LLM), retrieval-augmented generation (RAG), mock order-management tools, and a speech pipeline designed to use Gnani.ai.

### Key Features

- **LLM-based responses:** Uses a configurable LLM provider; Gemini configuration is supported.
- **Document-grounded RAG:** Retrieves relevant policy and FAQ sections using FAISS-based vector search.
- **Multi-turn conversations:** Preserves context and handles follow-up questions.
- **Caller verification:** Requires an approved verification detail before disclosing protected order information.
- **Mock order management:** Supports order lookup and support-ticket creation.
- **Policy enforcement:** Handles cancellations, returns, refunds, compensation requests, and human escalation.
- **Voice integration:** Includes Gnani.ai speech-to-text (STT) and text-to-speech (TTS) integration.
- **Batch processing:** Includes a command-line runner for processing audio files and saving outputs.

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
RAG / FAISS              Order Tools
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
| Language | Python |
| LLM | Configurable provider; Gemini configuration supported |
| Retrieval | FAISS and embeddings |
| Knowledge base | Markdown policy and FAQ documents |
| Structured data | CSV files |
| Voice input/output | Gnani.ai STT/TTS integration |
| Testing | pytest |

## 3. Repository Structure

The exact files may vary by repository revision. Confirm that listed files are present before relying on optional artifacts.

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
- API credentials for the LLM provider and Gnani.ai when running live hosted services

### Step 1 — Clone the repository

```bash
git clone https://github.com/Nileshkrishesh/VoiceOps-2026.git
cd VoiceOps-2026
```

### Step 2 — Create and activate a virtual environment

**Windows CMD**

```cmd
python -m venv .venv
.venv\Scripts\activate
```

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

Copy the example file.

**Windows CMD**

```cmd
copy .env.example .env
```

**Linux/macOS**

```bash
cp .env.example .env
```

Edit `.env` and add your own credentials using the variable names supported by `.env.example` and `src/config.py`. The following is an example only; verify exact variable names and supported settings in the current code:

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

- Gemini credentials: [Google AI Studio](https://aistudio.google.com/)
- Gnani.ai credentials: [Gnani Voice](https://app.gnani.ai/voice)

**Security:** Never commit `.env`, real API keys, or private customer data to GitHub. `.env.example` must contain placeholder values only.

## 5. Running the Agent

### Batch audio processing

Check the actual supported command-line arguments first:

```bash
python run.py --help
```

If supported by the current runner, a batch run may look like:

```bash
python run.py --input-dir ./sample_audio --output-dir ./outputs
```

Use only flags reported by `--help`; optional TTS flags may differ by code version. Configure the required API credentials for live voice processing.

### Expected outputs

Depending on the implementation and API availability, the runner may produce:

- A JSON result for each input recording
- A recognized transcript
- The agent's text response
- A synthesized WAV reply
- Tool-call and retrieval evidence, where available
- A batch summary with processing status

Inspect the actual output files to confirm which stages completed successfully. A passing unit test or mocked batch test does not, by itself, prove that live speech APIs work end to end.

## 6. Knowledge Base and RAG

The RAG pipeline is designed to retrieve relevant document chunks before generating an answer:

1. Load policy and FAQ documents.
2. Split documents into searchable chunks.
3. Generate embeddings and index them in FAISS.
4. Retrieve relevant chunks for a question.
5. Use retrieved evidence to ground the response.
6. Abstain when available documents do not support an answer.

The intended policy precedence is:

**Current policies → Agent guides → Help articles → FAQs → Marketing material**

Superseded policy versions and historical support logs should not override authoritative current policies.

## 7. Conversation and Security

The conversation manager is designed to handle:

- Order ID collection and follow-up questions
- Caller verification before disclosure of protected order details
- Order status and policy-related questions
- Cancellation, return, and refund discussions
- Compensation refusals
- Human escalation and support-ticket creation
- Conversation context across consecutive turns

The agent should confirm a ticket or other action only after the corresponding tool reports success. Sensitive order information must not be disclosed to unverified callers.

## 8. Automated Tests

The following result was reported by a local test run on Python 3.13.7:

```text
44 passed, 3 warnings in 98.78s (0:01:38)
```

Run the test suite with:

```bash
python -m pytest -v
```

**Latest shared test result: 44 passed, 0 failed.** Three SWIG-related deprecation warnings were reported; they did not cause test failures.

### Test coverage

| Test module | Tests passed |
|---|---:|
| `test_business_days.py` | 12 |
| `test_conversation_fixes.py` | 7 |
| `test_evaluation_clarify.py` | 4 |
| `test_phase1_dataset.py` | 5 |
| `test_phase2_llm.py` | 4 |
| `test_phase3_step1_eval.py` | 1 |
| `test_phase4_rag.py` | 4 |
| `test_phase5_conversation.py` | 4 |
| `test_phase6_voice_and_runner.py` | 3 |
| **Total** | **44** |

The test-module counts above total 44. The terminal excerpt shared for review omitted the first few lines of output, so use the complete pytest output if you need to audit every individual test name.

## 9. Evaluation Results

The project benchmark compares the Step 1 baseline against the Step 2 RAG-grounded agent on 52 questions in `practice/questions.csv`.

The following figures were reported in the project's existing README and must be checked against the current evaluation CSV/report before submission.

| Metric | Step 1: Baseline | Step 2: Grounded RAG | Reported change |
|---|---:|---:|---:|
| Total questions | 52 | 52 | Same benchmark |
| Correct answers | 12/52 | 52/52 | +40 answers |
| Factual accuracy | 23.08% | 100.00% | +76.92 percentage points |
| Safe-claims adherence | 100.00% | 100.00% | No reported change |
| Abstention on unanswerable questions | 100.00% | 100.00% | No reported change |
| Clarification accuracy | N/A | 100.00% | Reported for Step 2 |

**Evaluation caveat:** The project notes that local offline runs may use the deterministic `_synthesize_grounded_answer` function when live API network access is unavailable. Such results must be labelled as offline deterministic evaluation, not live LLM performance. Verify the evaluation CSVs and run configuration before treating these figures as final benchmark results.

## 10. Voice Integration Status

The intended voice pipeline is:

1. Accept a customer audio file.
2. Transcribe it using Gnani.ai STT.
3. Send the recognized text to the conversation agent.
4. Generate a grounded text response.
5. Synthesize the response using Gnani.ai TTS.
6. Save the transcript, response, audio, and relevant metadata.

Use the language, voice, and model supported by your Gnani.ai account and installed SDK.

**Live verification status:** The shared test output confirms that the automated test suite passed, including a batch-runner test. It does **not** establish that a real audio file successfully passed through live Gnani.ai STT and TTS. Perform and record a real end-to-end run before claiming full live voice verification.

See [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md), if present, for the demonstration script. The submission demo should be no longer than two minutes and should show a document-grounded answer, a follow-up conversation, and a handover or appropriate “I don't know” response.

Do not substitute another speech provider if the capstone requires Gnani.ai exclusively.

## 11. Privacy and Responsible Use

- Use synthetic capstone customer data and only recordings you are permitted to use.
- Do not commit API keys, `.env` files, or private customer data.
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

