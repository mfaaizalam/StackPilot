"""Word (.docx) export of the SRS, built from the structured Requirements (never from Markdown).

Layout follows ISO/IEC/IEEE 29148:2018 (which supersedes IEEE 830): introduction, overall description,
specific requirements (interfaces, functional, non-functional, use cases, data), appendices.
Diagrams are drawn as figures; the same diagrams are available as editable draw.io files.
"""
import re
from datetime import datetime

from app.schemas.srs import Issue, Requirements
from app.services.docx_style import Word, add_scene

STANDARD = "ISO/IEC/IEEE 29148:2018 (Systems and software engineering: Requirements engineering)"
PRIORITY = {"must": "Must have (essential)", "should": "Should have (important)", "could": "Could have (desirable)"}


def _slug(s: str) -> str:
    """Short document code: initials of a multi-word title (Library Management System -> LMS)."""
    words = re.findall(r"[A-Za-z0-9]+", s)
    return ("".join(w[0] for w in words)[:6] if len(words) > 1 else (words[0][:8] if words else "SYSTEM")).upper()


def _figs(figures: list[dict], *types: str) -> list[dict]:
    return [f for f in (figures or []) if f["type"] in types]


def build_docx(req: Requirements, issues: list[Issue], version: int = 1, figures: list[dict] | None = None) -> bytes:
    figures = figures or []
    w = Word("Software Requirements Specification", "Requirements document for", req.title, f"{version}.0",
             STANDARD, f"SRS-{_slug(req.title).upper()}-V{version}")
    w.front_matter([[f"{version}.0", f"{datetime.utcnow():%d %b %Y}", "StackPilot",
                     "Generated from the project description and the answers given to the requirement questions."]])

    # ------------------------------------------------------------ 1
    w.h1("1  Introduction")
    w.h2("1.1  Purpose")
    w.para(req.purpose)
    w.para("This document specifies the requirements of the system in a form that can be reviewed, agreed with the "
           "stakeholders, designed against and tested. It is the baseline for the Software Design Description.")
    w.h2("1.2  Scope")
    w.para(req.scope)
    w.h2("1.3  Definitions, Acronyms and Abbreviations")
    w.table(["Term", "Definition"], [[t.term, t.definition] for t in req.definitions], [1.3, 4],
            caption="Definitions, acronyms and abbreviations", empty="No special terms are used in this document.")
    w.h2("1.4  References")
    w.table(["Ref.", "Document"], [
        ["[1]", "ISO/IEC/IEEE 29148:2018, Systems and software engineering: Life cycle processes: Requirements engineering."],
        ["[2]", "IEEE Std 1016-2009, IEEE Standard for Information Technology: Systems Design: Software Design Descriptions."],
        ["[3]", "IEEE Std 830-1998, IEEE Recommended Practice for Software Requirements Specifications (superseded by [1])."],
    ], [0.6, 5], caption="Reference documents")
    w.h2("1.5  Document Conventions")
    w.para("Requirements are identified by a unique tag: FR-nnn for functional requirements, NFR-nnn for non-functional "
           "requirements and UC-nnn for use cases. The word \u201cshall\u201d states a mandatory requirement. Each "
           "functional requirement carries a priority:")
    w.table(["Priority", "Meaning"], [[k.capitalize(), v] for k, v in PRIORITY.items()], [1, 4], caption="Requirement priorities")
    w.h2("1.6  Document Overview")
    w.para("Section 2 describes the product and its users in general terms. Section 3 contains the specific, testable "
           "requirements: external interfaces, functional requirements, non-functional requirements, use cases, data "
           "requirements and analysis models. The appendices contain the requirements traceability matrix, the open "
           "issues and the results of the automatic quality check.")

    # ------------------------------------------------------------ 2
    w.h1("2  Overall Description")
    w.h2("2.1  Product Perspective")
    w.para(req.product_perspective)
    w.h2("2.2  Product Functions")
    w.para("The principal functions of the system are summarised below. Section 3.2 specifies each one in detail.")
    w.table(["ID", "Function", "Primary actor", "Priority"],
            [[f.id, f.title, f.actor, f.priority.capitalize()] for f in req.functional_requirements],
            [0.9, 3.2, 1.6, 1], caption="Summary of product functions")
    w.h2("2.3  User Classes and Characteristics")
    w.table(["User class", "Description"], [[a.name, a.description] for a in req.actors], [1.3, 4],
            caption="User classes and characteristics")
    w.h2("2.4  Constraints")
    w.bullets(req.constraints)
    w.h2("2.5  Assumptions and Dependencies")
    w.bullets(req.assumptions)

    # ------------------------------------------------------------ 3
    w.h1("3  Specific Requirements")
    w.h2("3.1  External Interface Requirements")
    w.para("The system shall provide or use the following external interfaces.")
    w.table(["ID", "Interface requirement"], [[f"EIR-{i:03d}", t] for i, t in enumerate(req.external_interfaces, start=1)],
            [0.9, 5], caption="External interface requirements", empty="No external interfaces have been identified.")

    w.h2("3.2  Functional Requirements")
    by_actor: dict[str, list] = {}
    for f in req.functional_requirements:
        by_actor.setdefault(f.actor, []).append(f)
    uc_of = {f.id: [u.id for u in req.use_cases if f.id in u.fr_ids] for f in req.functional_requirements}
    for n, (actor, frs) in enumerate(by_actor.items(), start=1):
        w.h3(f"3.2.{n}  Functions for {actor}")
        for f in frs:
            w.kv_table(f"{f.id}  {f.title}", [
                ("Statement", f.statement),
                ("Priority", PRIORITY.get(f.priority, f.priority)),
                ("Actor", f.actor),
                ("Acceptance criteria", w.list_cell(f.acceptance_criteria)),
                ("Related use cases", ", ".join(uc_of[f.id]) or "None"),
            ])

    w.h2("3.3  Non-Functional Requirements")
    w.para("Each non-functional requirement has a measurable target so that it can be verified.")
    by_cat: dict[str, list] = {}
    for r in req.non_functional_requirements:
        by_cat.setdefault(r.category, []).append(r)
    for n, (cat, rs) in enumerate(by_cat.items(), start=1):
        w.h3(f"3.3.{n}  {cat.capitalize()} requirements")
        w.table(["ID", "Requirement", "Measurable target"], [[r.id, r.statement, r.metric] for r in rs], [0.9, 3.2, 2.4],
                caption=f"{cat.capitalize()} requirements")

    w.h2("3.4  Use Cases")
    for u in req.use_cases:
        pairs = [("Primary actor", u.actor), ("Description", u.description),
                 ("Related requirements", ", ".join(u.fr_ids) or "None"),
                 ("Preconditions", w.list_cell(u.preconditions)),
                 ("Main flow", "\n".join(f"{i}. {s}" for i, s in enumerate(u.main_flow, start=1)) or "\u2014"),
                 ("Alternate flows", w.list_cell(u.alternate_flows))]
        w.kv_table(f"{u.id}  {u.name}", pairs)

    w.h2("3.5  Logical Data Requirements")
    w.para("The system shall store and maintain the following data entities.")
    w.table(["Entity", "Description", "Attributes", "Relationships"],
            [[e.name, e.description, ", ".join(e.attributes), "; ".join(e.relations)] for e in req.entities],
            [1, 2, 2.2, 1.8], caption="Data entities", empty="No data entities have been identified.")
    for f in _figs(figures, "er"):
        add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))

    w.h2("3.6  Analysis Models")
    ucd = _figs(figures, "usecase")
    dfd = _figs(figures, "dfd")
    if ucd:
        w.h3("3.6.1  Use Case Diagram")
        w.para("The use case diagram shows the actors and the functions of the system that each one uses.")
        for f in ucd:
            add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
    if dfd:
        w.h3("3.6.2  Data Flow Diagrams")
        w.para("The data flow diagrams describe how data moves through the system. Level 0 is the context diagram: "
               "the whole system as one process and the external entities around it. Level 1 splits the system into "
               "its major processes and data stores. Level 2 explodes selected Level 1 processes into their "
               "sub-processes. The levels are balanced: the data entering and leaving a process is the same at every level.")
        for f in dfd:
            add_scene(w, f["scene"], f["title"], f["stale"], f.get("png"))
    if not ucd and not dfd:
        w.para("No analysis models have been generated yet. Generate the diagrams in StackPilot and export again.", italic=True)

    # ------------------------------------------------------------ appendices
    w.h1("Appendix A  Requirements Traceability Matrix", page_break=True)
    w.table(["Requirement", "Title", "Priority", "Covered by use case"],
            [[f.id, f.title, f.priority.capitalize(), ", ".join(uc_of[f.id]) or "NOT COVERED"] for f in req.functional_requirements],
            [1, 3, 1, 1.6], caption="Functional requirements to use cases")
    w.h1("Appendix B  Open Issues")
    w.bullets(req.open_issues, "No open issues.")
    if issues:
        w.h1("Appendix C  Quality Check Findings")
        w.table(["Level", "Finding"], [[i.level.upper(), i.message] for i in sorted(issues, key=lambda i: i.level != "error")],
                [0.8, 5], caption="Automatic quality check findings")
    return w.save()
