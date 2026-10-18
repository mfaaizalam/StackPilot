# StackPilot: Product Requirements Document (PRD)

> Derived from `STACKPILOT_BUILD_PLAN.md` and `PHASE6_HANDOFF.md`. Items marked *(assumption)* were not stated in those docs; confirm or edit them.

---

## 1. Overview

**StackPilot** is an AI project manager. A user describes a project in plain language and the system produces, in one chain:

**Description → clarifying questions → structured requirements → IEEE-style SRS → UML diagrams → Kanban board → cost estimate in PKR**

The primary near-term goal is a polished, reliable **exhibition demo (2-3 minutes)** that still works if Wi-Fi or the AI API fails.

## 2. Problem Statement *(assumption)*

Small teams, students and freelancers in Pakistan often start software projects without proper requirements documents, diagrams, task plans or defensible cost estimates. Producing these by hand is slow and inconsistent. StackPilot automates the pipeline while keeping output structured, traceable and consistent.

## 3. Goals and Non-Goals

### Goals
- Turn a one-paragraph project description into a validated SRS, diagrams, a traceable Kanban board and a PKR cost range.
- Keep every artifact consistent with the others (requirement IDs link SRS ↔ use cases ↔ tasks ↔ costs).
- Make the output deterministic and clean: AI produces structured data, code renders and validates.
- Never leave the user stuck: every stage has a fallback.

### Non-Goals (current scope)
- Drag/edit diagram canvas (React Flow is a later upgrade).
- Swimlane activity diagrams.
- Editing use cases and entities inline (only FR/NFR fields are editable today).
- Persisting offline-demo fixtures into a user's real board.
- Verified Pakistan market pricing (rate table ships as placeholders).
- Alembic migrations (stop-gap startup migration used instead).

## 4. Target Users *(assumption)*

- Students and developers planning a project or final-year project.
- Freelancers and small software houses preparing proposals and quotations.
- Exhibition/demo visitors evaluating the product.

## 5. Core User Flow

1. **Describe** the project (textarea with examples, or load a demo).
2. **Answer** 5-8 project-specific clarifying questions (option chips + free text).
3. **Progress**: live stage stepper while a background job runs (polled every 2 s).
4. **Result**: SRS, requirements table, traceability, issues, diagrams, board, cost.
5. **Export / continue**: download, generate Kanban board, estimate cost.

## 6. Functional Requirements

### 6.1 Authentication and Ownership
- FR-1: Users shall authenticate with JWT.
- FR-2: Every route touching a board, column, task, SRS, diagram or cost estimate shall verify ownership; non-owners receive 404 (never 403); unauthenticated calls receive 401.

### 6.2 SRS Engine
- FR-3: The system shall generate 5-8 clarifying questions from the description, each with 2-4 options.
- FR-4: The system shall generate structured requirements (actors, FRs with MoSCoW priority and acceptance criteria, NFRs with metrics, use cases, entities, constraints, assumptions, interfaces, open issues) via a single LLM entry point.
- FR-5: The system shall validate requirements in code: ID formats (`FR-###`, `NFR-###`, `UC-###`), no duplicates, valid actor and FR references, every FR covered by a use case, every actor used, minimums (≥5 FR, ≥3 NFR, ≥3 UC).
- FR-6: On validation errors the system shall make exactly one AI repair attempt; remaining issues are shown to the user. Warnings (missing "shall", vague NFRs, unknown entity relations, >25 FRs per actor) are shown without repair.
- FR-7: The system shall render the SRS to Markdown deterministically (no LLM) with six sections: Introduction, Overall Description, Specific Requirements, Use Cases, Data Entities, Appendices (traceability matrix, open issues).
- FR-8: SRS generation shall run as a background job with a status row and polling endpoint; one active job per board is reused.
- FR-9: Users shall edit FR (title, statement, priority) and NFR (statement, metric); each edit re-validates, re-renders, creates a new version and marks diagrams stale.
- FR-10: Users shall switch between SRS versions.

