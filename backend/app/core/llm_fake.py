"""Canned answers used when LLM_FAKE=1 (unit tests and the offline exhibition fallback)."""
from app.schemas.diagrams import (
    ActivityModel, ClassModel, SequenceModel, StateModelSet, UseCaseRelations,
)
from app.schemas.cost import CostExplanation
from app.schemas.srs import QuestionList, Requirements


def sample_requirements() -> Requirements:
    actors = [
        {"name": "Member", "description": "A registered library user who borrows books."},
        {"name": "Librarian", "description": "Staff who manage the catalogue and loans."},
        {"name": "Administrator", "description": "Manages accounts and system settings."},
    ]
    frs = [
        ("FR-001", "Register account", "The system shall allow a visitor to register with name, email and password.", "must", "Member"),
        ("FR-002", "Search catalogue", "The system shall allow a member to search books by title, author or ISBN.", "must", "Member"),
        ("FR-003", "Borrow book", "The system shall allow a member to borrow an available book for up to 14 days.", "must", "Member"),
        ("FR-004", "Return book", "The system shall allow a librarian to record the return of a book.", "must", "Librarian"),
        ("FR-005", "Manage catalogue", "The system shall allow a librarian to add, edit and remove books.", "must", "Librarian"),
        ("FR-006", "Calculate fines", "The system shall calculate a fine for every day a book is overdue.", "should", "Librarian"),
        ("FR-007", "Manage users", "The system shall allow an administrator to deactivate member accounts.", "should", "Administrator"),
        ("FR-008", "Send reminders", "The system shall email a member two days before a due date.", "could", "Member"),
    ]
    ucs = [
        ("UC-001", "Register", "Member", ["FR-001"]),
        ("UC-002", "Find and borrow a book", "Member", ["FR-002", "FR-003", "FR-008"]),
        ("UC-003", "Process a return", "Librarian", ["FR-004", "FR-006"]),
        ("UC-004", "Maintain catalogue", "Librarian", ["FR-005"]),
        ("UC-005", "Administer users", "Administrator", ["FR-007"]),
    ]
    return Requirements.model_validate({
        "title": "Library Management System",
        "purpose": "Define the requirements of a web system that manages a library's catalogue and loans.",
        "scope": "Catalogue management, member accounts, borrowing, returns and fines for a single library.",
        "product_perspective": "A standalone web application with a relational database.",
        "definitions": [{"term": "ISBN", "definition": "International Standard Book Number."}],
        "actors": actors,
        "functional_requirements": [
            {"id": i, "title": t, "statement": s, "priority": p, "actor": a,
             "acceptance_criteria": [f"{t} succeeds with valid input.", f"{t} shows a clear error for invalid input."]}
            for i, t, s, p, a in frs
        ],
        "non_functional_requirements": [
            {"id": "NFR-001", "category": "performance", "statement": "Search results shall load quickly.", "metric": "95% of searches return in under 2 seconds"},
            {"id": "NFR-002", "category": "security", "statement": "Passwords shall be stored securely.", "metric": "Passwords hashed with bcrypt, cost factor at least 12"},
            {"id": "NFR-003", "category": "reliability", "statement": "The system shall be available during opening hours.", "metric": "99% uptime between 08:00 and 20:00"},
        ],
        "use_cases": [
            {"id": i, "name": n, "actor": a, "description": f"{a} performs: {n}.", "fr_ids": f,
             "preconditions": ["The user is logged in."] if i != "UC-001" else [],
             "main_flow": ["The actor starts the action.", "The system validates the input.", "The system confirms the result."],
             "alternate_flows": ["Input is invalid: the system shows an error and the actor retries."]}
            for i, n, a, f in ucs
        ],
        "entities": [
            {"name": "Member", "description": "A library user.", "attributes": ["id", "name", "email", "status"], "relations": ["Member has many Loan"]},
            {"name": "Book", "description": "A catalogue item.", "attributes": ["id", "title", "author", "isbn", "copies"], "relations": ["Book has many Loan"]},
            {"name": "Loan", "description": "A borrowing record.", "attributes": ["id", "borrowed_on", "due_on", "returned_on", "fine"], "relations": ["Loan belongs to Member", "Loan belongs to Book"]},
        ],
        "constraints": ["Must run in a standard web browser."],
        "assumptions": ["Only one library branch is supported."],
        "external_interfaces": ["Email service (SMTP) for reminders."],
        "open_issues": ["Fine rate per day is not yet decided."],
    })


