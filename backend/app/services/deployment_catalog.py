"""Issue #7, Document tab: deployment suggestions, pricing and the final document.

Same golden rules as the cost engine: prices come from a maintained table
(app/data/deployment_services.json) with source / last_updated / verified, never from an AI guess,
and the document is rendered by code (deterministic, works with Wi-Fi or Gemini down)."""
import json
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "deployment_services.json"

STACK_OPTIONS = {
    "frontend": [("react", "React"), ("nextjs", "Next.js"), ("vue", "Vue"), ("angular", "Angular"),
                 ("svelte", "Svelte"), ("flutter_web", "Flutter web"), ("static", "Static HTML"), ("none", "None / no web front end")],
    "backend": [("fastapi", "FastAPI (Python)"), ("django", "Django (Python)"), ("express", "Express (Node.js)"),
                ("nestjs", "NestJS (Node.js)"), ("spring", "Spring Boot (Java)"), ("laravel", "Laravel (PHP)"), ("none", "None / front end only")],
    "database": [("postgresql", "PostgreSQL"), ("mysql", "MySQL"), ("mongodb", "MongoDB"), ("none", "None")],
    "scale": [("small", "Small"), ("medium", "Medium"), ("large", "Large")],
}
EXTRAS = [("load_balancer", "Load balancer"), ("api_gateway", "API gateway"), ("blockchain", "Blockchain node provider"),
          ("cache", "Cache (Redis)"), ("object_storage", "File / object storage"), ("cdn", "CDN"),
          ("vector_db", "Vector database (RAG)"), ("monitoring", "Monitoring"), ("ci_cd", "CI/CD pipeline"),
          ("email", "Transactional email")]
ENVIRONMENTS = ("development", "staging", "production")
CONTINGENCY = 0.15

FRONT_ENV = {"react": "VITE_API_URL", "vue": "VITE_API_URL", "svelte": "VITE_API_URL", "static": "API_BASE_URL (in the page config)",
             "nextjs": "NEXT_PUBLIC_API_URL", "angular": "apiUrl (in environment.ts)", "flutter_web": "API_BASE_URL (--dart-define)"}
BACK_ENV = {"fastapi": "ALLOWED_ORIGINS", "django": "ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS", "express": "CORS_ORIGIN",
            "nestjs": "CORS_ORIGIN", "spring": "app.cors.allowed-origins", "laravel": "APP_URL and CORS allowed origins"}


class CatalogError(Exception):
    pass


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    try:
        with open(CATALOG_PATH, encoding="utf-8") as f:
            cat = json.load(f)
    except (OSError, ValueError) as e:
        raise CatalogError(f"The service price table could not be read: {e}")
    ids = [s["id"] for s in cat["services"]]
    if len(ids) != len(set(ids)):
        raise CatalogError("Duplicate service ids in the price table.")
    for s in cat["services"]:
        if s["category"] not in cat["categories"] or set(s["plans"]) != {"small", "medium", "large"}:
            raise CatalogError(f"Service {s['id']} is malformed.")
    return cat


def option_values(kind: str) -> set[str]:
    return {v for v, _ in STACK_OPTIONS[kind]}


def needed_categories(stack: dict) -> list[str]:
    cats = []
    if stack["frontend"] != "none":
        cats.append("frontend_hosting")
    if stack["backend"] != "none":
        cats.append("backend_hosting")
    if stack["database"] != "none":
        cats.append("database_hosting")
    cats += [c for c, _ in EXTRAS if c in stack.get("extras", [])]
    return cats


_FITS_KEY = {"frontend_hosting": "frontend", "backend_hosting": "backend", "database_hosting": "database"}


def _fits(service: dict, stack: dict) -> bool:
    key = _FITS_KEY.get(service["category"])
    allowed = service.get("fits", {}).get(key) if key else None
    return allowed is None or stack[key] in allowed


def _price(service: dict, scale: str, cat: dict) -> dict:
    plan, usd = service["plans"][scale]
    fx = cat["currency"]["usd_to_pkr"]
    status = cat["pricing_status"]
    return {"service_id": service["id"], "name": service["name"], "category": service["category"],
            "plan": plan, "monthly_usd": usd, "monthly_pkr": round(usd * fx), "why": service["why"],
            "hint": service["hint"], "url": service["url"],
            "verified": service.get("verified", status["verified"]),
            "source": service.get("source", status["source"]),
            "last_updated": service.get("last_updated", status["last_updated"])}


