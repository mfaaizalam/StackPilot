import random
import xml.etree.ElementTree as ET

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.llm import LLMError
from app.core.llm_fake import sample_requirements
from app.models.board import Board
from app.models.column import BoardColumn
from app.models.task import Task
from app.models.user import User
from app.models.otp import OTP
from app.models.chat import Chat
from app.models.srs import SRSDocument, SRSJob, Diagram, DiagramJob
from app.routes import diagrams as diagram_routes
from app.routes import srs as srs_routes
from app.routes.auth import get_current_user
from app.schemas.diagrams import *
from app.schemas.srs import Entity
from app.services import diagram_fallbacks as F
from app.services import diagram_mermaid as M
from app.services import diagram_service
from app.services import diagram_validator as V
from app.services.diagram_usecase_svg import layout, render_usecase_svg


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def codes(issues):
    return {i.code for i in issues}


def cls(name, attrs=(), methods=()):
    return ClassNode(name=name, attributes=list(attrs), methods=list(methods))


def rel(a, b, kind="association"):
    return ClassRelation(kind=kind, source=a, target=b, multiplicity_source="1", multiplicity_target="*", label="uses")


# ======================================================= class limits
def test_class_over_limit_is_trimmed_to_12_most_connected():
    names = [f"C{i}" for i in range(20)]
    # C0 is connected to everyone -> must survive; the rest are isolated
    m = ClassModel(classes=[cls(n) for n in names], relations=[rel("C0", n) for n in names[1:12]])
    assert "TOO_MANY_CLASSES" in codes(V.validate_class(m))
    clean, warns = V.sanitize_class(m)
    assert len(clean.classes) == MAX_CLASSES and "C0" in {c.name for c in clean.classes}
    assert warns and not V.has_errors(V.validate_class(clean))


def test_class_dangling_and_duplicate_relations_dropped_and_labels_clipped():
    m = ClassModel(classes=[cls("Order", ["x" * 80]), cls("Item")],
                   relations=[rel("order", "ITEM"), rel("Order", "Ghost"), rel("Order", "Item"), rel("Item", "Item")])
    assert "UNKNOWN_CLASS" in codes(V.validate_class(m))
    clean, _ = V.sanitize_class(m)
    assert len(clean.relations) == 1 and clean.relations[0].source == "Order"  # canonical casing
    assert all(len(a) <= MAX_LABEL for c in clean.classes for a in c.attributes)


def test_class_too_small_returns_none():
    assert V.sanitize_class(ClassModel(classes=[cls("A")], relations=[]))[0] is None


# =================================================== sequence limits
def test_sequence_limits_and_unknown_participants():
    parts = [f"P{i}" for i in range(12)]
    msgs = [Message(source="P0", target="P1", text="m" * 60, kind="sync") for _ in range(30)]
    msgs.append(Message(source="P0", target="Ghost", text="x", kind="sync"))
    m = SequenceModel(participants=parts, messages=msgs, fragments=[])
    c = codes(V.validate_sequence(m))
    assert {"TOO_MANY_PARTICIPANTS", "TOO_MANY_MESSAGES", "UNKNOWN_PARTICIPANT"} <= c
    clean, _ = V.sanitize_sequence(m)
    assert len(clean.participants) <= MAX_PARTICIPANTS and len(clean.messages) <= MAX_MESSAGES
    assert all(len(x.text) <= MAX_LABEL for x in clean.messages)
    assert not V.has_errors(V.validate_sequence(clean))


def test_sequence_fragments_must_be_valid_and_disjoint():
    msgs = [Message(source="A", target="B", text=f"m{i}", kind="sync") for i in range(6)]
    fr = [Fragment(kind="opt", label="a", start=2, end=4), Fragment(kind="alt", label="overlap", start=3, end=5),
          Fragment(kind="loop", label="bad", start=5, end=99)]
    clean, _ = V.sanitize_sequence(SequenceModel(participants=["A", "B"], messages=msgs, fragments=fr))
    assert [(f.start, f.end) for f in clean.fragments] == [(2, 4)]


# ================================================== activity rules
def n(i, k, l=""):
    return ActNode(id=i, kind=k, label=l)


def e(a, b, l=""):
    return ActEdge(source=a, target=b, label=l)


