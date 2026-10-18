"""Deterministic (AI-free) design builder, plus the mechanical table builder used by the sanitizer.

Used when the AI is unavailable. Produces a standard layered design from the SRS alone:
    WebClient -> RestApi -> <Entity>Service ... -> DataAccess (Repository) , + one Adapter per external interface.
Everything it produces is derived from the requirements; it never invents technologies."""
import re

from app.schemas.sdd import (
    MAX_COMPONENTS, MAX_ENDPOINTS, MAX_TABLES, MAX_TECH, Component, DesignDecision, DesignModel, Endpoint,
    QualityTactic, TableDesign, TechChoice,
)
from app.schemas.srs import Entity, Requirements

MAX_ENTITY_SERVICES = 6
MAX_ADAPTERS = 3
_STOP = {"for", "the", "a", "an", "to", "and", "of", "via", "with", "by", "in", "on"}


# ------------------------------------------------------------------ naming
def _words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", s or "")


def snake(s: str) -> str:
    return "_".join(w.lower() for w in _words(re.sub(r"([a-z])([A-Z])", r"\1 \2", s or ""))) or "item"


def slug(s: str) -> str:
    return snake(s).replace("_", "-")


def pascal(s: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in _words(s)) or "Item"


def singular(w: str) -> str:
    w = w.lower()
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("ses") or w.endswith("xes"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def plural(w: str) -> str:
    w = w.lower()
    if w.endswith("y") and w[-2:-1] not in "aeiou":
        return w[:-1] + "ies"
    if w.endswith(("s", "x", "ch", "sh")):
        return w + "es"
    return w + "s"


# ------------------------------------------------------------------ tables
_TYPE_WORDS = {"string": "VARCHAR(255)", "text": "TEXT", "integer": "INTEGER", "int": "INTEGER", "number": "INTEGER",
               "date": "DATE", "datetime": "TIMESTAMP", "timestamp": "TIMESTAMP", "decimal": "NUMERIC(12,2)",
               "float": "NUMERIC(12,2)", "money": "NUMERIC(12,2)", "boolean": "BOOLEAN", "bool": "BOOLEAN"}


def _sql_type(col: str, declared: str) -> str:
    if declared.lower() in _TYPE_WORDS:
        return _TYPE_WORDS[declared.lower()]
    c = col.lower()
    if c.endswith(("_at", "_on")) or c in ("date", "created", "updated"):
        return "TIMESTAMP"
    if c.startswith(("is_", "has_")):
        return "BOOLEAN"
    if any(k in c for k in ("price", "fee", "fine", "amount", "total", "cost", "balance")):
        return "NUMERIC(12,2)"
    if any(k in c for k in ("count", "copies", "quantity", "qty", "number", "points", "stock", "age")):
        return "INTEGER"
    if any(k in c for k in ("description", "notes", "comment", "address", "body", "content")):
        return "TEXT"
    if "status" in c or "state" in c or "role" in c:
        return "VARCHAR(30)"
    return "VARCHAR(255)"


def _foreign_keys(entity: Entity, all_entities: list[Entity]) -> list[str]:
    """FK columns for `entity`, read from relation strings like 'Member has many Loan' / 'Loan belongs to Member'."""
    names = {e.name.lower(): e for e in all_entities}
    fks: dict[str, str] = {}
    me = entity.name.lower()
    for other in all_entities:
        for rel in other.relations:
            m = re.match(r"^\s*(\w+)\s+has\s+(?:many|one|a|an)\s+(\w+)", rel, re.I)
            if m and m.group(2).lower() == me and m.group(1).lower() in names:
                parent = names[m.group(1).lower()]
                fks[f"{snake(parent.name)}_id"] = plural(snake(parent.name))
    for rel in entity.relations:
        m = re.match(r"^\s*(\w+)\s+belongs\s+to\s+(?:a|an|one)?\s*(\w+)", rel, re.I)
        if m and m.group(1).lower() == me and m.group(2).lower() in names:
            parent = names[m.group(2).lower()]
            fks[f"{snake(parent.name)}_id"] = plural(snake(parent.name))
    return [f"{col}: INTEGER NOT NULL REFERENCES {tbl}(id)" for col, tbl in fks.items()]


def table_from_entity(entity: Entity, all_entities: list[Entity]) -> TableDesign:
    table = plural(snake(entity.name))
    cols = ["id: SERIAL PRIMARY KEY"]
    seen = {"id"}
    for raw in entity.attributes:
        name, _, declared = raw.partition(":")
        col = snake(name)
        if col in seen:
            continue
        seen.add(col)
        spec = f"{col}: {_sql_type(col, declared.strip())}"
        if "email" in col:
            spec += " UNIQUE NOT NULL"
        cols.append(spec)
    indexes = []
    for fk in _foreign_keys(entity, all_entities):
        col = fk.split(":")[0]
        if col not in seen:
            seen.add(col)
            cols.append(fk)
            indexes.append(f"idx_{table}_{col} ({col})")
    return TableDesign(entity=entity.name, table=table, columns=cols, indexes=indexes,
                       notes="Derived mechanically from the SRS entity; review types and constraints.")


# --------------------------------------------------------------- endpoints
_GET = {"search", "view", "list", "browse", "track", "read", "check", "display", "show", "see", "find", "export", "download", "report"}
_DELETE = {"remove", "delete", "cancel", "withdraw"}
_PUT = {"edit", "update", "modify", "change", "manage", "maintain", "configure"}
_PATCH = {"deactivate", "activate", "approve", "reject", "assign", "close", "reopen", "suspend"}
_PUBLIC = {"register", "login", "log", "sign", "signup", "reset", "recover"}


def _verb(title: str) -> str:
    w = _words(title)
    return w[0].lower() if w else ""


def _method(title: str) -> str:
    v = _verb(title)
    return "GET" if v in _GET else "DELETE" if v in _DELETE else "PUT" if v in _PUT else "PATCH" if v in _PATCH else "POST"


# ------------------------------------------------------------ NFR tactics
_TACTICS = {
    "performance": ("Index frequently queried columns, paginate list endpoints and cache read-heavy lookups.", ("data", "service")),
    "security": ("Hash passwords with a salted adaptive algorithm, authenticate with expiring tokens, enforce role-based access on every endpoint and serve all traffic over HTTPS.", ("api", "service")),
    "usability": ("Provide a responsive interface with consistent navigation and clear, actionable error messages.", ("presentation",)),
    "reliability": ("Validate all input, wrap multi-step writes in transactions, schedule database backups and expose a health-check endpoint.", ("service", "data")),
    "maintainability": ("Keep layers separate, inject dependencies instead of constructing them, and cover services with automated tests.", ("api", "service")),
    "compatibility": ("Expose a versioned REST/JSON API and target current evergreen browsers.", ("presentation", "api")),
    "scalability": ("Keep the API stateless so instances can be added behind a load balancer, and pool database connections.", ("api", "service", "data")),
}


def _is_public(title: str) -> bool:
    return bool(set(w.lower() for w in _words(title)) & _PUBLIC)


# ------------------------------------------------------------------ design
def build_design(req: Requirements, ctx: dict | None = None) -> DesignModel:
    ctx = ctx or {}
    comps: list[Component] = []

    def add(name, layer, resp, pattern, frs=(), ents=(), deps=()) -> Component:
        c = Component(id=f"CMP-{len(comps) + 1:03d}", name=name, layer=layer, responsibility=resp, pattern=pattern,
                      fr_ids=list(frs), entities=list(ents), depends_on=list(deps))
        comps.append(c)
        return c

    web = add("WebClient", "presentation", "Renders screens for every actor and sends user actions to the REST API.", "MVC")
    api = add("RestApi", "api", "Authenticates callers, validates requests and routes them to the business services.", "Facade")
    web.depends_on = [api.id]

    # --- allocate each FR to the entity service whose entity it mentions most ------------
    entities = req.entities
    primary = entities[:MAX_ENTITY_SERVICES]
    owner: dict[str, str | None] = {}
    for f in req.functional_requirements:
        title = f.title.lower()
        # the actor's own name must not count as a mention of an entity (a "Member" is an actor here)
        statement = re.sub(re.escape(f.actor.lower()), " ", f.statement.lower()) if f.actor else f.statement.lower()
        best, score = None, 0
        for e in primary:
            names = {e.name.lower(), singular(e.name)}
            attr_words = {w.lower() for a in e.attributes for w in _words(a.partition(":")[0]) if len(w) > 3}
            s = sum(3 * title.count(n) + statement.count(n) for n in names)
            s += sum(2 for w in attr_words if w in title or w in statement)
            if s > score:
                best, score = e.name, s
        owner[f.id] = best

    services: dict[str, Component] = {}
    for e in primary:
        frs = [f.id for f in req.functional_requirements if owner[f.id] == e.name]
        if frs:
            services[e.name] = add(f"{pascal(e.name)}Service", "service",
                                   f"Implements the business rules for {e.name}: {e.description}".strip(),
                                   "Service Layer", frs, [e.name])
    leftovers = [f.id for f in req.functional_requirements if owner[f.id] is None]
    extra_entities = [e.name for e in entities[MAX_ENTITY_SERVICES:]]
    if leftovers or extra_entities or not services:
        core = add("CoreService", "service", "Implements business rules that do not belong to a single entity.",
                   "Service Layer", leftovers, extra_entities)
        services["__core__"] = core

    data = add("DataAccess", "data", "Persists and retrieves all entities through repositories inside one transaction boundary.",
               "Repository", ents=[e.name for e in entities])

    adapters: list[Component] = []
    for text in req.external_interfaces[:MAX_ADAPTERS]:
        words = [w for w in _words(re.sub(r"\(.*?\)", "", text)) if w.lower() not in _STOP]
        label = pascal(" ".join(words[:2])) + "Adapter"
        adapters.append(add(label, "integration", f"Wraps the external interface: {text.strip()}", "Adapter"))

    for s in services.values():
        s.depends_on = [data.id]
    api.depends_on = [s.id for s in services.values()]
    # an adapter is called by the service whose requirements mention one of the interface's key words
    for a, text in zip(adapters, req.external_interfaces):
        keys = {w.lower() for w in _words(text) if len(w) > 4}
        target = None
        for f in req.functional_requirements:
            if keys & {w.lower() for w in _words(f.title + " " + f.statement)}:
                target = services.get(owner[f.id] or "__core__") or next(iter(services.values()))
                break
        (target or next(iter(services.values()))).depends_on.append(a.id)

    # --- endpoints: one per FR, REST-style ------------------------------------------------
    endpoints: list[Endpoint] = []
    taken: set[tuple[str, str]] = set()
    for f in req.functional_requirements:
        svc = services.get(owner[f.id] or "__core__") or next(iter(services.values()))
        method = _method(f.title)
        resource = plural(slug(owner[f.id])) if owner[f.id] else slug(f.title)
        path = f"/api/v1/{resource}" + ("/{id}" if method in ("PUT", "PATCH", "DELETE") else "")
        if (method, path) in taken:
            path = f"{path}/{slug(f.title)}"
        taken.add((method, path))
        public = _is_public(f.title)
        errors = ["400 Invalid input"] + ([] if public else ["401 Not authenticated", "403 Not permitted"])
        if "{id}" in path:
            errors.append("404 Not found")
        endpoints.append(Endpoint(
            id=f"API-{len(endpoints) + 1:03d}", method=method, path=path, summary=f.title[:80], actor=f.actor,
            fr_ids=[f.id], component_id=svc.id,
            request="Query parameters" if method == "GET" else "JSON body" + (" and path id" if "{id}" in path else ""),
            response={"GET": "200 with the matching records", "POST": "201 with the created record",
                      "DELETE": "204 with no body"}.get(method, "200 with the updated record"),
            auth_required=not public, errors=errors))
    endpoints = endpoints[:MAX_ENDPOINTS]

    # --- tactics, decisions, stack ------------------------------------------------------------
    by_layer: dict[str, list[str]] = {}
    for c in comps:
        by_layer.setdefault(c.layer, []).append(c.id)
    tactics = []
    for n in req.non_functional_requirements:
        text, layers = _TACTICS.get(n.category, _TACTICS["maintainability"])
        realized = [cid for l in layers for cid in by_layer.get(l, [])]
        tactics.append(QualityTactic(nfr_id=n.id, tactic=f"{text} (target: {n.metric})", realized_by=realized))

    cats = {n.category: n.id for n in req.non_functional_requirements}
    decisions = [
        DesignDecision(id="DD-001", title="Layered architecture", decision="Separate presentation, API, service and data layers; calls only go downwards.",
                       rationale="Isolates change, keeps business rules testable and supports the maintainability targets.",
                       alternatives=["Monolith without layers", "Microservices"], nfr_ids=[cats[c] for c in ("maintainability", "scalability") if c in cats]),
        DesignDecision(id="DD-002", title="REST over HTTPS with JSON", decision="Expose all functionality as a versioned REST API.",
                       rationale="A uniform, stateless interface that any client can use and that is simple to secure and test.",
                       alternatives=["GraphQL", "RPC"], nfr_ids=[cats[c] for c in ("compatibility", "security") if c in cats]),
        DesignDecision(id="DD-003", title="Relational database", decision="Store all entities in a relational database with enforced foreign keys.",
                       rationale="The entities are highly related and need transactional integrity.",
                       alternatives=["Document store"], nfr_ids=[cats[c] for c in ("reliability",) if c in cats]),
    ]

    stack: list[TechChoice] = []
    for n in ctx.get("deployment", []):
        if n.get("technology"):
            stack.append(TechChoice(layer=n["name"], technology=n["technology"], rationale="Taken from the deployment diagram."))
    if not stack:
        stack = [TechChoice(layer=l, technology="To be confirmed", rationale="No technology was fixed in the SRS or the deployment diagram.")
                 for l in ("Frontend", "Backend", "Database")]

    risks = [f"Open SRS issue: {i}" for i in req.open_issues[:4]] + [
        "Endpoint definitions are indicative and must be reviewed against the acceptance criteria."]
    return DesignModel(
        architecture_style="Layered architecture with a REST API",
        architecture_overview=(f"The system is split into {len(comps)} components in layers: a web client, a REST API facade, "
                               f"{len(services)} business service(s), a data access layer and {len(adapters)} adapter(s) for external systems. "
                               "Each layer calls only the layer below it."),
        technology_stack=stack[:MAX_TECH], components=comps[:MAX_COMPONENTS], endpoints=endpoints, tables=[table_from_entity(e, entities) for e in entities[:MAX_TABLES]],
        quality_tactics=tactics, decisions=decisions,
        error_handling=["Reject invalid input with a 400 response that names the failing field.",
                        "Return 404 for records the caller does not own, never 403, so existence is not revealed.",
                        "Log technical details on the server and show users a safe, plain-language message.",
                        "Retry transient failures of external systems with exponential back-off."],
        design_risks=risks)