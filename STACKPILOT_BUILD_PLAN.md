# StackPilot: Phased Build Plan and Handoff

> **Read this first if you are continuing someone else's work (a developer or another AI).**
> This file is the single source of truth. Work one phase at a time, tick the checkboxes, and update the **Status Log** at the bottom before you stop.

---

## 0. What the product is

StackPilot is an AI project manager. The user describes a project and the system produces, in one chain:

**Description → clarifying questions → structured requirements → IEEE-style SRS → clean UML diagrams → Kanban board → cost estimate in PKR**

Goal: a polished, reliable exhibition demo (2–3 minutes, works even if Wi-Fi or the AI API fails).

**Stack (existing):** FastAPI + SQLAlchemy (Neon PostgreSQL) · Gemini via `google-genai` · Qdrant + sentence-transformers (RAG chat) · React 18 + Vite + Tailwind · JWT auth.

**Project layout:** `backend/app/{core,models,schemas,routes,services,prompts,rag}` and `frontend/src/{pages,components,api}`.

---

## 1. Golden rules (do not break these)

1. **The AI never draws.** The AI produces *structured JSON* validated by Pydantic. Our code renders documents and diagrams deterministically. This is what keeps the output clean and consistent.
2. **Validate with code, not the AI.** Requirement IDs, traceability and diagram size limits are checked in Python. The AI only gets one repair attempt.
3. **Every route that touches a board, column, task or SRS must check ownership** via `app/core/deps.py` (`get_owned_board`, `get_owned_column`, `get_owned_task`). Return 404, never 403.
4. **One LLM entry point:** all model calls go through `app/core/llm.py` → `llm_json(prompt, schema)`. Model name comes from settings (`GEMINI_MODEL`), not hardcoded.
5. **Long jobs run in the background** with a status row and a polling endpoint. Never block a request for more than a few seconds.
6. **Never commit secrets.** `.env`, `venv/` and `__pycache__/` stay out of git and out of zips.
7. **Pakistan costing uses a maintained rate table**, not AI guesses. The AI only explains results.
8. Keep every phase **demo-safe**: each phase must leave the app working.

---

## 2. Status overview

| Phase | Name | Status |
|---|---|---|
| 0 | Security and stability fixes | **DONE** (code); key rotation is a USER action |
| 1 | LLM core + SRS engine (backend) | **DONE**, 13 tests pass with fake LLM; real Gemini not yet tested |
| 2 | SRS UI (frontend) + export | **DONE**, builds clean; not yet clicked through in a real browser |
| 3 | Diagram models + renderers | **DONE**, 47 tests pass (fake LLM); Mermaid output verified with the real Mermaid parser; not yet clicked through in a real browser |
| 4 | SRS → Kanban generation | **DONE**, 91 backend tests pass (47 old + 44 new); startup migration proven against an old-schema DB; UI logic checked in a simulated DOM; not yet clicked through in a real browser |
| 5 | Pakistan cost estimation | **DONE**, 138 backend tests pass (91 old + 47 new); Cost tab checked in real headless Chromium with mocked API (desktop + phone, no overflow); **rate table values are unverified placeholders the owner must replace** |
| 6 | Exhibition hardening (cache, fallback, video) | **CODE BUILT; manual/live verification pending** |

---

## PHASE 0: Security and stability fixes

**Goal:** nobody can read, change or delete another user's data or burn the API quota.

### Done (compile-checked only, not run against a real DB)
- [x] `backend/app/core/deps.py` created with `get_owned_board / get_owned_column / get_owned_task`.
- [x] `routes/board.py`: get, update and delete now require login + ownership.
- [x] `routes/column.py`: create, get, update and delete now require login + ownership (update also checks the target board).
- [x] `routes/task.py`: create, get, update and delete now require login + ownership (update also checks the target column).
- [x] All `.py` files converted from CRLF to LF line endings.

### Completed in the second pass
- [x] `routes/ai.py` → `/ai/generate-project` has **no auth**. Add `current_user = Depends(get_current_user)`.
- [x] `routes/analysis.py` → call `get_owned_board(db, board_id, current_user)` before `analyze_project`.
- [x] `routes/chat.py` → call `get_owned_board` before `ask_ai`.
- [x] `services/ai_save_service.py` → on `column_map[task.column_name]` use `.get()` and skip or fall back to the first column instead of crashing with a 500.
- [x] `main.py` → CORS `allow_origins` must include the **deployed frontend URL** (read from a `FRONTEND_ORIGINS` env var, comma-separated) plus localhost.
- [x] `core/config.py` → add `GEMINI_MODEL: str = "gemini-2.5-flash"` (change if your account uses a different model) and `FRONTEND_ORIGINS: str = ""`. Stop using `GEMINI_API_KEY_2/_3` for different features; use one key (`GEMINI_API_KEY`). Keep the extra fields optional so old `.env` files still load.
- [ ] **STILL OPEN:** add Alembic. Phase 1 adds NEW tables only, so `create_all` creates them; any later change to an existing table needs a migration. **Phase 4 handled its one change (4 new columns on `tasks`) with `app/core/migrate.py`, an idempotent startup upgrade, so Alembic is no longer blocking. Add it before the next change to an existing table.**
- [x] `models/task.py` has duplicate `column_id` and `created_by` definitions. Remove the first pair.
- [x] `requirements.txt` → remove the trailing `# dd`, remove `psycopg` *or* `psycopg2-binary` (keep one), and consider replacing `torch` + `sentence-transformers` with Gemini embeddings to make deployment lighter.
- [ ] **USER ACTION (cannot be done by code): rotate every key** (Neon DB password, Gmail app password, all Gemini keys, Qdrant key, JWT `SECRET_KEY`). They were shared in a zip.
- [x] Add `.env.example` with variable names only.