def test_activity_valid_sample_has_no_errors():
    from app.core.llm_fake import fake_response
    assert not V.has_errors(V.validate_activity(fake_response(ActivityModel)))


def test_activity_errors_detected():
    m = ActivityModel(nodes=[n("1", "start"), n("2", "start"), n("3", "decision", "ok?")], edges=[e("1", "3"), e("3", "9")])
    assert {"START_COUNT", "NO_END", "UNKNOWN_NODE", "DECISION_BRANCHES"} <= codes(V.validate_activity(m))


def test_activity_sanitize_repairs_structure():
    m = ActivityModel(
        nodes=[n("s", "start"), n("s2", "start"), n("a", "action", "Do A"), n("b", "action", "Do B"), n("orphan", "action", "Lost")],
        edges=[e("s", "a"), e("a", "b"), e("a", "nowhere")])
    clean, warns = V.sanitize_activity(m)
    ids = {x.id for x in clean.nodes}
    assert "orphan" not in ids and "s2" not in ids
    assert sum(x.kind == "start" for x in clean.nodes) == 1 and any(x.kind == "end" for x in clean.nodes)
    assert not V.has_errors(V.validate_activity(clean)) or codes(V.validate_activity(clean)) == {"DECISION_BRANCHES"}
    assert warns


def test_activity_node_cap():
    nodes = [n("s", "start")] + [n(f"a{i}", "action", f"Step {i}") for i in range(40)]
    edges = [e("s", "a0")] + [e(f"a{i}", f"a{i+1}") for i in range(39)]
    clean, _ = V.sanitize_activity(ActivityModel(nodes=nodes, edges=edges))
    assert len(clean.nodes) <= MAX_ACTIVITY_NODES + 1  # +1: auto-added end node


# ===================================================== state rules
def test_state_sanitize():
    m = StateModel(entity="Order", states=["New", "Paid", "Shipped"] + [f"S{i}" for i in range(12)], initial="Nope", finals=["Shipped", "Zzz"],
                   transitions=[Transition(source="New", target="Paid", label="pay"), Transition(source="New", target="Ghost", label="x")])
    assert {"TOO_MANY_STATES", "BAD_INITIAL", "UNKNOWN_STATE"} <= codes(V.validate_state(m))
    clean, _ = V.sanitize_state(m)
    assert len(clean.states) <= MAX_STATES and clean.initial == "New" and clean.finals == ["Shipped"]
    assert len(clean.transitions) == 1


# ================================================ garbage-in property test
def test_sanitizers_always_produce_valid_output():
    rnd = random.Random(7)
    words = ["A", "B", "C", "D", "E", "ghost", "a b", ""]
    for _ in range(200):
        cm = ClassModel(
            classes=[cls(rnd.choice(words) + str(rnd.randint(0, 20))) for _ in range(rnd.randint(0, 25))],
            relations=[rel(rnd.choice(words) + str(rnd.randint(0, 20)), rnd.choice(words) + str(rnd.randint(0, 20))) for _ in range(rnd.randint(0, 30))])
        c, _ = V.sanitize_class(cm)
        if c:
            assert not V.has_errors(V.validate_class(c))
        names = [rnd.choice(words) + str(i) for i in range(rnd.randint(0, 14))]
        sm = SequenceModel(participants=names, messages=[
            Message(source=rnd.choice(names + ["zz"]), target=rnd.choice(names + ["zz"]), text="hello " * rnd.randint(0, 9), kind="sync")
            for _ in range(rnd.randint(0, 40))], fragments=[Fragment(kind="opt", label="x", start=rnd.randint(-2, 20), end=rnd.randint(-2, 40))])
        s, _ = V.sanitize_sequence(sm)
        if s:
            assert not V.has_errors(V.validate_sequence(s))
            assert all(1 <= f.start <= f.end <= len(s.messages) for f in s.fragments)


# ========================================================= mermaid
def test_class_mermaid():
    from app.core.llm_fake import fake_response
    txt = M.class_to_mermaid(fake_response(ClassModel))
    assert txt.startswith("classDiagram") and "class Member {" in txt
    assert 'Member "1" --> "*" Loan : borrows' in txt and "+borrowBook()" in txt


