# StackPilot Phase 6 — Exhibition Hardening

## What changed

- Added read-only `GET /demo/{name}` fixtures for `hospital`, `ecommerce`, and `university`. The endpoint reads local JSON and does not call Gemini, Qdrant, or the database.
- Added a Demo mode in SRS Studio with one-click sample loading. It displays a sample SRS, requirement counts, diagram source previews, Kanban tasks, and clearly labelled illustrative PKR estimates.
- Live question/SRS generation failures now fall back to the hospital demo. A live SRS job that remains in progress for over 60 seconds switches to the same offline example.
- Reduced SRS and diagram generation job limits to 5 per user per hour. Existing active-job reuse remains in place.
- Added a generic FastAPI exception handler: technical details are logged server-side and a safe message is returned to visitors.
- Removed raw exception text from the AI project generation/save route responses.
- Added this handoff plan and a manual exhibition checklist.

## Demo endpoint contract

`GET /demo/hospital`
`GET /demo/ecommerce`
`GET /demo/university`

Returns `name`, `title`, `description`, `requirements`, `issues`, `markdown`, `diagrams`, `board`, and `cost`. Unknown demo names return 404. Fixture estimates are illustrative only and must not be represented as verified Pakistani market pricing.

## Important limitation

The offline fallback is a standalone exhibition preview. It does **not** create a persisted SRS/diagram/board/cost record on the user's real board. This avoids silently inserting canned sample data into user-owned projects. If a generation fails, the UI explicitly labels the preview as offline demo data.

The 60-second timeout is enforced by the SRS Studio polling client. It does not cancel a server-side background job; a timed-out job may finish on the server. Active-job reuse prevents an immediate duplicate generation for that board.

## Manual verification checklist

- [ ] Start backend with valid required environment variables.
- [ ] `GET /demo/hospital`, `/demo/ecommerce`, `/demo/university` each return 200 without Gemini credentials being used.
- [ ] `GET /demo/not-a-demo` returns a safe 404.
- [ ] Open SRS Studio and click all three demo buttons; check mobile and desktop layouts.
- [ ] Disable network access to Gemini or use an invalid key; verify question generation failure shows the offline demo.
- [ ] Simulate a job lasting over 60 seconds; verify the offline preview appears.
- [ ] Verify a sixth SRS or diagram generation request within one hour is rate-limited for that user, unless it reuses an active job.
- [ ] Confirm unexpected backend exceptions return a safe message while details remain in server logs.
- [ ] Run `cd backend && python -m pytest tests -q`.
- [ ] Run `cd frontend && npm ci && npm run build`.
- [ ] Complete one real end-to-end run with Gemini, Neon PostgreSQL, and Qdrant before the exhibition.
- [ ] Replace all unverified placeholders in `backend/app/data/pk_rates.json` with sourced, current values; only then set `verified: true`.
- [ ] Set a billing budget on the Gemini key, rotate all previously exposed credentials, configure `FRONTEND_ORIGINS`, and deploy HTTPS.
- [ ] Record the 60-second backup video and prepare the one-page pipeline poster.

## Security and deployment reminders

- Never place `.env`, credentials, virtual environments, `node_modules`, or Python cache files in the ZIP.
- Keep the public demo endpoint limited to static fixtures. Do not add database access or AI calls to it.
- The generic exception handler is a final safety net; route-specific validation and HTTP errors should continue to return intentional status codes.
- Existing project routes still require real environment/database setup; the offline demo route itself is static.

## Phase 7 candidate (ask owner before starting)

Potential next phase: Exhibition QA and deployment validation — run the complete app against real services, verify the production migration and CORS configuration, fix any live integration issues, validate actual browser diagrams/export/print, verify cost rates, and rehearse the presentation. Do not start Phase 7 until the owner reviews this ZIP and explicitly asks to continue.