**Acceptance:** with two test users A and B, user B gets 404 on every board/column/task/chat/analyze/SRS endpoint belonging to A, and unauthenticated calls get 401.

---

## PHASE 1: LLM core + SRS engine (backend only)

**Goal:** `description + answers → validated requirements JSON → rendered SRS Markdown`, produced by a background job.

### 1.1 `app/core/llm.py`
```python
def llm_json(prompt: str, schema: type[BaseModel], *, system: str = "", temperature: float = 0.2) -> BaseModel
```
- Uses `google-genai` with `GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=temperature, system_instruction=system)`.
- Parses with `schema.model_validate_json`.
- Retries 3× with exponential backoff on 429/5xx/`RESOURCE_EXHAUSTED`. Raises a clean `LLMError`.
- Add a **fake mode** (`LLM_FAKE=1` env) that returns canned JSON so tests and the offline demo work without network.

### 1.2 Models (`app/models/srs.py`, import in `main.py`)
- `SRSDocument`: `id, board_id (FK boards.id, ondelete CASCADE), version:int, description:Text, answers:JSON, requirements:JSON, issues:JSON, markdown:Text, created_at`.
- `SRSJob`: `id:str (uuid), board_id, user_id, status ('queued'|'running'|'done'|'failed'), stage:str, error:Text|None, srs_id:int|None, created_at`.
- `Diagram` (used in Phase 3): `id, srs_id (FK CASCADE), type, title, model:JSON, stale:bool, created_at`.
- Add `srs_documents = relationship(..., cascade="all, delete-orphan")` on `Board`.

### 1.3 Requirements schema (`app/schemas/srs.py`)
Keep fields simple (no dicts, no recursive types) so Gemini structured output accepts it.
```python
class Actor(BaseModel): name: str; description: str
class FR(BaseModel):  id: str; title: str; statement: str; priority: Literal["must","should","could"]; actor: str; acceptance_criteria: list[str]
class NFR(BaseModel): id: str; category: Literal["performance","security","usability","reliability","maintainability","compatibility","scalability"]; statement: str; metric: str
class UseCase(BaseModel): id: str; name: str; actor: str; description: str; fr_ids: list[str]; preconditions: list[str]; main_flow: list[str]; alternate_flows: list[str]
class Entity(BaseModel): name: str; description: str; attributes: list[str]; relations: list[str]
class Term(BaseModel): term: str; definition: str
class Requirements(BaseModel):
    title: str; purpose: str; scope: str; product_perspective: str
    definitions: list[Term]; actors: list[Actor]
    functional_requirements: list[FR]; non_functional_requirements: list[NFR]
    use_cases: list[UseCase]; entities: list[Entity]
    constraints: list[str]; assumptions: list[str]; external_interfaces: list[str]; open_issues: list[str]
class Question(BaseModel): id: str; question: str; options: list[str]
class QuestionList(BaseModel): questions: list[Question]
```

### 1.4 Validator (`app/services/srs_validator.py`), pure Python, returns `list[Issue(level, code, message)]`
Errors (trigger the single repair call):
- IDs must match `FR-\d{3}`, `NFR-\d{3}`, `UC-\d{3}`; no duplicates.
- Every `UseCase.actor` and `FR.actor` exists in `actors`.
- Every `UseCase.fr_ids` item exists.
- **Every FR is covered by at least one use case** (traceability).
- Every actor appears in at least one use case.
- Minimums: ≥3 actors is *not* required; ≥5 FR, ≥3 NFR, ≥3 UC.
Warnings (shown to the user, no repair):
- FR statement doesn't contain "shall".
- NFR has an empty `metric` or uses vague words (`fast`, `user-friendly`, `easy`, `efficient`, `robust`, `scalable`) without a number.
- Entity referenced in `relations` doesn't exist.
- More than 25 FRs per actor (suggest splitting).

### 1.5 Prompts (`app/prompts/srs_prompt.py`)
- **Questions prompt:** read the description, return 5–8 short, project-specific questions with 2–4 options each (roles, platform, must-have features, integrations, scale, constraints, deadline).
- **Requirements prompt:** system role = senior requirements engineer following ISO/IEC/IEEE 29148. Rules: "The system shall…" wording; one requirement = one testable statement; measurable NFRs (e.g. "95% of pages load in under 3 s on 4G"); no invented facts, so put guesses in `assumptions` and unknowns in `open_issues`; IDs sequential; every FR mapped by a use case.
- **Repair prompt:** give the previous JSON + the list of validator errors; ask for the *complete corrected* JSON.