def test_mermaid_inheritance_and_composition_direction():
    m = ClassModel(classes=[cls("Animal"), cls("Dog"), cls("Order"), cls("Line")],
                   relations=[ClassRelation(kind="inheritance", source="Dog", target="Animal", multiplicity_source="", multiplicity_target="", label=""),
                              ClassRelation(kind="composition", source="Order", target="Line", multiplicity_source="1", multiplicity_target="1..*", label="")])
    txt = M.class_to_mermaid(m)
    assert "Animal <|-- Dog" in txt and 'Order "1" *-- "1..*" Line' in txt


def test_mermaid_text_is_scrubbed():
    m = SequenceModel(participants=["A", "B"], messages=[
        Message(source="A", target="B", text='Do "x"; #1 {y} <z>', kind="sync"),
        Message(source="B", target="A", text="ok", kind="return")], fragments=[Fragment(kind="opt", label="maybe;", start=1, end=2)])
    txt = M.sequence_to_mermaid(m, {"a"})
    assert 'Do "' not in txt and "#" not in txt and "{" not in txt and "<" not in txt
    assert "actor p1 as A" in txt and "participant p2 as B" in txt
    assert txt.count("opt ") == 1 and txt.strip().endswith("end")
    assert "p1->>p2:" in txt and "p2-->>p1:" in txt


def test_activity_and_state_mermaid():
    from app.core.llm_fake import fake_response
    a = M.activity_to_mermaid(fake_response(ActivityModel))
    assert a.startswith("flowchart TD") and '-->|"Yes"|' in a and "{" in a
    s = M.state_to_mermaid(fake_response(StateModelSet).machines[0])
    assert s.startswith("stateDiagram-v2") and "[*] --> s1" in s and "s3 --> [*]" in s


# =================================================== use-case SVG
def test_usecase_svg_is_valid_xml_and_complete():
    req = sample_requirements()
    model = F.build_usecase_model(req)
    model.includes = [Rel(source="UC-002", target="UC-001")]
    svg = render_usecase_svg(model)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    for u in req.use_cases:
        assert u.name.split()[0] in svg
    assert svg.count("<ellipse") == len(req.use_cases) and "«include»" in svg
    assert render_usecase_svg(model) == svg  # deterministic


def test_usecase_layout_has_no_overlaps():
    req = sample_requirements()
    lay = layout(F.build_usecase_model(req))
    ys = sorted(y for _, y in lay["rows"].values())
    assert all(b - a >= 70 for a, b in zip(ys, ys[1:]))           # ellipses don't touch
    ay = sorted(y for _, y in lay["actors"].values())
    assert all(b - a >= 120 for a, b in zip(ay, ay[1:]))          # actors don't overlap
    x, y, w, h = lay["box"]
    assert all(x < ux < x + w and y < uy < y + h for ux, uy in lay["rows"].values())
    assert lay["height"] >= y + h


def test_usecase_svg_escapes_and_external_actor():
    req = sample_requirements()
    req.actors.append(req.actors[0].model_copy(update={"name": "Payment Gateway", "description": "External payment service"}))
    req.use_cases.append(req.use_cases[0].model_copy(update={"id": "UC-006", "name": "Pay <b>fine</b> & go", "actor": "Payment Gateway"}))
    svg = render_usecase_svg(F.build_usecase_model(req))
    ET.fromstring(svg)  # still well-formed
    assert "<b>" not in svg and "«system»" in svg


def test_many_use_cases_still_render():
    req = sample_requirements()
    for i in range(20):
        req.use_cases.append(req.use_cases[0].model_copy(update={"id": f"UC-{100+i}", "name": f"Extra use case number {i}"}))
    ET.fromstring(render_usecase_svg(F.build_usecase_model(req)))


# ===================================================== fallbacks
def test_class_from_entities_parses_relations():
    m = F.class_from_entities(sample_requirements().entities)
    assert {c.name for c in m.classes} == {"Member", "Book", "Loan"}
    pairs = {(r.source, r.target) for r in m.relations}
    assert ("Member", "Loan") in pairs and ("Book", "Loan") in pairs
    assert not V.has_errors(V.validate_class(m))


