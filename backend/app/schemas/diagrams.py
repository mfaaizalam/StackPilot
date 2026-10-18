"""Diagram models. Flat on purpose (no dicts, no recursion) so Gemini's
structured-output mode accepts them. The AI fills these; our code validates,
trims and renders them."""
from typing import Literal

from pydantic import BaseModel, Field

# Hard limits enforced in code (Phase 3.2). These are what keep diagrams readable.
MAX_LABEL = 28
MAX_CLASSES = 12
MAX_CLASS_MEMBERS = 8
MAX_RELATIONS = 18
MAX_PARTICIPANTS = 8
MAX_MESSAGES = 15
MAX_FRAGMENTS = 3
MAX_ACTIVITY_NODES = 18
MAX_STATES = 8
MAX_TRANSITIONS = 14
MAX_UC_RELATIONS = 6
MAX_DEPLOY_NODES = 8
MAX_DEPLOY_ARTIFACTS = 4
MAX_DEPLOY_LINKS = 12
DIAGRAM_TYPES = ["usecase", "class", "sequence", "activity", "state", "deployment"]


# ---- class ----------------------------------------------------------------
class ClassNode(BaseModel):
    name: str = Field(description="PascalCase singular noun, no spaces")
    attributes: list[str] = Field(description='e.g. "email: String"')
    methods: list[str] = Field(description='e.g. "borrowBook" (no parentheses)')


class ClassRelation(BaseModel):
    kind: Literal["association", "aggregation", "composition", "inheritance"]
    source: str = Field(description="For aggregation/composition: the whole. For inheritance: the child.")
    target: str = Field(description="For aggregation/composition: the part. For inheritance: the parent.")
    multiplicity_source: str = Field(description='"1", "0..1", "*", "1..*" or ""')
    multiplicity_target: str
    label: str = Field(description="Short verb phrase, max 20 characters, or empty")


class ClassModel(BaseModel):
    classes: list[ClassNode]
    relations: list[ClassRelation]


# ---- sequence -------------------------------------------------------------
class Message(BaseModel):
    source: str = Field(description="Participant name, exactly as listed")
    target: str
    text: str = Field(description="Max 28 characters")
    kind: Literal["sync", "return", "async"]


class Fragment(BaseModel):
    kind: Literal["opt", "alt", "loop"]
    label: str
    start: int = Field(description="1-based index of the first message inside the fragment")
    end: int = Field(description="1-based index of the last message inside the fragment")


class SequenceModel(BaseModel):
    participants: list[str]
    messages: list[Message]
    fragments: list[Fragment]


# ---- activity -------------------------------------------------------------
class ActNode(BaseModel):
    id: str = Field(description="n1, n2, ...")
    kind: Literal["start", "action", "decision", "merge", "end"]
    label: str = Field(description="Max 28 characters; empty for start/merge/end")


class ActEdge(BaseModel):
    source: str
    target: str
    label: str = Field(description='Guard such as "Yes"/"No", or empty')


class ActivityModel(BaseModel):
    nodes: list[ActNode]
    edges: list[ActEdge]


# ---- state ----------------------------------------------------------------
class Transition(BaseModel):
    source: str
    target: str
    label: str = Field(description="The event or action that triggers it, max 28 characters")


class StateModel(BaseModel):
    entity: str
    states: list[str]
    initial: str
    finals: list[str]
    transitions: list[Transition]


class StateModelSet(BaseModel):
    machines: list[StateModel]

# ---- deployment -----------------------------------------------------------
class DeployNode(BaseModel):
    id: str = Field(description="d1, d2, ...")
    name: str = Field(description='Short node name, max 28 characters, e.g. "Web Server"')
    kind: Literal["client", "server", "database", "external"]
    technology: str = Field(description='Runtime / platform, e.g. "Ubuntu + Nginx", max 28 characters, or empty')
    artifacts: list[str] = Field(description='Software deployed on this node, e.g. "Web App". 1 to 4 items')


class DeployLink(BaseModel):
    source: str = Field(description="Node id, e.g. d1")
    target: str = Field(description="Node id, e.g. d2")
    protocol: str = Field(description='e.g. "HTTPS" or "SQL/TCP", max 20 characters, or empty')


class DeploymentModel(BaseModel):
    nodes: list[DeployNode]
    links: list[DeployLink]
# ---- use case -------------------------------------------------------------
class Rel(BaseModel):
    source: str = Field(description="Use case id, e.g. UC-002")
    target: str


class UseCaseRelations(BaseModel):
    includes: list[Rel] = Field(description="source ALWAYS needs target")
    extends: list[Rel] = Field(description="source optionally extends target")


class UCActor(BaseModel):
    name: str
    external: bool = False


class UCNode(BaseModel):
    id: str
    name: str
    actor: str


class UseCaseModel(BaseModel):
    system: str
    actors: list[UCActor]
    use_cases: list[UCNode]
    includes: list[Rel] = []
    extends: list[Rel] = []


# ---- API ------------------------------------------------------------------
class DiagramGenerateRequest(BaseModel):
    srs_id: int | None = None
    types: list[Literal["usecase", "class", "sequence", "activity", "state", "deployment"]] | None = None