### 1.6 Service (`app/services/srs_service.py`)
- `generate_questions(description) -> QuestionList`
- `build_requirements(description, answers) -> (Requirements, issues)`: LLM → validate → if errors, **one** repair → validate again → return remaining issues.
- `render_srs_markdown(req: Requirements, issues) -> str`: deterministic template, no LLM. Sections:
  1. Introduction (purpose, scope, definitions, overview)
  2. Overall description (perspective, user classes/actors, constraints, assumptions)
  3. Specific requirements (3.1 external interfaces, 3.2 functional grouped by actor, 3.3 non-functional grouped by category)
  4. Use cases (with main and alternate flows)
  5. Data entities
  6. Appendix A: Traceability matrix (FR ↔ UC), Appendix B: Open issues
- `run_srs_job(job_id)`: opens its **own** `SessionLocal()`, updates `stage` ("questions" → "requirements" → "validating" → "rendering" → "saving"), writes `SRSDocument` with `version = last+1`, sets `status='done'` or `'failed'` with a readable error.

### 1.7 Routes (`app/routes/srs.py`, prefix `/boards/{board_id}/srs`, all owner-checked)
| Method | Path | Body / result |
|---|---|---|
| POST | `/questions` | `{description}` → `{questions:[...]}` |
| POST | `/generate` | `{description, answers:[{question,answer}]}` → `{job_id}` (uses `BackgroundTasks`) |
| GET | `/jobs/{job_id}` | `{status, stage, error, srs_id}` |
| GET | `/` | latest SRS (requirements, issues, markdown, version) |
| GET | `/versions` | list of versions |
| GET | `/export.md` | Markdown download |
| PATCH | `/requirements` | user-edited requirements JSON → re-validate, re-render, new version, mark diagrams stale |

Register the router in `main.py`.

### 1.8 Tests (`backend/tests/`)
- Validator unit tests (good sample, missing-FR-coverage, duplicate IDs, unknown actor).
- Renderer test (snapshot of a sample requirements JSON).
- Job test using `LLM_FAKE=1` + SQLite.

**Built:** `core/llm.py`, `core/llm_fake.py`, `models/srs.py`, `schemas/srs.py`, `services/srs_validator.py`, `services/srs_service.py`, `prompts/srs_prompt.py`, `routes/srs.py`, `tests/`. Beyond the spec: one active job per board is reused (no double billing), max 10 jobs per user per hour, user text is wrapped in `<project>` tags to resist prompt injection.

**Deviations / not done:** `PATCH /requirements` creates a new version but diagram stale-marking waits for Phase 3. Validator minimum for actors is 1 (not 3).

**Run tests:** `cd backend && pip install pytest httpx && python -m pytest tests -q` (uses SQLite + fake LLM, needs no keys).

**Acceptance:** with `LLM_FAKE=1` the whole job completes and the Markdown contains all six sections; with a real key a one-paragraph description yields a valid SRS in under about 90 seconds.

---

## PHASE 2: SRS UI + export (frontend)

**Goal:** a nice "SRS Studio" page inside each board.

- [x] New page `frontend/src/pages/SrsStudio.jsx`, route `/boards/:boardId/srs` (wrapped in `PrivateRoute` in `App.jsx`), plus a button on `BoardDetail.jsx`.
- [x] Step flow: **1. Describe** (textarea + examples) → **2. Answer questions** (tappable option chips + free text) → **3. Progress** (poll `/jobs/{id}` every 2 s; show the stage names as a stepper) → **4. Result**.
- [x] Result view: tabs **SRS | Requirements table | Traceability | Issues**; render Markdown with the existing `react-markdown`.
- [x] Inline edit of a requirement → `PATCH /requirements`.
- [x] Buttons: **Download .md**, **Download .docx** (backend `GET /export.docx` using `python-docx`), **Print / PDF** (browser print stylesheet).
- [x] Version dropdown.
- [x] Use the same Tailwind look as `ProjectAnalysis.jsx` (neutral cards, rounded-2xl).
- [x] Move the hardcoded base URL in `src/api/axios.js` to `import.meta.env.VITE_API_URL` with a localhost fallback.

**Built:** `frontend/src/pages/SrsStudio.jsx` (route `/boards/:boardId/srs`, "SRS" button bottom-left of the board page), `backend/app/services/srs_docx.py` (`GET /boards/{id}/srs/export.docx`, built from the structured data), `remark-gfm` added for Markdown tables, `frontend/.env.example`.

**Deviations:** `axios.js` reads `VITE_API_URL` but still falls back to the deployed Railway URL (not localhost) so existing behaviour does not change; for local dev create `frontend/.env` with `VITE_API_URL=http://localhost:8000`. PDF is "Print to PDF" via the browser (print CSS hides the UI). Editing supports FR title/statement/priority and NFR statement/metric (not use cases or entities yet).

**Verified:** `npx vite build` passes; the sample SRS Markdown renders through react-markdown + remark-gfm as 6 tables / 8 sections with no raw pipes; 14 backend tests pass (including .docx export and ownership). **Not verified:** real browser click-through, print layout, polling against a live backend.

