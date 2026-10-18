"""Deterministic Markdown renderer for the SDD (no AI). Structure follows IEEE 1016.

Inputs are already validated: the DesignModel, the SRS Requirements, the quality issues and the
rendered diagrams of the SRS version (list of dicts from diagram_service.list_diagrams)."""
import re
from datetime import datetime

from app.schemas.sdd import DesignModel
from app.schemas.srs import Issue, Requirements


def _cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip() or "—"


def _bullets(items: list[str], empty: str = "None.") -> str:
    return "\n".join(f"- {i}" for i in items) if items else empty


def _mm(s: str) -> str:
    """Make a label safe inside a Mermaid quoted string."""
    return re.sub(r'["\[\]{}()<>|`]', "", s or "").strip()


def component_diagram(d: DesignModel) -> str:
    """Mermaid flowchart of the component dependencies, grouped by layer. Built from the model, never by AI."""
    L = ["flowchart TD"]
    for layer in ("presentation", "api", "service", "data", "integration", "infrastructure"):
        members = [c for c in d.components if c.layer == layer]
        if not members:
            continue
        L.append(f'  subgraph {layer.upper()}["{layer.capitalize()} layer"]')
        for c in members:
            L.append(f'    {c.id.replace("-", "_")}["{_mm(c.name)}"]')
        L.append("  end")
    for c in d.components:
        for dep in c.depends_on:
            L.append(f'  {c.id.replace("-", "_")} --> {dep.replace("-", "_")}')
    return "\n".join(L)


def _diagram_block(dg: dict) -> str:
    stale = " *(out of date: generated from an earlier SRS version)*" if dg.get("stale") else ""
    out = [f"**{dg['title']}**{stale}\n"]
    if dg.get("mermaid"):
        out.append(f"```mermaid\n{dg['mermaid']}\n```\n")
    else:
        out.append("*This diagram could not be rendered.*\n")
    return "\n".join(out)


def _of_type(diagrams: list[dict], t: str) -> list[dict]:
    return [x for x in diagrams if x["type"] == t]