def suggest(stack: dict, cat: dict | None = None) -> list[dict]:
    """For each layer the stack needs: the options that fit, best first. The first is `recommended`."""
    cat = cat or load_catalog()
    out = []
    for c in needed_categories(stack):
        options = sorted((s for s in cat["services"] if s["category"] == c and _fits(s, stack)),
                         key=lambda s: (s["rank"], s["plans"][stack["scale"]][1]))
        priced = [{**_price(s, stack["scale"], cat), "recommended": i == 0} for i, s in enumerate(options)]
        out.append({"category": c, "label": cat["categories"][c], "options": priced})
    return out


def resolve_selection(stack: dict, selected: dict, cat: dict | None = None) -> list[dict]:
    """Check the user's final choice and price it. Raises ValueError with a message safe to show."""
    cat = cat or load_catalog()
    needed = needed_categories(stack)
    unknown = [k for k in selected if k not in needed]
    if unknown:
        raise ValueError(f"These layers are not part of your stack: {', '.join(sorted(unknown))}.")
    missing = [cat["categories"][c] for c in needed if c not in selected]
    if missing:
        raise ValueError(f"Choose a service for: {', '.join(missing)}.")
    by_id = {s["id"]: s for s in cat["services"]}
    out = []
    for c in needed:
        s = by_id.get(selected[c])
        if not s or s["category"] != c or not _fits(s, stack):
            raise ValueError(f"That service is not available for {cat['categories'][c]} with this stack.")
        out.append(_price(s, stack["scale"], cat))
    return out


def totals(resolved: list[dict], cat: dict | None = None) -> dict:
    cat = cat or load_catalog()
    usd = sum(r["monthly_usd"] for r in resolved)
    fx = cat["currency"]["usd_to_pkr"]
    return {"monthly_usd": usd, "monthly_pkr": round(usd * fx), "yearly_usd": usd * 12, "yearly_pkr": round(usd * 12 * fx),
            "monthly_with_contingency_pkr": round(usd * fx * (1 + CONTINGENCY)), "usd_to_pkr": fx,
            "unverified_count": sum(1 for r in resolved if not r["verified"]), "service_count": len(resolved)}


def env_vars(stack: dict, resolved: list[dict]) -> list[tuple[str, str, str]]:
    """(name, where it is set, what it is for)."""
    have = {r["category"] for r in resolved}
    rows = []
    if stack["backend"] != "none":
        rows += [("SECRET_KEY", "Backend", "Signs login tokens. Long random value, never committed to Git."),
                 (BACK_ENV[stack["backend"]], "Backend", "Allows only your real front-end address to call the API.")]
        if stack["database"] != "none":
            rows.append(("DATABASE_URL", "Backend", "Connection string of the production database."))
    if stack["frontend"] != "none":
        rows.append((FRONT_ENV[stack["frontend"]], "Frontend (build time)", "Public address of the backend API."))
    extra = {"cache": ("REDIS_URL", "Cache connection string."), "blockchain": ("BLOCKCHAIN_RPC_URL", "Node provider endpoint including its key."),
             "vector_db": ("QDRANT_URL and QDRANT_API_KEY", "Vector database address and key."),
             "email": ("EMAIL_API_KEY", "Key of the email service; the sending domain must be verified."),
             "object_storage": ("STORAGE_BUCKET and STORAGE_KEY", "Bucket name and access credentials."),
             "monitoring": ("SENTRY_DSN (or the monitoring agent key)", "Where errors and metrics are sent.")}
    rows += [(n, "Backend", d) for c, (n, d) in extra.items() if c in have]
    return rows


ARCH_ORDER = ["cdn", "load_balancer", "api_gateway", "frontend_hosting", "backend_hosting", "cache", "database_hosting",
              "vector_db", "object_storage", "blockchain", "email"]
STEP_ORDER = ["database_hosting", "cache", "vector_db", "object_storage", "blockchain", "email", "backend_hosting",
              "frontend_hosting", "load_balancer", "api_gateway", "cdn", "ci_cd", "monitoring"]