**Acceptance:** `npm run build` passes; a user can go from description to a downloadable SRS without touching Swagger.

---

## PHASE 3: Diagrams (the "mind-blowing" part)

**Goal:** clean, readable UML from the SRS JSON.

### 3.1 Diagram models (small schemas, built from the *validated* requirements JSON)
- **Use case:** `actors, use_cases, includes, extends`, one system boundary.
- **Class:** `classes(name, attributes, methods), relations(kind: association|aggregation|composition|inheritance, source, target, multiplicity_source, multiplicity_target, label)`.
- **Sequence** (top 4 use cases): `participants, messages(source, target, text, kind: sync|return|async), fragments(opt|alt|loop)`.
- **Activity** (top 3 use cases): `nodes(start|action|decision|merge|end), edges(label)`.
- **State:** only for entities that have a lifecycle (max 3 machines).

### 3.2 Hard limits enforced in code (this is what prevents "messy")
Class diagram <= 12 classes, <= 8 members each, <= 18 relations; sequence <= 8 participants, <= 15 messages, <= 3 fragments; activity <= 18 nodes; state <= 8 states, <= 14 transitions; **every label <= 28 characters**; every referenced name must exist. Pipeline per diagram: AI -> `validate_*` -> one repair call if errors -> `sanitize_*` (always yields a diagram that satisfies every limit, with a warning shown to the user) -> if the AI is down, a deterministic AI-free fallback is drawn instead.

### 3.3 Rendering
- [x] **Mermaid.js** in the browser for class, sequence, activity (flowchart) and state. The backend converts model -> Mermaid text (`services/diagram_mermaid.py`), scrubbing every label so it cannot break the syntax. Mermaid is lazy-loaded (separate chunk).
- [x] **Use-case diagram:** our own deterministic SVG renderer in Python (`services/diagram_usecase_svg.py`): actors left, external systems right as `<<system>>` boxes, rounded boundary, ellipses, dashed `<<include>>` / `<<extend>>` arcs. **No ELK needed**: use cases are ordered by actor and each actor is centred on its own use cases, so lines are short and rarely cross.
- [ ] Later upgrade: React Flow for drag/edit. Because we store JSON, only the frontend changes.
- [x] Exports per diagram: **SVG, PNG (2x, white background), Mermaid text**, plus an "Expand" full-screen view.

### 3.4 Routes (all owner-checked, prefix `/boards/{board_id}/srs/diagrams`)
| Method | Path | Result |
|---|---|---|
| POST | `/generate` | body `{srs_id?, types?}` -> `{job_id, srs_id}` (background job; reuses a running job; max 15/hour/user) |
| GET | `/jobs/{job_id}` | `{status, stage:"3/9", error}` (stage is progress, diagrams are saved as each one finishes) |
| GET | `?srs_id=` | `{srs_id, version, diagrams:[{id,type,title,stale,warnings,source, svg \| mermaid}]}` |

**Stale flag:** whenever a new SRS version is saved (edit or regeneration), the previous version's diagrams are copied to it with `stale=true`; the UI shows an amber "Out of date" banner with a Regenerate button. Regenerating replaces old diagrams of that type (never duplicates).

### Built
`schemas/diagrams.py`, `services/diagram_validator.py` (validate + sanitize), `services/diagram_mermaid.py`, `services/diagram_usecase_svg.py`, `services/diagram_fallbacks.py` (use-case builder, entity->class parser, entity chunking, sequence/activity from use-case flows, use-case ranking), `services/diagram_service.py` (pipeline + thread-pool job), `prompts/diagram_prompt.py`, `routes/diagrams.py`, `DiagramJob` model, fake-LLM diagram data, `tests/test_diagrams.py` (33 tests). Frontend: `components/DiagramCard.jsx`, `components/DiagramsPanel.jsx`, new **Diagrams** tab in `SrsStudio.jsx` (stays mounted so a running job keeps polling), `mermaid` dependency.

### Deviations from the original plan
- **Use-case diagram is built from the requirements by code, not by the AI** (actors, use cases and associations already exist in the JSON, so this is 100% consistent with the SRS). The AI only proposes optional include/extend arcs.
- **No ELK.js.** The custom layout above replaced it (one less dependency).
- Routes are nested under `/boards/{board_id}/...` (not `/srs/{srs_id}/...`) so ownership is checked the same way as everything else. Types are generated together in one job instead of one POST per type.
- Activity diagrams are drawn with Mermaid `flowchart` (no swimlanes).
- If the AI is unavailable, class/sequence/activity fall back to rule-based diagrams (flagged "Drawn from requirements"); state diagrams are simply skipped because a lifecycle cannot be honestly guessed.
- Entities > 12 are split into up to 2 class diagrams by connected group.
- Sequence participants whose name matches an SRS actor are drawn as UML actors.

### Verified
- `python -m pytest tests -q` -> 47 passed (14 old + 33 new): limits, dangling references, 200-round garbage-in property test (sanitizers always yield valid output), Mermaid scrubbing, SVG is well-formed XML / deterministic / no overlaps, API flow, stale flag, regenerate-replaces, AI-down fallback, exactly one repair call, owner-only 404s, cascade delete.
- All generated Mermaid text (normal, fallback and deliberately hostile input such as a class named `class`, quotes, `;`, `#`, `{}`, colons, unicode) passes the **real `mermaid.parse`** (run in Node). This found two real bugs (Mermaid keywords as class names, colons in labels), both fixed with regression tests.
- Use-case SVG rendered to an image and inspected by eye: clean, no overlaps.
- `npx vite build` passes.