def _fake_diagram(schema):
    """Canned diagram models (match sample_requirements) for tests and the offline demo."""
    if schema is ClassModel:
        return ClassModel.model_validate({
            "classes": [
                {"name": "Member", "attributes": ["id: Integer", "name: String", "email: String"], "methods": ["register", "borrowBook"]},
                {"name": "Book", "attributes": ["id: Integer", "title: String", "isbn: String", "copies: Integer"], "methods": ["isAvailable"]},
                {"name": "Loan", "attributes": ["id: Integer", "borrowedOn: Date", "dueOn: Date", "fine: Decimal"], "methods": ["calculateFine", "markReturned"]},
            ],
            "relations": [
                {"kind": "association", "source": "Member", "target": "Loan", "multiplicity_source": "1", "multiplicity_target": "*", "label": "borrows"},
                {"kind": "association", "source": "Book", "target": "Loan", "multiplicity_source": "1", "multiplicity_target": "*", "label": "lent in"},
            ]})
    if schema is SequenceModel:
        m = lambda a, b, t, k="sync": {"source": a, "target": b, "text": t, "kind": k}
        return SequenceModel.model_validate({
            "participants": ["Member", "Web App", "Server", "Database"],
            "messages": [
                m("Member", "Web App", "Search by title"), m("Web App", "Server", "GET /books?q="),
                m("Server", "Database", "Query catalogue"), m("Database", "Server", "Matching books", "return"),
                m("Server", "Web App", "Book list", "return"), m("Member", "Web App", "Choose Borrow"),
                m("Web App", "Server", "POST /loans"), m("Server", "Database", "Save loan"),
                m("Server", "Web App", "Loan confirmed", "return"),
            ],
            "fragments": [{"kind": "opt", "label": "Book available", "start": 6, "end": 9}]})
    if schema is ActivityModel:
        n = lambda i, k, l="": {"id": i, "kind": k, "label": l}
        e = lambda a, b, l="": {"source": a, "target": b, "label": l}
        return ActivityModel.model_validate({
            "nodes": [n("n1", "start"), n("n2", "action", "Search the catalogue"), n("n3", "decision", "Book available?"),
                      n("n4", "action", "Borrow the book"), n("n5", "action", "Show unavailable notice"),
                      n("n6", "merge"), n("n7", "end")],
            "edges": [e("n1", "n2"), e("n2", "n3"), e("n3", "n4", "Yes"), e("n3", "n5", "No"),
                      e("n4", "n6"), e("n5", "n6"), e("n6", "n7")]})
    if schema is StateModelSet:
        t = lambda a, b, l: {"source": a, "target": b, "label": l}
        return StateModelSet.model_validate({"machines": [{
            "entity": "Loan", "states": ["Active", "Overdue", "Returned"], "initial": "Active", "finals": ["Returned"],
            "transitions": [t("Active", "Returned", "Book returned"), t("Active", "Overdue", "Due date passes"),
                            t("Overdue", "Returned", "Book returned + fine paid")]}]})
    if schema is UseCaseRelations:
        return UseCaseRelations.model_validate({"includes": [], "extends": []})
    raise NotImplementedError


def fake_response(schema):
    if schema is Requirements:
        return sample_requirements()
    if schema is QuestionList:
        return QuestionList.model_validate({"questions": [
            {"id": "q1", "question": "Who will use the system?", "options": ["Students", "Staff", "Both"]},
            {"id": "q2", "question": "Which platform?", "options": ["Web", "Mobile", "Both"]},
            {"id": "q3", "question": "Any integrations needed?", "options": ["Email", "SMS", "Payments", "None"]},
        ]})
    if schema is CostExplanation:
        return CostExplanation.model_validate({
            "summary": "The estimate is driven mainly by team salaries over the project duration.",
            "key_drivers": ["Developer and QA time make up most of the cost.", "Longer duration adds hosting and tool costs."],
            "risks": ["Scope growth raises effort faster than linearly.", "Salary rates may differ from the table."],
            "tips": ["Build the must-have requirements first.", "Verify the salary table with local quotes."]})
    try:
        return _fake_diagram(schema)
    except NotImplementedError:
        raise NotImplementedError(f"No fake data for {schema.__name__}")