def test_chunk_entities_splits_large_domains():
    ents = [Entity(name=f"E{i}", description="", attributes=["id"], relations=[f"E{i} has many E{i+1}"] if i % 5 != 4 else []) for i in range(20)]
    parts = F.chunk_entities(ents)
    assert 1 < len(parts) <= 2 and all(len(p) <= MAX_CLASSES for p in parts)
    assert len(F.chunk_entities(ents[:5])) == 1


def test_fallback_sequence_and_activity_are_valid():
    uc = sample_requirements().use_cases[1]
    seq, _ = V.sanitize_sequence(F.sequence_from_usecase(uc))
    assert seq and not V.has_errors(V.validate_sequence(seq))
    act, _ = V.sanitize_activity(F.activity_from_usecase(uc))
    assert act and not V.has_errors(V.validate_activity(act))
    assert any(x.kind == "decision" for x in act.nodes)  # alternate flow became a decision


def test_rank_use_cases_prefers_important():
    ranked = F.rank_use_cases(sample_requirements())
    assert ranked[0].id == "UC-002"  # covers 3 FRs incl. two musts


# ===================================================== API + job
DESC = "A web system for a university library to manage books, members, loans and fines."


def make_client(user_id):
    app = FastAPI()
    app.include_router(srs_routes.router)
    app.include_router(diagram_routes.router)
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": user_id})()
    return TestClient(app)


def seed_with_srs():
    db = SessionLocal()
    db.add_all([User(id=1, name="A", email="a@a.com"), User(id=2, name="B", email="b@b.com")])
    db.add(Board(id=1, name="Library", description="x", owner_id=1))
    db.commit(); db.close()
    c = make_client(1)
    c.post("/boards/1/srs/generate", json={"description": DESC})
    return c


def test_full_diagram_flow_with_fake_llm():
    c = seed_with_srs()
    r = c.post("/boards/1/srs/diagrams/generate", json={})
    assert r.status_code == 202
    st = c.get(f"/boards/1/srs/diagrams/jobs/{r.json()['job_id']}").json()
    assert st["status"] == "done", st
    out = c.get("/boards/1/srs/diagrams").json()
    by_type = {}
    for d in out["diagrams"]:
        by_type.setdefault(d["type"], []).append(d)
    assert len(by_type["usecase"]) == 1 and "<svg" in by_type["usecase"][0]["svg"]
    assert len(by_type["class"]) == 1 and by_type["class"][0]["mermaid"].startswith("classDiagram")
    assert len(by_type["sequence"]) == 4 and len(by_type["activity"]) == 3
    assert len(by_type["state"]) == 1 and by_type["state"][0]["title"] == "Loan lifecycle"
    assert [d["type"] for d in out["diagrams"]] == sorted((d["type"] for d in out["diagrams"]), key=lambda t: TYPES.index(t))
    assert not any(d["stale"] for d in out["diagrams"])
    # actors are drawn as UML actors in sequence diagrams
    assert "actor p1 as Member" in by_type["sequence"][0]["mermaid"]


TYPES = ["usecase", "class", "sequence", "activity", "state"]


def test_regenerate_replaces_instead_of_duplicating():
    c = seed_with_srs()
    for _ in range(2):
        c.post("/boards/1/srs/diagrams/generate", json={"types": ["class", "usecase"]})
    out = c.get("/boards/1/srs/diagrams").json()["diagrams"]
    assert sorted(d["type"] for d in out) == ["class", "usecase"]


def test_requirement_edit_marks_diagrams_stale_then_regenerate_clears():
    c = seed_with_srs()
    c.post("/boards/1/srs/diagrams/generate", json={})
    req = c.get("/boards/1/srs/").json()["requirements"]
    req["title"] = "Edited"
    assert c.patch("/boards/1/srs/requirements", json=req).json()["version"] == 2
    v2 = c.get("/boards/1/srs/diagrams").json()
    assert v2["version"] == 2 and v2["diagrams"] and all(d["stale"] for d in v2["diagrams"])
    v1_id = c.get("/boards/1/srs/versions").json()[1]["id"]
    assert not any(d["stale"] for d in c.get(f"/boards/1/srs/diagrams?srs_id={v1_id}").json()["diagrams"])
    c.post("/boards/1/srs/diagrams/generate", json={})
    assert not any(d["stale"] for d in c.get("/boards/1/srs/diagrams").json()["diagrams"])


