# StackPilot: Optimization Recommendations

> Ratings are estimates based on the code and docs seen so far (Dashboard.jsx, analysis_service.py, analysis route, build plan). **Measure first**: items marked *(needs confirmation)* depend on files not yet reviewed (`core/database.py`, list routes in `board.py` / `column.py` / `task.py`, hosting setup).

## How to read the ratings

- **Impact:** how much faster the thing users feel gets. ★★★★★ = fixes the main problem, ★ = barely noticeable.
- **Effort:** S = under an hour, M = a few hours to a day, L = multi-day.
- **Risk:** chance of breaking working features before the exhibition (Low / Med / High).

## 1. Summary table

| # | Optimization | Targets | Impact | Effort | Risk | Do it? |
|---|---|---|---|---|---|---|
| 1 | Neon cold start mitigation | First load after idle | ★★★★★ *(needs confirmation)* | S | Low | **Yes, first** |
| 2 | Dashboard summary endpoint (1 request, counts only) | Dashboard load | ★★★★☆ | S | Low | **Yes** |
| 3 | Fix DB connection pool settings | Intermittent slow/failed requests | ★★★☆☆ | S | Low | **Yes** |
| 4 | Co-locate backend and Neon region | Every request | ★★★★☆ *(needs confirmation)* | S-M | Low | **Yes** |
| 5 | Add indexes on foreign keys | List and join queries as data grows | ★★★☆☆ | S | Low | **Yes** |
| 6 | Fix N+1 / Python-side filtering in list routes | Boards, columns, tasks lists | ★★★★☆ *(needs confirmation)* | M | Low | **Yes** after review |
| 7 | Frontend: cached stats + skeleton | Perceived speed | ★★★★☆ (perceived) | S | Low | **Yes** |
| 8 | Lazy-load embedding model; `HF_HUB_OFFLINE=1` | Backend startup, `--reload`, import failures | ★★★★☆ (startup only) | S | Low | **Yes** |
| 9 | Backend hosting cold start (serverless) | First request after idle | ★★★★☆ *(needs confirmation)* | M | Med | Check |
| 10 | Replace torch + sentence-transformers with Gemini embeddings | Deploy size, cold start, memory | ★★★☆☆ | M-L | Med | Later |
| 11 | Reduce per-request auth overhead | Every request | ★★☆☆☆ | S | Low | Optional |
| 12 | Pagination on list endpoints | Large accounts | ★★☆☆☆ now, ★★★★☆ later | M | Low | Later |
| 13 | GZip response compression | Large JSON (SRS, diagrams) | ★★☆☆☆ | S | Low | Optional |
| 14 | Analysis page: reuse client, use `llm_json`, cache result | `/boards/{id}/analyze` | ★★★☆☆ | S-M | Low | Yes |
| 15 | Route-level code splitting (`React.lazy`) | First page load | ★★☆☆☆ | S | Low | Optional |
| 16 | Async SQLAlchemy + asyncpg | Concurrency under load | ★☆☆☆☆ for a single page | L | **High** | **No (not now)** |
| 17 | Redis (cache, rate limits, queue backing) | Multi-instance scale | ★☆☆☆☆ now | M | Med | **No (not now)** |
| 18 | Job queue (Celery/ARQ/RQ) | Job durability | ★☆☆☆☆ now | L | Med | **No (not now)** |

## 2. Details

### 1. Neon cold start mitigation: ★★★★★ / S / Low
Neon suspends idle compute and wakes it on the next query, adding seconds to the first request. Likely the biggest cause of "dashboard takes a while".
- Disable or lengthen autosuspend (plan-dependent; free tier may not allow disabling it).
- Keep it warm: ping a DB-touching endpoint every 3-4 minutes before and during the exhibition (cron job or uptime monitor).
- Use the `-pooler` connection host.
- Add `pool_pre_ping=True` so connections killed by suspend don't cause errors on the next request.
- Exhibition tip: open the app 10 minutes before and click through once.

### 2. Dashboard summary endpoint: ★★★★☆ / S / Low
`Dashboard.jsx` downloads every board, column and task just to show three counts and four recent boards. Replace the three calls with `GET /dashboard/summary` returning counts and the last 4 boards, computed with `COUNT` in one query. Fewer requests, fewer auth lookups, much smaller payloads, and the user-scoping lives in SQL.