### Not verified (owner please check)
- **Real browser:** Mermaid layout/appearance, PNG export, the Expand view and print layout have not been seen in a browser (the sandbox has none). Syntax is verified; visuals are not.
- **A real Gemini call** for diagrams. The schemas are flat like the SRS ones, but the first live run may show prompt/schema tweaks. The free tier is rate-limited: the job runs up to 4 AI calls in parallel and retries 3x, so on a free key some diagrams may come out as "Drawn from requirements" fallbacks. Use a paid key for the exhibition.
- Neon/PostgreSQL: the new `diagram_jobs` table is created by `create_all` (new table, no migration needed).

**Acceptance (still to do by hand):** for three different sample projects every diagram renders without overlapping labels and without errors; limits hold (limits are test-proven, overlap-free rendering of Mermaid needs your eyes).

---

## PHASE 4: SRS → Kanban

**Goal:** a *logical* board generated from requirements, replacing the flat generator.

- [x] New route `POST /boards/{id}/srs/generate-board`.
- [x] Mapping: one **column per phase** (Backlog, Ready, In Progress, Testing, Done); every task starts in Backlog/Ready (a new project has nothing done). Tasks come from FRs, grouped by use case; each task carries `acceptance_criteria` in its description, `priority` from MoSCoW (must→high, should→medium, could→low), the requirement ID in the title (e.g. `[FR-004] …`), and dependency notes.
- [x] Add optional fields to `Task`: `requirement_id`, `estimate_points`, `depends_on` (JSON list), plus `srs_id` (see deviations). Migration done by `app/core/migrate.py` at startup (and `backend/migrations/phase4_tasks.sql` for a manual run).
- [x] Reuse `save_project`'s all-or-nothing transaction idea but make the column lookup safe (columns are resolved case-insensitively; a failure rolls everything back).
- [x] Clicking a task in the UI shows its requirement and use case (traceability story for the exhibition).

### Built
**Backend**
- `services/board_planner.py`: PURE Python (no AI, no DB). `plan_board(requirements, include_nfr)` returns columns, tasks and warnings. Same input gives an identical plan. Also `plan_dependencies`, `has_cycle`, `estimate_points`.
- `services/board_service.py`: `generate_board` (one transaction, row lock against double clicks), `index_tasks` (best-effort Qdrant indexing so the RAG chat knows the new tasks), `task_trace`.
- `routes/srs_board.py`: `POST /boards/{id}/srs/generate-board` and `GET /boards/{id}/tasks/{task_id}/trace`, both owner-checked (404 for strangers).
- `schemas/board_gen.py`, `core/migrate.py`, `migrations/phase4_tasks.sql`, `models/task.py` (4 new nullable columns), `schemas/task.py` (`TaskResponse` extended), `main.py` (router + startup migration, failure is logged and never stops the API).
- `tests/test_board_gen.py` (44 tests).

**Frontend**
- `SrsStudio.jsx`: **Generate board** button (result step). On 409 a dialog offers *Add missing requirements* or *Replace the whole board* (two-step confirm). On success a summary (tasks, points, warnings) and *Open board*.
- `BoardDetail.jsx`: task cards show a points chip; the task panel shows story points plus a **Traceability** section: requirement statement and acceptance criteria, use case(s) with main flow, "Suggested to start after" with each dependency's live column and a "Waiting on N unfinished tasks" notice, "Unblocks", and an amber notice when the SRS has a newer version.

### How the board is built (rules, all in `board_planner.py`)
- Columns: Backlog, Ready, In Progress, Testing, Done. No task is ever planned into In Progress, Testing or Done.
- One task per FR, plus one per NFR (cross-cutting, Backlog; security/reliability = high, others medium; 3 points). `include_nfr=false` turns NFR tasks off.
- **Ready** = a MUST task with no dependencies. Everything else = Backlog.
- Order: by the first use case that covers the FR, then by ID; NFRs last. An FR no use case covers goes to "Unassigned" with a warning (it still becomes a task, so no `must` is lost).
- **Dependencies** are suggestions and come only from (1) another FR ID named in the requirement's own text and (2) the order of `fr_ids` inside a use case. Cycle-closing edges are dropped (warning if explicit). A derived edge is never created from a less important FR (e.g. `could`) to a more important one; an explicit one is kept but warned.
- **Story points** = 1 + acceptance criteria + 0.5 per dependency + 1 if the statement is long, snapped to 1/2/3/5/8. Relative sizes to edit, not a promise.
- **Modes** (`mode` in the request body): `create` (default; 409 if the board has any column, nothing is touched), `sync` (keeps every existing task untouched, adds tasks only for requirement IDs that have none; creates a standard column only if a new task needs it), `replace` (deletes ALL columns and tasks of this board, then rebuilds; UI asks twice).
- Duplicate or blank requirement IDs are skipped with a warning.

