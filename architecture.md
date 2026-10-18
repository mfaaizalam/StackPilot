# StackPilot: Architecture

> Sources: repo tree (`repo_tree.txt`), `STACKPILOT_BUILD_PLAN.md`, `PHASE6_HANDOFF.md`. Descriptions of files not covered by those docs (e.g. RAG internals, auth) are inferred from file names and marked *(inferred)*.

---

## 1. System at a Glance

```
React 18 + Vite + Tailwind (frontend)
        │  axios (JWT)  — VITE_API_URL
        ▼
FastAPI (backend/app/main.py)
  routes (thin) → services (logic) → models / schemas
        │                │
        │                ├── core/llm.py ──► Gemini (google-genai)   [only LLM entry point]
        │                ├── rag/*       ──► Qdrant + sentence-transformers
        │                └── SQLAlchemy  ──► Neon PostgreSQL
        └── /demo/{name} ──► static JSON fixtures (no AI, no DB)
```

**Core pipeline:** Description → questions → requirements JSON → SRS Markdown → diagrams → Kanban board → PKR cost estimate.

## 2. Golden Rules (architectural invariants)

1. **AI never draws.** AI returns structured JSON validated by Pydantic; code renders documents and diagrams.
2. **Validate with code.** IDs, traceability and diagram limits are checked in Python; AI gets at most one repair attempt.
3. **Ownership on every board-linked route** via `core/deps.py` (`get_owned_board/column/task`). 404, never 403.
4. **One LLM entry point:** `core/llm.py → llm_json(prompt, schema)`. Model from `GEMINI_MODEL`.
5. **Long jobs run in the background** with a status row and polling endpoint.
6. **No secrets in git or zips.**
7. **Costing uses a maintained rate table**; AI only explains.
8. **Every phase stays demo-safe.**

## 3. Repository Layout

```
.
├── README.md  prd.md  architecture.md
├── STACKPILOT_BUILD_PLAN.md      # phased plan + status log (source of truth)
├── PHASE6_HANDOFF.md             # exhibition hardening contract + QA checklist
├── backend/
│   ├── requirements.txt  vercel.json  .env.example
│   ├── migrations/phase4_tasks.sql      # manual version of startup migration
│   ├── tests/                           # pytest, SQLite + fake LLM
│   └── app/
│       ├── main.py                      # app, CORS, routers, startup migration, exception handler
│       ├── core/                        # config, database, deps, llm, llm_fake, migrate, security
│       ├── models/                      # SQLAlchemy tables
│       ├── schemas/                     # Pydantic request/response + LLM output schemas
│       ├── routes/                      # thin HTTP layer
│       ├── services/                    # business logic
│       ├── prompts/                     # prompt templates
│       ├── rag/                         # vector search for chat
│       └── data/                        # pk_rates.json, demo_fixtures.json
└── frontend/
    ├── package.json  vite.config.js  tailwind.config.js  vercel.json  .env.example
    ├── public/StackPilot_video.mp4      # backup demo video
    └── src/
        ├── main.jsx  App.jsx  index.css
        ├── api/axios.js                 # axios instance, VITE_API_URL
        ├── pages/                       # route-level screens
        ├── components/                  # reusable UI
        └── hooks/useReveal.js
```

## 4. Backend

### 4.1 Layers

| Layer | Folder | Responsibility |
|---|---|---|
| Routes | `routes/` | Parse input, check auth/ownership, call a service, return JSON. No logic. |
| Services | `services/` | All business logic. Pure where possible (planner, calculator, validators). |
| Models | `models/` | SQLAlchemy 2.x tables. |
| Schemas | `schemas/` | Pydantic v2: API contracts and flat LLM output schemas (no dicts, no recursion, so Gemini accepts them). |
| Prompts | `prompts/` | Prompt text per feature. |
| Core | `core/` | Config, DB session, JWT/security, LLM client, ownership deps, startup migration. |
| RAG | `rag/` | Embeddings, Qdrant access, retrieval, chat memory *(inferred)*. |

### 4.2 Core modules

