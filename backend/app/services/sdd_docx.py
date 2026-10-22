"""Word (.docx) export of the SDD, built from the structured DesignModel (never from Markdown).

Layout follows IEEE Std 1016-2009 (Software Design Descriptions): introduction, design overview,
architectural (composition) design, data (information) design, structural and behavioural views,
deployment, interfaces, quality attribute design, design decisions, risks, traceability.
All diagrams are drawn as figures (ER, DFD Level 0/1/2, UML ...) and are also available as editable
draw.io files.
"""
import re
from datetime import datetime

from app.schemas.sdd import DesignModel
from app.schemas.srs import Issue, Requirements
from app.services.diagram_fallbacks import er_from_tables
from app.services.diagram_scene import component_scene, er_scene
from app.services.docx_style import Word, add_scene

STANDARD = "IEEE Std 1016-2009 (Software Design Descriptions)"
VIEWPOINTS = [
    ("Context", "Section 2", "System boundary, actors and external interfaces."),
    ("Composition", "Section 3", "Components, their layers, responsibilities and dependencies."),
    ("Information", "Section 4", "Data entities, tables, relationships (ER diagram) and data flow (DFD levels 0, 1, 2)."),
    ("Logical / Structure", "Section 5", "Use cases and the class structure."),
    ("Interaction / State dynamics", "Section 6", "Sequence, activity and state behaviour."),
    ("Deployment", "Section 7", "Physical nodes, software artifacts and communication paths."),
    ("Interface", "Section 8", "External interfaces and the REST API."),
]


def _slug(s: str) -> str:
    """Short document code: initials of a multi-word title (Library Management System -> LMS)."""
    words = re.findall(r"[A-Za-z0-9]+", s)
    return ("".join(w[0] for w in words)[:6] if len(words) > 1 else (words[0][:8] if words else "SYSTEM")).upper()


def _figs(figures: list[dict], *types: str) -> list[dict]:
    return [f for f in (figures or []) if f["type"] in types]