### Deviations from the original plan
- **4th column `srs_id`** on `tasks`. Without it the traceability panel cannot tell which SRS version a task came from once the SRS is edited. Plain nullable integer, no FK.
- **No AI and no background job.** The board is pure code (golden rule 1) and takes milliseconds, so the endpoint answers inside the request. Only the Qdrant indexing runs after the response (`BackgroundTasks`).
- **No dependency guessing from keywords.** An early idea ("everything for an actor depends on its Register/Login FR") was rejected: it would be an invented assumption (a public search page does not need login).
- **No Alembic yet** (see Phase 0). `core/migrate.py` is the stop-gap and is idempotent, including for two servers booting at once on PostgreSQL (`ADD COLUMN IF NOT EXISTS`).
- NFRs also become tasks (the plan only said FRs).
- Task create/edit routes are unchanged; hand-made tasks simply have NULL in the new columns.

### Verified
- `python -m pytest tests -q` → **91 passed** (47 old + 44 new). New tests cover: every `must` FR present; nothing starts in Done/Testing/In Progress; Ready rule; flow-order and explicit dependencies; self-reference; cycle breaking; 200-round random reference graphs never produce a cycle; priority-inversion rules; determinism; uncovered/duplicate/blank IDs; point values; title clipping; create/409/sync/replace; sync never modifies user-edited tasks and a second sync is a no-op; replace leaves other boards alone; damaged SRS → 422; empty SRS → 422; failure rolls back (also during replace, the old board survives); owner-only 404 on every new route; trace for FR / NFR / hand-made / removed requirement / SRS moved on / dependency moved; NULL `depends_on` from old rows; migration adds columns once and keeps rows; vector indexing success and failure never raise; Qdrant is not imported at module load.
- Mutation check: breaking the cycle guard, the Ready rule and the sync filter each made a test fail.
- **Startup migration proven on an old schema:** booted the real `app.main` (Qdrant/Gemini stubbed) against a database whose `tasks` table had no new columns: all four columns were added, an old row still loads, `/health` OK, both new endpoints appear in OpenAPI, a second boot adds nothing.
- `npx vite build` passes.
- UI logic checked with a throwaway jsdom script (not in the repo): trace panel for FR/NFR/removed/error/hand-made tasks, "waiting" banner and case-insensitive Done, newer-SRS notice, points chip, singular "1 story point", dialog states, Replace needs the second confirm click. 25 checks passed.

### Not verified (owner please check)
- **Real browser:** layout of the new dialog, task panel and chip, drag/drop with the new cards.
- **Neon/PostgreSQL:** `ADD COLUMN IF NOT EXISTS`, `SELECT … FOR UPDATE` and JSON columns use standard syntax but were only run on SQLite. Watch the first deploy log for "Added columns to tasks".
- **Real Qdrant + embeddings:** indexing is best-effort and only tested with fakes. If it fails, the board still works; the chat just will not know the new tasks (see the log).
- Real Gemini: Phase 4 makes no AI call, but Phases 1 to 3 have still never run against a real key. Do one real end-to-end run before building more on top.

**Acceptance (met in tests):** every `must` FR appears as at least one task; no task in Done on creation; dependencies never form a cycle (checked in code, with a final safety net). Still to do by hand: demo the flow on one real project in the browser.

---

## PHASE 5: Pakistan cost estimation

**Goal:** defensible PKR ranges using engineering economics.

- [x] `app/data/pk_rates.json`: salary range and allocation per role (junior/mid/senior dev, QA, UI/UX, PM, DevOps), overhead %, tax %, hosting/tool/one-time costs, contingency %, maintenance %, scenario settings, model constants. Every item has `source`, `last_updated`, `verified`. **ALL values currently ship as `verified: false` placeholders. The owner must replace them with current local data (job portals, PSEB/market surveys, software-house quotes, accountant for tax) and set `verified: true`.** The UI shows a warning while any item is unverified.
- [x] Effort model: function points counted from the SRS (FR weight 3/4/6 by acceptance criteria and statement length, entity weight 7/10/15 by attributes, 5 per external interface) -> KSLOC (45 LOC/FP, editable) -> COCOMO II (A=2.94, B=0.91, nominal scale factors, E=1.10) -> person-months and schedule (C=3.67, D=0.28). Inputs: platform, complexity, reliability, team experience.
- [x] Cross-checks: Use Case Points (independent person-months figure, flagged "close" if within 0.5x-2x) and board story points (shown as relative size, never hours).
- [x] Output: optimistic / likely / pessimistic (effort 0.8 / 1.0 / 1.5, salary at min / mid / max, all in the table), PERT `(O + 4M + P) / 6` for every line, cost per role, overhead, hosting/tools, contingency, tax, monthly burn, sensitivity table (salaries +/-20%, scope +/-30%, best and worst case; each row is a full recomputation), ROI / payback range / break-even / cumulative position when the user gives expected yearly revenue.
- [x] AI only explains: a deterministic template explanation is always stored; "Explain with AI" asks the model to write it from a flat `figures` dictionary. Code then rejects the AI text if it contains any number (other than whole numbers under 10) that is not in `figures`, and falls back to the template.
- [x] UI: **Cost** tab in SRS Studio (`components/CostPanel.jsx`): settings, range chart (SVG), tiles, money-split bar, per-role table, scenarios, sensitivity, ROI, explanation, assumptions, collapsible rate table with verified status, outdated-SRS banner, disclaimer, rate-table version and `last_updated` always visible.
- [x] Always shows `last_updated` and a disclaimer that figures are estimates.

