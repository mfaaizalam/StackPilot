"""Software Design Description (SDD) models, structured after IEEE 1016.

Flat on purpose (no dicts, no recursion) so Gemini's structured-output mode accepts them.
The AI fills `DesignModel`; our code validates, cleans and renders it. The AI never draws
and never writes the final document."""
from typing import Literal

from pydantic import BaseModel, Field

# ---- hard limits enforced in code (keep the document readable and the job cheap) ----
MAX_COMPONENTS = 14
MAX_ENDPOINTS = 40
MAX_TABLES = 16
MAX_DECISIONS = 8
MAX_TECH = 8
MAX_NAME = 40

LAYERS = ("presentation", "api", "service", "data", "integration", "infrastructure")
PATTERNS = ("none", "MVC", "Service Layer", "Repository", "Facade", "Adapter",
            "Gateway", "Strategy", "Observer", "Factory", "Unit of Work")


class TechChoice(BaseModel):
    layer: str = Field(description='e.g. "Frontend", "Backend", "Database", "Hosting"')
    technology: str = Field(description="Named in the constraints or deployment diagram; otherwise 'To be confirmed'. Never invent products.")
    rationale: str = Field(description="One sentence")


class Component(BaseModel):
    id: str = Field(description="CMP-001, CMP-002, ...")
    name: str = Field(description="Short PascalCase-style name, max 40 characters, e.g. 'LoanService'")
    layer: Literal["presentation", "api", "service", "data", "integration", "infrastructure"]
    responsibility: str = Field(description="One or two sentences")
    pattern: Literal["none", "MVC", "Service Layer", "Repository", "Facade", "Adapter",
                     "Gateway", "Strategy", "Observer", "Factory", "Unit of Work"]
    fr_ids: list[str] = Field(description="Functional requirements this component implements, e.g. FR-003")
    entities: list[str] = Field(description="Data entities this component owns or manipulates")
    depends_on: list[str] = Field(description="Component ids this one calls. Dependencies point DOWN the layers; no cycles.")


class Endpoint(BaseModel):
    id: str = Field(description="API-001, API-002, ...")
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = Field(description="Starts with '/', REST style, plural nouns, e.g. /api/v1/loans/{id}")
    summary: str = Field(description="Max 80 characters")
    actor: str = Field(description="Actor allowed to call it, named exactly as in the SRS")
    fr_ids: list[str]
    component_id: str = Field(description="The service component that handles it")
    request: str = Field(description="Short description of path/query/body inputs, or empty")
    response: str = Field(description="Short description of the success response")
    auth_required: bool
    errors: list[str] = Field(description='e.g. "404 Book not found"')


class TableDesign(BaseModel):
    entity: str = Field(description="SRS entity this table stores, named exactly")
    table: str = Field(description="snake_case plural table name")
    columns: list[str] = Field(description='e.g. "id: SERIAL PRIMARY KEY", "email: VARCHAR(255) UNIQUE NOT NULL"')
    indexes: list[str] = Field(description='e.g. "idx_loans_member_id (member_id)"')
    notes: str = Field(description="Integrity rules, retention, or empty")


class QualityTactic(BaseModel):
    nfr_id: str = Field(description="NFR-001, ...")
    tactic: str = Field(description="The concrete design measure that satisfies the requirement")
    realized_by: list[str] = Field(description="Component ids that implement the tactic")


class DesignDecision(BaseModel):
    id: str = Field(description="DD-001, DD-002, ...")
    title: str
    decision: str
    rationale: str
    alternatives: list[str] = Field(description="Options that were considered and rejected")
    nfr_ids: list[str] = Field(description="Requirements that drove the decision")


class DesignModel(BaseModel):
    architecture_style: str = Field(description='e.g. "Layered architecture with a REST API"')
    architecture_overview: str = Field(description="Two to four sentences describing how the system is structured")
    technology_stack: list[TechChoice]
    components: list[Component]
    endpoints: list[Endpoint]
    tables: list[TableDesign]
    quality_tactics: list[QualityTactic]
    decisions: list[DesignDecision]
    error_handling: list[str] = Field(description="Cross-cutting rules: validation errors, logging, retries, user messages")
    design_risks: list[str]


# ---- API request / response bodies --------------------------------------
class SDDGenerateRequest(BaseModel):
    srs_id: int | None = None  # default: latest SRS version of the board