def build_docx(d: DesignModel, req: Requirements, issues: list[Issue], figures: list[dict] | None,
               version: int = 1, srs_version: int = 1) -> bytes:
    figures = figures or []
    name = {c.id: c.name for c in d.components}
    w = Word("Software Design Description", "Design document for", req.title, f"{version}.0", STANDARD,
             f"SDD-{_slug(req.title).upper()}-V{version}")
    w.front_matter([[f"{version}.0", f"{datetime.utcnow():%d %b %Y}", "StackPilot",
                     f"Generated from SRS version {srs_version}."]])

    # ------------------------------------------------------------ 1
    w.h1("1  Introduction")
    w.h2("1.1  Purpose")
    w.para(f"This Software Design Description (SDD) describes how the system specified in the Software Requirements "
           f"Specification (SRS), version {srs_version}, is designed. It is written for the developers who will "
           f"implement the system, the testers who will verify it and the reviewers who will approve the design.")
    w.h2("1.2  Scope")
    w.para(req.scope)
    w.h2("1.3  Definitions, Acronyms and Abbreviations")
    w.table(["Term", "Definition"], [[t.term, t.definition] for t in req.definitions], [1.3, 4],
            caption="Definitions, acronyms and abbreviations", empty="No special terms are used in this document.")
    w.h2("1.4  References")
    w.table(["Ref.", "Document"], [
        ["[1]", f"Software Requirements Specification: {req.title}, version {srs_version}."],
        ["[2]", "IEEE Std 1016-2009, IEEE Standard for Information Technology: Systems Design: Software Design Descriptions."],
        ["[3]", "ISO/IEC/IEEE 29148:2018, Systems and software engineering: Requirements engineering."],
    ], [0.6, 5], caption="Reference documents")
    w.h2("1.5  Document Overview and Design Viewpoints")
    w.para("The design is described from several viewpoints. Each viewpoint answers a different question about the system "
           "and is covered by one section of this document.")
    w.table(["Viewpoint", "Where", "Concern addressed"], [list(v) for v in VIEWPOINTS], [1.5, 0.9, 3.6],
            caption="Design viewpoints used in this document")

    # ------------------------------------------------------------ 2
    w.h1("2  Design Overview")
    w.h2("2.1  Architectural Style")
    w.para(d.architecture_style, bold=True, keep=True)
    w.para(d.architecture_overview)
    w.h2("2.2  Technology Stack")
    w.table(["Layer", "Technology", "Rationale"], [[t.layer, t.technology, t.rationale] for t in d.technology_stack],
            [1, 1.6, 3.4], caption="Technology stack")
    w.h2("2.3  Design Constraints and Assumptions")
    w.bullets(req.constraints + req.assumptions)

    # ------------------------------------------------------------ 3
    w.h1("3  Architectural Design")
    w.h2("3.1  Component Overview")
    w.table(["ID", "Component", "Layer", "Pattern", "Implements"],
            [[c.id, c.name, c.layer.capitalize(), c.pattern, ", ".join(c.fr_ids)] for c in d.components],
            [0.8, 1.6, 1.1, 1.2, 1.5], caption="Components of the system")
    w.h2("3.2  Component Diagram")
    w.para("The diagram groups the components by layer. An arrow means \u201ccalls\u201d: dependencies point down the "
           "layers and there are no cycles.")
    if d.components:
        add_scene(w, component_scene([c.model_dump() for c in d.components],
                                     "Component diagram: " + req.title), "Component diagram: layers and dependencies")
    w.h2("3.3  Component Specifications")
    for c in d.components:
        w.kv_table(f"{c.id}  {c.name}", [
            ("Layer", c.layer.capitalize()), ("Design pattern", c.pattern),
            ("Responsibility", c.responsibility), ("Implements", ", ".join(c.fr_ids)),
            ("Data entities", ", ".join(c.entities)),
            ("Depends on", ", ".join(f"{x} ({name.get(x, x)})" for x in c.depends_on)),
        ])

    # ------------------------------------------------------------ 4
    w.h1("4  Data Design")
    w.h2("4.1  Entity-Relationship Diagram")
    w.para("The ER diagram shows the persistent data. It uses crow\u2019s foot notation: PK marks a primary key, FK a "
           "foreign key and UK a unique column. It is derived from the table designs in Section 4.2.")
    if d.tables:
        er = er_from_tables(d.tables)
        add_scene(w, er_scene(er.model_dump(), "ER diagram"), "Entity-relationship diagram")
    else:
        for f in _figs(figures, "er"):
            add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
    w.h2("4.2  Data Dictionary")
    for t in d.tables:
        w.h3(f"{t.table}")
        w.label_para("Stores", t.entity)
        w.table(["Column", "Definition"], [[c.partition(":")[0].strip(), c.partition(":")[2].strip()] for c in t.columns],
                [1.4, 3.6], caption=f"Columns of {t.table}")
        if t.indexes:
            w.label_para("Indexes", "; ".join(t.indexes))
        if t.notes:
            w.label_para("Notes", t.notes)
    w.h2("4.3  Data Flow Design")
    dfd = _figs(figures, "dfd")
    if dfd:
        w.para("Data flow diagrams (DFD) show how data moves between the external entities, the processes and the data "
               "stores. Level 0 is the context diagram, Level 1 the major processes and Level 2 the detail of the "
               "most important Level 1 processes.")
        for f in dfd:
            add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
    else:
        w.para("No data flow diagrams have been generated yet. Generate the diagrams in StackPilot and export again.", italic=True)

    # ------------------------------------------------------------ 5
    w.h1("5  Structural Design")
    w.h2("5.1  Use Cases and Actors")
    w.table(["Use case", "Name", "Actor", "Requirements"],
            [[u.id, u.name, u.actor, ", ".join(u.fr_ids)] for u in req.use_cases], [0.9, 2.4, 1.4, 1.5], caption="Use cases")
    for f in _figs(figures, "usecase"):
        add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
    w.h2("5.2  Class Diagram")
    cls = _figs(figures, "class")
    for f in cls:
        add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
    if not cls:
        w.para("No class diagram has been generated yet.", italic=True)

    # ------------------------------------------------------------ 6
    w.h1("6  Behavioural Design")
    for n, (head, t, intro) in enumerate((
            ("Sequence Diagrams", "sequence", "Each sequence diagram shows the messages exchanged to carry out one important use case."),
            ("Activity Diagrams", "activity", "Each activity diagram shows the workflow of one use case, including its decisions."),
            ("State Diagrams", "state", "Each state diagram shows the life cycle of one entity.")), start=1):
        w.h2(f"6.{n}  {head}")
        fs = _figs(figures, t)
        if fs:
            w.para(intro)
        for f in fs:
            add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
        if not fs:
            w.para(f"No {t} diagrams have been generated yet.", italic=True)

    # ------------------------------------------------------------ 7
    w.h1("7  Deployment Design")
    dep = _figs(figures, "deployment")
    if dep:
        w.para("The deployment diagram shows the physical nodes, the software artifacts installed on them and the protocols between them.")
    for f in dep:
        add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
    if not dep:
        w.para("No deployment diagram has been generated yet.", italic=True)

    # ------------------------------------------------------------ 8
    w.h1("8  Interface Design")
    w.h2("8.1  External Interfaces")
    w.bullets(req.external_interfaces)
    w.h2("8.2  REST API")
    w.table(["ID", "Method", "Path", "Actor", "Handled by", "Auth"],
            [[e.id, e.method, e.path, e.actor, name.get(e.component_id, e.component_id), "Yes" if e.auth_required else "No"]
             for e in d.endpoints], [0.8, 0.8, 2.4, 1.2, 1.4, 0.6], caption="REST API endpoints", size=9)
    w.h2("8.3  Endpoint Details")
    for e in d.endpoints:
        w.kv_table(f"{e.id}  {e.method} {e.path}", [
            ("Summary", e.summary), ("Implements", ", ".join(e.fr_ids)),
            ("Request", e.request), ("Response", e.response), ("Errors", ", ".join(e.errors))])

    # ------------------------------------------------------------ 9-12
    w.h1("9  Quality Attribute Design")
    tactic = {q.nfr_id: q for q in d.quality_tactics}
    w.table(["Requirement", "Category", "Target", "Design tactic", "Realized by"],
            [[n.id, n.category.capitalize(), n.metric, tactic[n.id].tactic if n.id in tactic else "NO TACTIC",
              ", ".join(name.get(c, c) for c in tactic[n.id].realized_by) if n.id in tactic else ""]
             for n in req.non_functional_requirements], [0.9, 1, 1.5, 2.2, 1.4], caption="Quality attributes and design tactics")
    w.h1("10  Design Decisions")
    for dd in d.decisions:
        w.kv_table(f"{dd.id}  {dd.title}", [("Decision", dd.decision), ("Rationale", dd.rationale),
                                            ("Alternatives rejected", w.list_cell(dd.alternatives)),
                                            ("Driven by", ", ".join(dd.nfr_ids))])
    w.h1("11  Error Handling and Cross-Cutting Concerns")
    w.bullets(d.error_handling)
    w.h1("12  Design Risks")
    w.bullets(d.design_risks)

    w.h1("Appendix A  Requirements-to-Design Traceability", page_break=True)
    rows = []
    for f in req.functional_requirements:
        comps = [c for c in d.components if f.id in c.fr_ids]
        rows.append([f.id, f.title, ", ".join(c.name for c in comps) or "NOT ALLOCATED",
                     ", ".join(e.id for e in d.endpoints if f.id in e.fr_ids), ", ".join(sorted({x for c in comps for x in c.entities}))])
    w.table(["Requirement", "Title", "Components", "Endpoints", "Data entities"], rows, [0.9, 1.8, 1.6, 1.2, 1.4],
            caption="Requirements-to-design traceability", size=9)
    if issues:
        w.h1("Appendix B  Quality Check Findings")
        w.table(["Level", "Finding"], [[i.level.upper(), i.message] for i in sorted(issues, key=lambda i: i.level != "error")],
                [0.8, 5], caption="Automatic quality check findings")
    return w.save()