### Built
**Backend:** `data/pk_rates.json`, `schemas/cost.py`, `services/cost_rates.py` (load + validate: allocations sum to 1, min <= max, all three scenarios, every item has a source), `services/cost_calculator.py` (PURE: no AI, no DB), `services/cost_service.py` (SRS load, estimate row, explanation + number guard, board-points cross-check, rate limits), `routes/cost.py`, `prompts/cost_prompt.py`, `CostEstimate` model (new table, created by `create_all`; cascade on board delete), fake LLM answer for `CostExplanation`, `tests/test_cost.py` (47 tests).
**Routes** (prefix `/boards/{board_id}/srs/cost`, owner-checked, 404 for strangers): `GET /rates`, `POST /estimate` (instant, no AI), `GET /` (latest, with `srs_outdated`), `POST /{estimate_id}/explain`.
**Limits:** 30 estimates and 10 AI explanations per user per hour.
**Frontend:** `components/CostPanel.jsx`, new tab in `SrsStudio.jsx`; the SRS Studio header now wraps on phones (it overflowed before).

### Deviations from the original plan
- COCOMO constants stay in code (published values); only business rates and model switches (LOC per FP, platform multipliers, hours per month, scenario factors) are in the table.
- No AI call and no background job for the numbers (milliseconds, golden rule 1). Estimates are saved as rows so the Cost tab reloads instantly.
- Break-even is shown in months from project start (build time + payback), not in units, because StackPilot does not know the product price.
- Scale factors are fixed at nominal; only complexity, reliability, team experience and platform are user inputs.

### Verified
- `python -m pytest tests -q` -> **138 passed** (91 old + 47 new). Includes: hand-calculated COCOMO and labour values, PERT formula, totals equal the sum of their lines in every scenario, determinism, changing a rate (salary, tax, contingency, hosting) changes the result, multiplier directions, sensitivity rows are real recomputations, ROI maths and the never-pays-back case, rate-table validation errors, AI number guard (invented numbers rejected, AI down gives 503 and the template stays usable), rate limits, ownership 404s, 401 unauthenticated, cascade delete, outdated-SRS flag, board-points cross-check.
- Mutation checks: breaking the PERT formula, the role allocation, or the tax each made a test fail (the allocation one first survived, so two hand-calculation tests were added).
- Cost tab rendered in headless Chromium with a mocked API at 1200 px and 390 px: all sections draw, no horizontal overflow, Explain button works, rate table opens. Screenshot reviewed by eye.
- `npx vite build` passes.

### Not verified (owner please check)
- **Rate values are placeholders.** The totals are only as good as `pk_rates.json`. The tax rate (16%) in particular differs by province.
- **Whether the COCOMO numbers feel right for your projects.** For the 8-requirement sample library system the engine gives about PKR 3.2 million expected (1.8 to 5.4 million range), 6.9 months, 2 people. Tune `loc_per_function_point` and the effort factors in the table if real projects you know come out very different.
- Real Gemini explanation (only the fake LLM was run); Neon/PostgreSQL for the new `cost_estimates` table (standard types, created by `create_all`); a real browser with a live backend (the browser check used mocked responses).

**Acceptance (met in tests):** same input always gives the same numbers; changing a rate changes the result; assumptions are visible.

---

## PHASE 6: Exhibition hardening

### Built in this phase
- [x] Added local fixtures for hospital, e-commerce, and university demos in `backend/app/data/demo_fixtures.json`.
- [x] Added public read-only `GET /demo/{name}` endpoint. It serves static data without Gemini, Qdrant, or database access.
- [x] Added three demo buttons in SRS Studio and an offline preview of SRS, requirement counts, diagram source, Kanban tasks, and illustrative cost.
- [x] Live question/SRS generation failures fall back to the hospital demo with an explicit explanation.
- [x] SRS generation polling switches to offline demo after 60 seconds. Note: the server-side job is not cancelled.
- [x] Reduced SRS and diagram generation job limits to 5 per user per hour; active-job reuse is retained.
- [x] Added a generic API exception handler that logs technical details server-side and returns a safe message. AI project route no longer returns raw exception strings.
- [x] Added `PHASE6_HANDOFF.md` with endpoint contract and manual QA checklist.

### Owner actions / not yet verified
- [ ] Run backend tests and frontend production build in the target environment.
- [ ] Click through all three demo previews on desktop and phone.
- [ ] Verify fallback with an intentionally unavailable Gemini API and simulate a 60-second job.
- [ ] Verify rate limits against a real test user and the production database.
- [ ] Complete a real end-to-end run with Gemini, Neon PostgreSQL, and Qdrant.
- [ ] Replace all `verified: false` placeholder values in `backend/app/data/pk_rates.json` with current, sourced Pakistan market data before using estimates as anything other than a demo.
- [ ] Set a low Gemini billing budget; rotate all previously exposed credentials.
- [ ] Deploy backend/frontend with correct `FRONTEND_ORIGINS`, HTTPS, and health checks.
- [ ] Record a 60-second backup video, prepare the pipeline poster, and rehearse the 3-minute script.