### 6.3 SRS Studio UI
- FR-11: Result view with tabs: SRS, Requirements table, Traceability, Issues, Diagrams, Cost.
- FR-12: Export as Markdown, Word (`.docx`) and Print/PDF.

### 6.4 Diagrams
- FR-13: The system shall produce use case, class, sequence (top 4 use cases), activity (top 3) and state (max 3, lifecycle entities only) diagrams.
- FR-14: Hard limits enforced in code: class ≤12 classes / ≤8 members / ≤18 relations; sequence ≤8 participants / ≤15 messages / ≤3 fragments; activity ≤18 nodes; state ≤8 states / ≤14 transitions; every label ≤28 characters; all references must exist.
- FR-15: Pipeline per diagram: AI → validate → one repair → sanitize → AI-free fallback if AI is down.
- FR-16: The use-case diagram shall be built from requirements by code and rendered as deterministic SVG; other types render via Mermaid in the browser.
- FR-17: Each diagram shall export as SVG, PNG (2x, white background) and Mermaid text, with a full-screen Expand view.
- FR-18: When a new SRS version is saved, prior diagrams carry over flagged **stale**, with an "Out of date" banner and Regenerate button.

### 6.5 SRS → Kanban
- FR-19: The system shall generate a board from requirements with columns Backlog, Ready, In Progress, Testing, Done. No task starts in In Progress, Testing or Done.
- FR-20: One task per FR (plus one per NFR, optional), titled with the requirement ID, carrying acceptance criteria, priority (must→high, should→medium, could→low), story points (1/2/3/5/8) and suggested dependencies.
- FR-21: Dependencies shall be derived only from explicit FR references in text and use-case `fr_ids` order; cycles are never created.
- FR-22: "Ready" = a MUST task with no dependencies; all others start in Backlog.
- FR-23: Generation modes: `create` (409 if board has columns), `sync` (adds only missing requirement IDs, never touches existing tasks), `replace` (deletes and rebuilds, with two-step confirm).
- FR-24: Clicking a task shall show traceability: requirement, acceptance criteria, use cases, dependencies with live status, unblocks, and a notice if the SRS has a newer version.

### 6.6 Pakistan Cost Estimation
- FR-25: Cost shall be computed from a maintained rate table (`pk_rates.json`), never AI guesses; every item carries `source`, `last_updated`, `verified`.
- FR-26: Effort model: function points from SRS → KSLOC → COCOMO II → person-months and schedule, with inputs for platform, complexity, reliability and team experience.
- FR-27: Cross-checks with Use Case Points and board story points (relative size only).
- FR-28: Output optimistic / likely / pessimistic scenarios with PERT, cost per role, overhead, hosting/tools, contingency, tax, monthly burn, sensitivity table (salaries ±20%, scope ±30%) and ROI/payback/break-even when yearly revenue is provided.
- FR-29: AI shall only explain results; code rejects AI text containing numbers not present in the computed figures and falls back to a template explanation.
- FR-30: The UI shall always show rate-table version, `last_updated`, an estimate disclaimer, and a warning while any rate is unverified.

### 6.7 Exhibition Hardening
- FR-31: Public read-only `GET /demo/{hospital|ecommerce|university}` serves static fixtures with no Gemini, Qdrant or database access; unknown names return a safe 404.
- FR-32: SRS Studio shall offer one-click demo previews (SRS, requirement counts, diagram source, Kanban tasks, illustrative cost).
- FR-33: Live question/SRS failures, or an SRS job running over 60 s, shall fall back to the offline demo, clearly labelled.
- FR-34: A generic exception handler shall log details server-side and return a safe message.