def render_sdd_markdown(d: DesignModel, req: Requirements, issues: list[Issue], diagrams: list[dict],
                        version: int = 1, srs_version: int = 1) -> str:
    L: list[str] = []
    a = L.append
    comp_name = {c.id: c.name for c in d.components}

    a(f"# Software Design Description\n\n## {req.title}\n")
    a(f"*Version {version} · based on SRS version {srs_version} · {datetime.utcnow():%Y-%m-%d} · Structure based on IEEE 1016*\n")

    a("## 1. Introduction\n")
    a(f"### 1.1 Purpose\n\nThis document describes how the system specified in the SRS (version {srs_version}) is designed. "
      f"It is the bridge between the requirements and the implementation.\n")
    a(f"### 1.2 Scope\n\n{req.scope}\n")
    a("### 1.3 Definitions, Acronyms and Abbreviations\n")
    if req.definitions:
        a("| Term | Definition |\n|---|---|")
        L.extend(f"| {_cell(t.term)} | {_cell(t.definition)} |" for t in req.definitions)
        a("")
    else:
        a("None.\n")
    a("### 1.4 References\n")
    a(_bullets([f"Software Requirements Specification, version {srs_version}", "ISO/IEC/IEEE 29148: Requirements engineering",
                "IEEE 1016: Software design descriptions", "OMG Unified Modeling Language (UML) 2.5"]) + "\n")

    a("## 2. Design Overview\n")
    a(f"### 2.1 Architectural Style\n\n**{d.architecture_style}**\n\n{d.architecture_overview}\n")
    a("### 2.2 Technology Stack\n")
    a("| Layer | Technology | Rationale |\n|---|---|---|")
    L.extend(f"| {_cell(t.layer)} | {_cell(t.technology)} | {_cell(t.rationale)} |" for t in d.technology_stack)
    a("")
    a(f"### 2.3 Design Constraints and Assumptions\n\n**Constraints**\n\n{_bullets(req.constraints)}\n\n**Assumptions**\n\n{_bullets(req.assumptions)}\n")

    a("## 3. Architectural Design\n")
    a("### 3.1 Component Overview\n")
    a("| ID | Component | Layer | Pattern | Implements |\n|---|---|---|---|---|")
    L.extend(f"| {c.id} | {_cell(c.name)} | {c.layer} | {c.pattern} | {_cell(', '.join(c.fr_ids))} |" for c in d.components)
    a("")
    a("### 3.2 Component Dependencies\n")
    a(f"```mermaid\n{component_diagram(d)}\n```\n")
    a("### 3.3 Component Specifications\n")
    for c in d.components:
        a(f"#### {c.id} · {c.name}\n")
        a(f"- **Layer:** {c.layer}")
        a(f"- **Design pattern:** {c.pattern}")
        a(f"- **Responsibility:** {c.responsibility}")
        a(f"- **Implements:** {', '.join(c.fr_ids) or '—'}")
        a(f"- **Data entities:** {', '.join(c.entities) or '—'}")
        a(f"- **Depends on:** {', '.join(f'{x} ({comp_name.get(x, x)})' for x in c.depends_on) or '—'}\n")

    a("## 4. Structural Design\n")
    a("### 4.1 Use Cases and Actors\n")
    a("| Use case | Name | Actor | Requirements |\n|---|---|---|---|")
    L.extend(f"| {u.id} | {_cell(u.name)} | {_cell(u.actor)} | {_cell(', '.join(u.fr_ids))} |" for u in req.use_cases)
    a("\nThe use case diagram is available in the diagrams view of the project.\n")
    a("### 4.2 Class Diagram\n")
    cls = _of_type(diagrams, "class")
    a("\n".join(_diagram_block(x) for x in cls) if cls else "*No class diagram has been generated yet.*\n")

    a("## 5. Behavioural Design\n")
    for n, (heading, t) in enumerate((("Sequence Diagrams", "sequence"), ("Activity Diagrams", "activity"), ("State Diagrams", "state")), start=1):
        a(f"### 5.{n} {heading}\n")
        items = _of_type(diagrams, t)
        a("\n".join(_diagram_block(x) for x in items) if items else f"*No {t} diagrams have been generated yet.*\n")

    a("## 6. Deployment Design\n")
    dep = _of_type(diagrams, "deployment")
    a("\n".join(_diagram_block(x) for x in dep) if dep else "*No deployment diagram has been generated yet.*\n")

    a("## 7. Data Design\n")
    for t in d.tables:
        a(f"### {t.table}\n")
        a(f"Stores: **{t.entity}**\n")
        a("| Column | Definition |\n|---|---|")
        for col in t.columns:
            name, _, spec = col.partition(":")
            a(f"| `{name.strip()}` | {_cell(spec.strip())} |")
        a("")
        if t.indexes:
            a("**Indexes**\n")
            a(_bullets(t.indexes) + "\n")
        if t.notes:
            a(f"{t.notes}\n")

    a("## 8. Interface Design\n")
    a(f"### 8.1 External Interfaces\n\n{_bullets(req.external_interfaces)}\n")
    a("### 8.2 REST API\n")
    a("| ID | Method | Path | Actor | Handled by | Auth | Implements |\n|---|---|---|---|---|---|---|")
    L.extend(f"| {e.id} | {e.method} | `{e.path}` | {_cell(e.actor)} | {_cell(comp_name.get(e.component_id, e.component_id))} | "
             f"{'yes' if e.auth_required else 'no'} | {_cell(', '.join(e.fr_ids))} |" for e in d.endpoints)
    a("")
    a("### 8.3 Endpoint Details\n")
    for e in d.endpoints:
        a(f"#### {e.id} · {e.method} `{e.path}`\n")
        a(f"{e.summary}\n")
        a(f"- **Request:** {e.request or '—'}")
        a(f"- **Response:** {e.response or '—'}")
        a(f"- **Errors:** {', '.join(e.errors) or '—'}\n")

    a("## 9. Quality Attribute Design\n")
    a("| Requirement | Category | Target | Design tactic | Realized by |\n|---|---|---|---|---|")
    tactic = {q.nfr_id: q for q in d.quality_tactics}
    for n in req.non_functional_requirements:
        q = tactic.get(n.id)
        a(f"| {n.id} | {n.category} | {_cell(n.metric)} | {_cell(q.tactic) if q else '**NO TACTIC**'} | "
          f"{_cell(', '.join(comp_name.get(c, c) for c in q.realized_by)) if q else '—'} |")
    a("")

    a("## 10. Design Decisions\n")
    for dd in d.decisions:
        a(f"### {dd.id} · {dd.title}\n")
        a(f"- **Decision:** {dd.decision}")
        a(f"- **Rationale:** {dd.rationale}")
        a(f"- **Alternatives rejected:** {', '.join(dd.alternatives) or '—'}")
        a(f"- **Driven by:** {', '.join(dd.nfr_ids) or '—'}\n")

    a(f"## 11. Error Handling and Cross-Cutting Concerns\n\n{_bullets(d.error_handling)}\n")
    a(f"## 12. Design Risks\n\n{_bullets(d.design_risks)}\n")

    a("## Appendix A: Requirements-to-Design Traceability\n")
    a("| Requirement | Title | Components | Endpoints | Data entities |\n|---|---|---|---|---|")
    for f in req.functional_requirements:
        comps = [c for c in d.components if f.id in c.fr_ids]
        eps = [e.id for e in d.endpoints if f.id in e.fr_ids]
        ents = sorted({x for c in comps for x in c.entities})
        a(f"| {f.id} | {_cell(f.title)} | {_cell(', '.join(c.name for c in comps)) if comps else '**NOT ALLOCATED**'} | "
          f"{_cell(', '.join(eps))} | {_cell(', '.join(ents))} |")
    a("")

    a("## Appendix B: Diagram Index\n")
    if diagrams:
        a("| Type | Title | Status |\n|---|---|---|")
        L.extend(f"| {x['type']} | {_cell(x['title'])} | {'out of date' if x.get('stale') else 'current'} |" for x in diagrams)
        a("")
    else:
        a("No diagrams were available when this document was generated.\n")

    findings = [i for i in issues]
    if findings:
        a("## Appendix C: Quality Check Findings\n")
        order = sorted(findings, key=lambda i: i.level != "error")
        a(_bullets([f"[{i.level.upper()}] {i.message}" for i in order]) + "\n")
    return "\n".join(L)