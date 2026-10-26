# PulseCare AI Chatbot - Step 0 Exploration & Integration Report

## 1. System Overview & Repository Context
PulseCare is a Smart Healthcare Appointment & Triage System. The technology stack consists of:
- **Frontend**: React 18+, TypeScript, Tailwind CSS
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL (with local SQLite compatibility for testing and self-contained environments)
- **AI / Agentic Workflow**: LangGraph, LangChain, SentenceTransformers / LLM embeddings

## 2. Existing System Architecture (What Exists & What We Reuse)
The core PulseCare application provides:
1. **Authentication & Session Handling**:
   - JWT-based authentication (`/api/auth/login`, `/api/auth/register`, `/api/auth/me`).
   - Role-Based Access Control (`UserRole`: `PATIENT`, `DOCTOR`, `ADMIN`).
   - Reusable FastAPI dependencies: `get_current_user`, `get_current_patient`, `get_current_doctor`, and `get_optional_current_user`.
2. **Clinical & Administrative Data Layers**:
   - **Users & Doctors**: `User` and `Doctor` models providing profile, specialty, qualifications, consultation fees, and schedule availability.
   - **Appointments**: `Appointment` model linking patients and doctors with status (`scheduled`, `completed`, `cancelled`), notes, and symptoms.
   - **Medical Services**: `MedicalService` model listing hospital departments, clinical services, duration, and pricing.
   - **Medicines & Catalog**: `Medicine` model covering generic and brand names, indications, standard dosage precautions, contraindications, and prescription status.
3. **AI Triage Workflow (`/api/triage/assess`)**:
   - The established clinical triage endpoint assessing patient-described symptoms into emergency, urgent, non-urgent, and self-care categories.
   - **Strict integration rule**: The chatbot does NOT re-implement clinical triage; it hands off symptom assessment requests to this existing engine via the `handoff_to_triage` tool.

## 3. What We Are Adding (Chatbot Isolated Module)
The AI Chatbot is built as an isolated, modular sub-system:
1. **Isolated Backend (`backend/app/chatbot/`)**:
   - **Graph Architecture (`backend/app/chatbot/graph/`)**: A 10-node LangGraph state machine:
     1. `input_guard`: Prompt injection detection, PII masking, token limits.
     2. `emergency_detector`: Rule-based emergency keyword regex + fast confirmation, triggering immediate life-safety guidance.
     3. `query_understanding`: Sliding-window conversational resolution, entity extraction, standalone query rewriting.
     4. `router`: Multi-route classifier (`website_help`, `doctor_service_lookup`, `medicine_info`, `health_general`, `personal_data`, `triage_handoff`, `direct_llm`, `out_of_scope`). Supports parallel route merging.
     5. `retriever`: Advanced hybrid retrieval (dense vector search + BM25/FTS text search fused via Reciprocal Rank Fusion, with cross-encoder reranking).
     6. `tool_executor`: Parameterized, read-only tools executing doctor lookups, service lists, user-authenticated appointment retrieval, medicine information, and triage handoff.
     7. `document_grader`: Corrective RAG (CRAG) evaluating chunk relevance with an automated rewrite loop (max 2 attempts).
     8. `answer_generator`: Synthesis strictly grounded on retrieved documentation and tool outputs.
     9. `grounding_verifier`: Claim-by-claim verification of factual claims against retrieved evidence, returning a polite refusal if ungrounded.
     10. `safety_postprocessor`: Medical non-prescriptive disclaimers, info badges (`Verified from PulseCare data` vs `General Information`), citation attachment, and internal PII scrubbing.
   - **Memory System (`backend/app/chatbot/memory/`)**: PostgreSQL-backed persistent sessions and messages with sliding-window context and turn summarization.
   - **Data Models & Migrations (`backend/app/models/chatbot.py`)**:
     - `ChatSession`: User or guest conversation thread.
     - `ChatMessage`: Individual turn with citations, info badges, and metadata.
     - `ChatFeedback`: Thumbs up/down rating and audit commentary.
     - `KnowledgeDocument`: Document chunks with contextual headers and embeddings.
   - **API Endpoints (`backend/app/chatbot/router.py`)**:
     - `POST /api/chatbot/message`: Synchronous request/response.
     - `POST /api/chatbot/stream`: Server-Sent Events (SSE) streaming token output.
     - `GET /api/chatbot/sessions`: Session history list.
     - `GET /api/chatbot/sessions/{id}`: Detailed message history.
     - `DELETE /api/chatbot/sessions/{id}`: User privacy history purge.
     - `POST /api/chatbot/feedback`: Quality rating submission.
     - `POST /api/chatbot/admin/ingest`: Protected RAG knowledge base ingestion.
2. **Isolated Frontend (`frontend/src/features/chatbot/`)**:
   - Floating chat widget accessible from any page.
   - Streaming text support via SSE reader.
   - Interactive citation chips showing document title, section, and freshness.
   - Explicit "Verified" / "General Information" badges.
   - Quick-reply buttons and in-app feedback modal.
   - Full keyboard accessibility (WCAG / ARIA compliant).

## 4. Key Assumptions & Risk Mitigation
1. **LLM Provider Agnostic**: Configurable via `LLM_PROVIDER` (`mock`, `gemini`, `openai`, `anthropic`). Built-in mock LLM enables offline deterministic unit/integration testing without requiring third-party API credits.
2. **Vector Store Compatibility**: Implements standard dense vector cosine similarity compatible with PostgreSQL (`pgvector`) and an in-process fallback for SQLite/in-memory test runners.
3. **Strict Authorization & Patient Privacy**:
   - The `get_my_appointments` tool never accepts a user/patient ID from user prompt text; it strictly binds to `current_user.id` from the validated JWT token. Guests receive an authorization challenge.
   - PII is masked at input guard and scrubbed at postprocessing.
4. **Non-Prescriptive Healthcare Safety**:
   - The system prompt forbids diagnosing illnesses, prescribing medication, or modifying medical dosages.
   - Emergency detection takes unconditional priority, bypassing normal retrieval to provide immediate contact numbers for 911 / emergency care and PulseCare urgent triage.