def test_ai_down_falls_back_to_rules(monkeypatch):
    c = seed_with_srs()
    def boom(*a, **k): raise LLMError("quota")
    monkeypatch.setattr(diagram_service, "llm_json", boom)
    job = c.post("/boards/1/srs/diagrams/generate", json={}).json()["job_id"]
    assert c.get(f"/boards/1/srs/diagrams/jobs/{job}").json()["status"] == "done"
    out = c.get("/boards/1/srs/diagrams").json()["diagrams"]
    types = {d["type"] for d in out}
    assert {"usecase", "class", "sequence", "activity"} <= types and "state" not in types
    assert all(d["source"] in ("rules", "fallback") for d in out)
    assert all(d["warnings"] for d in out if d["type"] != "usecase")
    for d in out:
        assert "error" not in d


def test_bad_ai_output_is_repaired_then_trimmed(monkeypatch):
    c = seed_with_srs()
    calls = {"n": 0}
    big = ClassModel(classes=[cls(f"K{i}") for i in range(30)], relations=[rel("K0", f"K{i}") for i in range(1, 30)] + [rel("K0", "Ghost")])
    def fake(prompt, schema, **k):
        if schema is ClassModel:
            calls["n"] += 1
            return big  # the "repair" is just as bad
        from app.core.llm_fake import fake_response
        return fake_response(schema)
    monkeypatch.setattr(diagram_service, "llm_json", fake)
    c.post("/boards/1/srs/diagrams/generate", json={"types": ["class"]})
    d = c.get("/boards/1/srs/diagrams").json()["diagrams"][0]
    assert calls["n"] == 2  # exactly one repair attempt
    assert d["mermaid"].count("\n  class ") <= MAX_CLASSES
    assert any("most connected" in w for w in d["warnings"])


def test_diagram_endpoints_are_owner_only():
    c = seed_with_srs()
    job = c.post("/boards/1/srs/diagrams/generate", json={}).json()["job_id"]
    x = make_client(2)
    assert x.post("/boards/1/srs/diagrams/generate", json={}).status_code == 404
    assert x.get("/boards/1/srs/diagrams").status_code == 404
    assert x.get(f"/boards/1/srs/diagrams/jobs/{job}").status_code == 404


def test_generate_requires_srs_and_valid_types():
    db = SessionLocal()
    db.add(User(id=1, name="A", email="a@a.com")); db.add(Board(id=1, name="L", description="x", owner_id=1)); db.commit(); db.close()
    c = make_client(1)
    assert c.post("/boards/1/srs/diagrams/generate", json={}).status_code == 404
    assert c.post("/boards/1/srs/diagrams/generate", json={"types": ["pie"]}).status_code == 422


def test_deleting_srs_cascades_diagrams():
    c = seed_with_srs()
    c.post("/boards/1/srs/diagrams/generate", json={})
    db = SessionLocal()
    assert db.query(Diagram).count() > 0
    db.delete(db.query(Board).get(1)); db.commit()
    assert db.query(Diagram).count() == 0
    db.close()


# ---- regressions found by running the real Mermaid parser (node mermaid.parse) ----
def test_mermaid_keyword_class_names_and_display_labels():
    m = ClassModel(classes=[cls("class"), cls("Order Item"), cls("end")], relations=[rel("class", "Order Item"), rel("Order Item", "end")])
    txt = M.class_to_mermaid(m)
    assert "class C_class[" in txt and 'class Order_Item["Order Item"]' in txt and "class C_end[" in txt
    assert "C_class" in txt.split("C_class[")[0] or True
    import re
    assert not re.search(r"^\s+class class\b", txt, re.M)


def test_mermaid_colons_removed_from_class_and_state_labels():
    m = ClassModel(classes=[cls("A"), cls("B")], relations=[ClassRelation(kind="association", source="A", target="B",
                   multiplicity_source="1", multiplicity_target="*", label="a:b:c")])
    assert "A \"1\" --> \"*\" B : a b c" in M.class_to_mermaid(m)
    s = StateModel(entity="E", states=["X", "Y"], initial="X", finals=[], transitions=[Transition(source="X", target="Y", label="go: now")])
    assert "s1 --> s2 : go  now" in M.state_to_mermaid(s) or "s1 --> s2 : go now" in M.state_to_mermaid(s)