### 6.8 Existing Features
- AI chat over board data using RAG (Qdrant + sentence-transformers), project analysis, boards/columns/tasks CRUD, email-based flows.

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Security | Ownership checks on all board-linked routes; user text wrapped in `<project>` tags against prompt injection; no secrets in git or zips; CORS from `FRONTEND_ORIGINS`; HTTPS in deployment |
| Reliability | Every phase leaves the app working; AI-down fallbacks for diagrams, explanation and demo; board generation is one all-or-nothing transaction |
| Performance | Real Gemini SRS generation in about 90 s or less for a one-paragraph description; board and cost calculation in milliseconds; no request blocks more than a few seconds |
| Determinism | Same input yields identical board plan and identical cost figures |
| Cost control | Max 5 SRS and 5 diagram jobs per user per hour; 30 cost estimates and 10 AI explanations per user per hour; Gemini billing budget set |
| Compatibility | Works on desktop and phone layouts without horizontal overflow |
| Maintainability | Thin routes, logic in `services/`; one LLM entry point `llm_json`; model name from `GEMINI_MODEL` |
| Testability | Fake LLM mode (`LLM_FAKE=1`) for tests and offline demo; 138+ backend tests |

## 8. Technical Constraints

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.x, Pydantic v2, Neon PostgreSQL.
- **AI:** Gemini via `google-genai`; Qdrant + sentence-transformers for RAG.
- **Frontend:** React 18, Vite, Tailwind, axios, react-markdown + remark-gfm, Mermaid.
- **Golden rules:** AI never draws; validate with code; single LLM entry point; long jobs run in the background; costing uses a rate table; each phase stays demo-safe.

## 9. Success Metrics

- A user goes from description to downloadable SRS without touching Swagger.
- Every `must` FR appears as at least one board task.
- Diagrams render without errors for three different sample projects.
- The 3-minute exhibition script completes even with Gemini or Wi-Fi unavailable.
- Cost output is reproducible and its assumptions are visible.

## 10. Current Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Security and stability | Done (key rotation is a user action; Alembic still open) |
| 1 | LLM core + SRS engine | Done, tested with fake LLM |
| 2 | SRS Studio UI + export | Done, builds clean |
| 3 | Diagrams | Done, 47 tests; browser visuals unverified |
| 4 | SRS → Kanban | Done, 91 tests |
| 5 | PKR cost estimation | Done, 138 tests; rates are placeholders |
| 6 | Exhibition hardening | Code built; manual/live verification pending |

## 11. Risks and Open Items

- **Never run against real services end-to-end:** Gemini, Neon/PostgreSQL and Qdrant have not been exercised together. Do one full real run first.
- **Placeholder rates:** all `pk_rates.json` values are `verified: false`; estimates are demo-grade until sourced (tax varies by province).
- **Gemini free-tier limits:** parallel diagram calls may fall back to rule-based diagrams; use a paid key for the exhibition.
- **Browser visuals unverified:** Mermaid layout, PNG export, Expand view and print layout.
- **Exposed credentials:** rotate Neon password, Gmail app password, Gemini keys, Qdrant key and JWT `SECRET_KEY`.
- **60-second timeout** is client-side only; the server job is not cancelled.
- **Alembic** must be added before the next change to an existing table.

## 12. Exhibition Readiness Checklist

- [ ] Backend tests and frontend production build pass in the target environment.
- [ ] All three demo previews clicked through on desktop and phone.
- [ ] Fallback verified with Gemini unavailable and with a simulated 60 s job.
- [ ] Rate limits verified against a real test user.
- [ ] One real end-to-end run with Gemini, Neon and Qdrant.
- [ ] Rates in `pk_rates.json` replaced with sourced data and marked verified.
- [ ] Gemini billing budget set; credentials rotated.
- [ ] Deployed with correct `FRONTEND_ORIGINS`, HTTPS and health checks.
- [ ] 60-second backup video recorded, pipeline poster ready, 3-minute script rehearsed.

## 13. Future Work (Phase 7 candidate, owner approval required)

Exhibition QA and deployment validation: run against real services, verify production migration and CORS, validate browser diagrams/export/print, verify cost rates, rehearse. Later: React Flow diagram editing, Alembic, editing use cases/entities, lighter embeddings via Gemini.