### 3. Connection pool settings: ★★★☆☆ / S / Low
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=5,
)
```
A pool of 1, or no pool, forces parallel requests to queue. *(Check `core/database.py`.)*

### 4. Region co-location: ★★★★☆ / S-M / Low
Each request makes several DB round trips (auth lookup plus data). If the backend host and the Neon project are on different continents, every round trip costs 100-250 ms. Put both in the same region (and close to your users) and note that the browser-to-backend distance matters too.

### 5. Foreign key indexes: ★★★☆☆ / S / Low
PostgreSQL does not index foreign keys automatically. Check that these are indexed: `boards.user_id`, `columns.board_id`, `tasks.column_id`, `srs_documents.board_id`, `diagrams.srs_id`, `cost_estimates.board_id`, `srs_jobs.board_id`. Add with `index=True` on the model column and a one-off `CREATE INDEX IF NOT EXISTS` in `migrate.py`. Small gain today, large gain with more data.

### 6. N+1 queries and Python-side filtering: ★★★★☆ / M / Low
Look in `routes/board.py`, `column.py`, `task.py` for: loops that query per board or per column, `.all()` followed by Python filtering, and relationship access inside loops. Fix with a single filtered query, joins, or `selectinload`. Also confirm list routes filter by the current user in SQL and never return other users' rows.

### 7. Frontend perceived speed: ★★★★☆ / S / Low
- Show the last known stats from `sessionStorage` immediately, refresh in the background (stale-while-revalidate).
- Keep skeleton cards (already present).
- Prefetch the Boards list when the dashboard loads.

### 8. Lazy-load embedding model: ★★★★☆ (startup) / S / Low
`rag/embedding_service.py` builds `SentenceTransformer(...)` at import. This slows every start and every `--reload`, and a network or SSL error takes down the whole API (as happened). Load it on first use inside `create_embedding`, and set `HF_HUB_OFFLINE=1` once the model is cached so it never needs the network. Does not speed up requests, but removes the biggest startup cost and failure point.

### 9. Hosting cold start: ★★★★☆ / M / Med *(needs confirmation)*
Both `backend/vercel.json` and `frontend/vercel.json` exist, while the frontend default points to a Railway URL. Confirm where the backend runs. On a serverless platform, loading torch and sentence-transformers makes cold starts very slow and may exceed size limits. An always-on host (Railway, Render, Fly, a VPS) avoids this for the exhibition.

### 10. Gemini embeddings instead of local model: ★★★☆☆ / M-L / Med
Removes torch and sentence-transformers (about 2 GB installed), shrinks the deploy and cuts cold start. Cost: vector dimensions change, so Qdrant collections must be re-created and tasks re-indexed. Also noted in the Phase 0 plan. Do it after the exhibition.

### 11. Auth overhead: ★★☆☆☆ / S / Low
`get_current_user` queries the database on every request. Acceptable for now. If profiling shows it matters, keep the user id and email in the JWT claims for routes that don't need the full row, or add a short in-process TTL cache (no Redis required).

### 12. Pagination: ★★☆☆☆ now / M / Low
Add `limit` and `offset` (or cursor) to list endpoints once accounts have hundreds of tasks. Not needed for the demo.

### 13. GZip: ★★☆☆☆ / S / Low
`app.add_middleware(GZipMiddleware, minimum_size=1000)` helps SRS Markdown, diagram JSON and task lists. Many hosts already compress; check before adding.

### 14. Analysis endpoint: ★★★☆☆ / S-M / Low
The LLM call dominates the time. Improvements: reuse the single client through `core/llm.py` (golden rule 4), use `llm_json` with a response schema instead of stripping code fences and calling `json.loads`, and cache the result per board until tasks change (store a hash of the board state). Also show a progress state in `ProjectAnalysis.jsx`, since this call is inherently slow.

### 15. Code splitting: ★★☆☆☆ / S / Low
Wrap page imports in `React.lazy` so Landing and Login don't download SRS Studio and the cost UI. Mermaid is already a lazy chunk.

### 16. Async SQLAlchemy: ★☆☆☆☆ / L / High
Helps only when many requests are in flight at once. Does not speed up one dashboard load. Requires rewriting nearly every Python file (routes, services, `deps.py`, `get_current_user`, background jobs, tests), switching to `asyncpg`, eager loading everywhere, and making Gemini, Qdrant, embedding and email calls non-blocking. The frontend is unaffected. Revisit only if you see real concurrency problems after the cheaper fixes.

### 17. Redis: ★☆☆☆☆ now / M / Med
Useful for shared rate-limit counters, caches across multiple instances, or a job queue backend. With one backend instance it adds another service to host and fail. Revisit when you run more than one instance or hit a measured hot read path.

### 18. Job queue: ★☆☆☆☆ now / L / Med
`BackgroundTasks` plus status rows is enough for the demo. A restart mid-job loses that job, and the 60-second fallback covers the experience. Adopt a queue only when job loss or long jobs become a real problem.

## 3. Recommended order

1. **Measure** (10 minutes): browser DevTools waterfall plus the cold-start test below.
2. **Quick wins (one afternoon):** #1, #3, #5, #7, #8.
3. **Dashboard fix:** #2, then #6 after reviewing the list routes.
4. **Infrastructure check:** #4 and #9 (region and hosting).
5. **After the exhibition:** #10, #12, #14, #15, #11.
6. **Only if measurements demand it:** #16, #17, #18.

## 4. How to measure

- **Waterfall:** DevTools → Network → reload the dashboard. Note start time, wait (TTFB) and size of each request.
- **Cold start test:** leave the app idle for over 5 minutes (check the compute status in the Neon console), then time the first dashboard load. Reload immediately and compare. A big gap means cold start.
- **Server timing:** log query counts and durations per request (SQLAlchemy `echo=True` locally, or event listeners) to spot N+1 patterns.
- **Record before and after** each change in this file so the improvement is visible and you know what actually helped.