def render_document(project: str, stack: dict, resolved: list[dict], tot: dict, *, version: int, generated_on: str,
                    domain: str | None, environments: list[str], notes: str | None, cat: dict | None = None) -> str:
    cat = cat or load_catalog()
    label = lambda kind, v: dict(STACK_OPTIONS[kind]).get(v, v)
    by_cat = {r["category"]: r for r in resolved}
    L: list[str] = []
    a = L.append

    a(f"# Deployment Document: {project}\n")
    a(f"*Version {version} · generated {generated_on}*\n")
    a("## 1. Overview\n")
    a(f"- **Project:** {project}")
    a(f"- **Expected scale:** {cat['scales'][stack['scale']]}")
    a(f"- **Environments:** {', '.join(environments)}")
    a(f"- **Domain:** {domain or 'not decided yet'}\n")

    a("## 2. Technology stack\n")
    a("| Layer | Choice |\n|---|---|")
    a(f"| Frontend | {label('frontend', stack['frontend'])} |")
    a(f"| Backend | {label('backend', stack['backend'])} |")
    a(f"| Database | {label('database', stack['database'])} |")
    for c, name in EXTRAS:
        if c in stack.get("extras", []):
            a(f"| {name} | Included |")
    a("")

    a("## 3. Selected services and monthly cost\n")
    a("| Layer | Service | Plan | USD / month | PKR / month |\n|---|---|---|---:|---:|")
    for r in resolved:
        a(f"| {cat['categories'][r['category']]} | {r['name']} | {r['plan']} | {r['monthly_usd']:,.0f} | {r['monthly_pkr']:,} |")
    a(f"| **Total** | | | **{tot['monthly_usd']:,.0f}** | **{tot['monthly_pkr']:,}** |\n")
    a(f"Yearly: about USD {tot['yearly_usd']:,.0f} (PKR {tot['yearly_pkr']:,}). With a {int(CONTINGENCY * 100)}% contingency, "
      f"plan for about PKR {tot['monthly_with_contingency_pkr']:,} per month. Exchange rate used: 1 USD = PKR {tot['usd_to_pkr']}.\n")
    if tot["unverified_count"]:
        a(f"> **Pricing warning:** {tot['unverified_count']} of {tot['service_count']} prices are approximate and not yet verified. "
          "Check each vendor's pricing page (listed in section 9) before quoting a client.\n")

    a("## 4. Architecture overview\n")
    chain = [by_cat[c]["name"] for c in ARCH_ORDER if c in by_cat]
    a("Request path and supporting services, from the user inward:\n")
    a("**Users** → " + " → ".join(f"**{n}**" for n in chain) if chain else "No hosted services were selected.")
    a("")

    a("## 5. Configuration\n")
    a("Set these as environment variables or secrets in the hosting dashboards. Never commit real values to Git.\n")
    a("| Variable | Where | Purpose |\n|---|---|---|")
    for n, where, why in env_vars(stack, resolved):
        a(f"| `{n}` | {where} | {why} |")
    a("")

    a("## 6. Deployment steps\n")
    n = 1
    for c in STEP_ORDER:
        if c in by_cat:
            r = by_cat[c]
            a(f"{n}. **{cat['categories'][c]}: {r['name']} ({r['plan']}).** {r['hint']}")
            n += 1
    if stack["backend"] != "none" and stack["database"] != "none":
        a(f"{n}. **Run database migrations** against the production database before the first release.")
        n += 1
    a(f"{n}. **Point the domain** ({domain or 'your domain'}) to the services, enable HTTPS and set the allowed origins to the real front-end address.")
    a(f"{n + 1}. **Smoke test** the health endpoint, sign-in and one complete user flow in each environment.\n")

    a("## 7. Operations\n")
    a("- **Backups:** enable automatic database backups and test one restore before launch." if stack["database"] != "none" else "- **Backups:** back up any data you store elsewhere.")
    a("- **Rollback:** keep the previous release available and redeploy it if the smoke test fails.")
    a("- **Secrets:** rotate keys whenever a team member leaves or a key is exposed.")
    a("- **Monitoring:** " + (f"{by_cat['monitoring']['name']} is selected; add alerts for errors and downtime." if "monitoring" in by_cat else "no monitoring service was selected; at least add an uptime check on the health endpoint."))
    a("")

    a("## 8. Cost summary and assumptions\n")
    a(f"- Monthly infrastructure cost: **PKR {tot['monthly_pkr']:,}** (USD {tot['monthly_usd']:,.0f}).")
    a(f"- Plans were chosen for the **{stack['scale']}** scale; move up a plan if traffic grows.")
    a("- Prices exclude tax, domain registration, staff time and usage beyond each plan's included limits.\n")

    a("## 9. Price sources\n")
    a("| Service | Source page | Verified | Last updated |\n|---|---|---|---|")
    for r in resolved:
        a(f"| {r['name']} | {r['url']} | {'yes' if r['verified'] else 'no'} | {r['last_updated']} |")
    a("")

    if notes and notes.strip():
        a("## 10. Additional notes\n")
        a(notes.strip() + "\n")
    return "\n".join(L)