- `config.py`: settings from env (`DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `FRONTEND_ORIGINS`, `QDRANT_*`, `EMAIL_*`, `LLM_FAKE`).
- `database.py`: engine and `SessionLocal`. Background jobs open their **own** session.
- `deps.py`: `get_current_user`, `get_owned_board`, `get_owned_column`, `get_owned_task`.
- `llm.py`: `llm_json(prompt, schema, system, temperature)`. Structured JSON mode, `model_validate_json`, 3 retries with backoff on 429/5xx, raises `LLMError`.
- `llm_fake.py`: canned JSON when `LLM_FAKE=1` (tests and offline demo).
- `migrate.py`: idempotent startup migration (adds 4 columns to `tasks`; failure is logged, never blocks boot). Stop-gap until Alembic.
- `security.py`: password hashing and JWT *(inferred)*.

### 4.3 Route map

| Route file | Domain |
|---|---|
| `auth.py` | Register/login, OTP email verification *(inferred from `otp.py`, `email_service.py`)* |
| `board.py`, `column.py`, `task.py` | Kanban CRUD, owner-checked |
| `ai.py` | Original flat AI project generator (auth required) |
| `analysis.py` | Project analysis (owner-checked) |
| `chat.py` | RAG chat over a board (owner-checked) |
| `srs.py` | `/boards/{id}/srs`: questions, generate (job), jobs poll, latest, versions, export `.md`/`.docx`, PATCH requirements |
| `diagrams.py` | `/boards/{id}/srs/diagrams`: generate (job), jobs poll, list |
| `srs_board.py` | `POST /boards/{id}/srs/generate-board`; `GET /boards/{id}/tasks/{task_id}/trace` |
| `cost.py` | `/boards/{id}/srs/cost`: `rates`, `estimate`, latest, `{id}/explain` |
| `demo.py` | Public `GET /demo/{hospital\|ecommerce\|university}`, static only |

### 4.4 Data model

- `User`, `OTP` *(inferred)*, `Chat` messages.
- `Board` → `Column` → `Task` (cascade deletes). Task has Phase 4 fields: `requirement_id`, `estimate_points`, `depends_on` (JSON), `srs_id`.
- `SRSDocument`: versioned (`version`, `description`, `answers`, `requirements` JSON, `issues`, `markdown`), cascade from Board.
- `SRSJob`, `DiagramJob`: background job status rows (`queued/running/done/failed`, `stage`, `error`).
- `Diagram`: per SRS version (`type`, `model` JSON, `stale`).
- `CostEstimate`: saved estimates so the Cost tab reloads instantly; cascade from Board.

New tables are created by `create_all`; changes to existing tables need `migrate.py` (or Alembic, still open).

## 5. Feature Architecture

### 5.1 SRS engine

```
description ─► generate_questions (LLM) ─► answers
            ─► build_requirements:  LLM ─► srs_validator ─► [errors? one repair LLM call] ─► validator again
            ─► render_srs_markdown (deterministic template, no LLM)
            ─► SRSDocument (version = last + 1)
```

- Files: `srs_service.py`, `srs_validator.py`, `srs_docx.py`, `prompts/srs_prompt.py`, `schemas/srs.py`.
- Job stages: questions → requirements → validating → rendering → saving.
- Protections: one active job per board reused, 5 jobs per user per hour, user text wrapped in `<project>` tags (prompt-injection guard).
- Edits via `PATCH /requirements` re-validate, re-render, create a new version and mark diagrams stale.

### 5.2 Diagrams

```
validated requirements
   ├─ use case:  built by code ─► diagram_usecase_svg.py (custom SVG) 
   └─ class / sequence / activity / state:
        LLM ─► validate_* ─► one repair ─► sanitize_* ─► diagram_mermaid.py ─► Mermaid text ─► browser render
        LLM down ─► diagram_fallbacks.py (rule-based, flagged "Drawn from requirements")
```

- Hard limits enforced in `diagram_validator.py` (class ≤12, sequence ≤15 messages, labels ≤28 chars, etc.).
- `diagram_service.py` runs a thread-pool job (up to 4 parallel AI calls), saving each diagram as it finishes.
- Stale carry-over: new SRS version copies old diagrams with `stale=true`.
- Frontend: `DiagramsPanel.jsx` (stays mounted so polling continues), `DiagramCard.jsx` (SVG/PNG/Mermaid export, Expand).

### 5.3 SRS → Kanban

- `board_planner.py`: pure function `plan_board(requirements, include_nfr)` → columns, tasks, warnings. Deterministic; handles Ready rule, dependency derivation, cycle breaking, story points.
- `board_service.py`: `generate_board` (single transaction, row lock, modes `create | sync | replace`), `index_tasks` (best-effort Qdrant indexing in a background task), `task_trace`.
- No AI and no job: answers inside the request.

### 5.4 Cost estimation

```
SRS requirements ─► function points ─► KSLOC ─► COCOMO II ─► person-months/schedule
rates (pk_rates.json via cost_rates.py, validated) ─► cost_calculator.py (pure)
   ─► O/L/P scenarios + PERT, per-role, overhead, tax, contingency, sensitivity, ROI
   ─► cross-checks: Use Case Points, board story points
cost_service.py ─► saves CostEstimate; explanation = template, or AI text accepted only if every number is in `figures`
```

- Limits: 30 estimates and 10 AI explanations per user per hour.
- Frontend: `CostPanel.jsx`. All rates currently `verified: false`; UI warns.

### 5.5 RAG chat and analysis

- `chat.py` → `chat_service.py` / `gemini_chat_service.py` → `rag/*` (`embedding_service`, `qdrant_service`, `retrieval_service`, `chat_retrieval`, `chat_memory`, `vector_service`) with `context_builder.py` building board context *(inferred)*.
- `analysis_service.py` + `analysis_prompt.py` power `ProjectAnalysis.jsx`.
- `ai_save_service.py` saves flat AI-generated projects with safe column lookup.
- Qdrant is imported lazily and indexing failures never break board generation.

### 5.6 Exhibition fallback (Phase 6)

- `GET /demo/{name}` reads `data/demo_fixtures.json`; no Gemini, Qdrant or DB.
- Frontend falls back to the hospital demo when question/SRS generation fails or a job exceeds 60 s (client-side timeout; the server job continues).
- Demo data is a standalone labelled preview; it is never written into a user's board.
- Global exception handler in `main.py` logs details and returns a safe message.

## 6. Frontend

| Area | Files |
|---|---|
| Entry/routing | `main.jsx`, `App.jsx` (`PrivateRoute` wraps protected pages) |
| Public pages | `Landing.jsx`, `Login.jsx`, `Register.jsx`, `NotFound.jsx`, `AuthShell.jsx` |
| App pages | `Dashboard.jsx`, `Boards.jsx`, `BoardDetail.jsx` (Kanban, traceability panel, points chip, SRS button), `ProjectAnalysis.jsx`, `SrsStudio.jsx` (`/boards/:boardId/srs`) |
| SRS Studio tabs | SRS, Requirements, Traceability, Issues, Diagrams (`DiagramsPanel`), Cost (`CostPanel`) |
| Shared UI | `BoardModal`, `ColumnModal`, `TaskModal`, `ConfirmDialog`, `ChatWidget` |
| API | `api/axios.js`: base URL from `VITE_API_URL` (falls back to the deployed backend URL) |
| Styling | Tailwind, neutral cards, `rounded-2xl`; print stylesheet hides UI for PDF |

Rendering libraries: `react-markdown` + `remark-gfm` for the SRS, `mermaid` (lazy-loaded chunk) for diagrams.

## 7. Key Data Flows

**Generate SRS**
`SrsStudio` → `POST /srs/questions` → user answers → `POST /srs/generate` (returns `job_id`) → poll `GET /srs/jobs/{id}` every 2 s → `GET /srs` for result.

**Board from SRS**
`POST /srs/generate-board` (mode) → planner → one transaction → tasks with `requirement_id`, `srs_id` → UI task panel calls `GET /tasks/{id}/trace`.

**Cost**
`POST /srs/cost/estimate` (instant) → stored → `GET /srs/cost` reloads (with `srs_outdated` flag) → optional `POST /{id}/explain`.

## 8. Security Model

- JWT auth; every board-linked route resolves through `deps.py` and returns 404 for non-owners.
- Per-user hourly rate limits on AI-backed jobs and explanations.
- CORS origins from `FRONTEND_ORIGINS` plus localhost.
- Public surface is only `/demo/*` (static) and auth routes.
- Secrets live in `.env` (git-ignored); `.env.example` lists names only. Credentials exposed earlier must be rotated.

## 9. Testing

- `backend/tests/`: `test_srs.py`, `test_diagrams.py`, `test_board_gen.py`, `test_cost.py`, `test_demo_fixtures.py`, shared `conftest.py`.
- Runs on SQLite with `LLM_FAKE=1`; needs no keys: `cd backend && python -m pytest tests -q`.
- Frontend check: `cd frontend && npm ci && npm run build`.
- Not yet covered by automation: real Gemini, Neon, Qdrant, real-browser visuals.

## 10. Deployment and Config

- Both `backend/vercel.json` and `frontend/vercel.json` exist; the frontend default API URL points at a Railway deployment, so confirm where the backend actually runs.
- Required env: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`. New: `GEMINI_MODEL`, `FRONTEND_ORIGINS`, `LLM_FAKE`. Frontend: `VITE_API_URL`.
- Watch the first PostgreSQL deploy log for "Added columns to tasks".

## 11. Known Gaps

- No Alembic (use `migrate.py` until the next change to an existing table).
- Never run end-to-end against real Gemini, Neon and Qdrant.
- `pk_rates.json` values are unverified placeholders.
- Mermaid layout, PNG export and print layout are unchecked in a real browser.
- Inline editing covers FR/NFR only, not use cases or entities.
- `repo_tree.txt` is a generated helper file; consider git-ignoring it.