**Scope note:** Offline fallback is a standalone, clearly labelled preview; it does not insert fixture records into the user's board. The 60-second client timeout does not cancel an already-running server job.

---

## 3. Conventions

- Python 3.13, FastAPI, SQLAlchemy 2.x, Pydantic v2. LF line endings. Type hints on new functions.
- Routes stay thin; logic lives in `services/`.
- Return JSON error bodies shaped `{ "detail": "..." }`.
- Don't add libraries without a reason; prefer the standard library and what is already in `requirements.txt`.
- Frontend: React function components, Tailwind, axios instance from `src/api/axios.js`.

## 4. Environment variables

Required: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`.
New: `GEMINI_MODEL`, `FRONTEND_ORIGINS`, `LLM_FAKE` (optional, for tests/offline demo).
Frontend: `VITE_API_URL`.

## 5. Known limits of the work done so far

- Nothing has been run against the real database, Gemini or Qdrant. Only syntax checks were done on the Phase 0 edits.
- Model names and prices change often; verify `GEMINI_MODEL` and current pricing on Google's pricing page.
- Pakistan cost data in `pk_rates.json` is **placeholder only** (all `verified: false`). It must be sourced and verified by the developer.

---

## 6. Status Log (update before you stop)

| Date | Who | Phase | What changed | Next step |
|---|---|---|---|---|
| 2026-10-17 | Claude | 0 | Added `core/deps.py`; secured board/column/task routes; LF endings. Compile-checked. | (superseded below) |
| 2026-10-17 | Claude | 0 + 1 | Finished Phase 0 (ai/analysis/chat auth, CORS from env, single Gemini key + `GEMINI_MODEL`, safe column lookup, cleanup, `.env.example`). Built all of Phase 1. 13/13 tests pass (fake LLM, SQLite). Verified offline that the google-genai SDK accepts the `Requirements` and `QuestionList` schemas. **Not yet tested:** a real Gemini call, Neon/PostgreSQL, the old routes (board/column/task) against a real DB. | **Phase 3** (diagrams). Before that, the owner should run one real generation with a real key and report any schema/model errors. |
| 2026-10-17 | Claude | 2 | Built SRS Studio page (describe → questions → live progress → result with 4 tabs, version switch, inline edit, .md/.docx/print export), backend `.docx` export, route + launcher button, `VITE_API_URL`. 14/14 backend tests pass, `vite build` passes. | **Phase 3**: diagram schemas + validators + Mermaid conversion + ELK use-case renderer. Owner should first click through Phase 2 with a real key and report bugs. |
| 2026-10-17 | Claude | 3 | Built all of Phase 3: diagram schemas, code-enforced limits (validate -> one repair -> sanitize), Mermaid converters, custom use-case SVG renderer, deterministic AI-free fallbacks, background job with progress, stale-flag carry-over, Diagrams tab with SVG/PNG/Mermaid export and full-screen view. 47/47 backend tests pass, Mermaid output verified with the real parser, `vite build` passes. Not tested: browser visuals, real Gemini, Neon. | **Phase 4** (SRS -> Kanban). Needs an Alembic migration or manual `ALTER TABLE tasks` (adds `requirement_id`, `estimate_points`, `depends_on`). Owner should first click through the Diagrams tab with a real key and report anything ugly. |
| 2026-10-17 | Claude | 4 | Built all of Phase 4: deterministic planner (columns, MoSCoW priorities, acceptance criteria in descriptions, safe dependencies, story points), `generate-board` with create/sync/replace modes in one transaction, per-task trace endpoint, startup migration for 4 new `tasks` columns, best-effort Qdrant indexing, UI (Generate board dialog, points chip, Traceability panel). 91/91 backend tests pass, migration proven on an old-schema DB, `vite build` passes. Not tested: real browser, Neon, real Qdrant, real Gemini. | **Phase 5** (Pakistan cost estimation). The developer must supply/verify the rate table data (`pk_rates.json`) first. Before that, run one full real flow (describe → SRS → diagrams → board) in the browser with a real key and report anything ugly. |
| 2026-10-17 | Claude | 5 | Built all of Phase 5: validated PKR rate table (placeholders, flagged unverified), function-point + COCOMO II effort model, UCP and board-points cross-checks, O/L/P scenarios with PERT, per-role cost, sensitivity table, ROI/payback, cost explanation that the AI can only phrase (code rejects invented numbers), Cost tab with range chart. 138/138 backend tests pass, Cost tab checked in headless Chromium (desktop + phone), `vite build` passes. Not tested: real Gemini, Neon, live backend in a browser. | **Phase 6** (exhibition hardening). Before that the owner must replace the placeholder rates in `pk_rates.json` and run one full real flow (describe -> SRS -> diagrams -> board -> cost) with a real key. |
