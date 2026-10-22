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
MAX_ER_ENTITIES = 14
MAX_ER_ATTRS = 10
MAX_ER_RELATIONS = 22
MAX_DFD_EXTERNALS = 6
MAX_DFD_PROCESSES = 8
MAX_DFD_STORES = 6
MAX_DFD_FLOWS = 26
DIAGRAM_TYPES = ["usecase", "class", "er", "dfd", "sequence", "activity", "state", "deployment"]


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


# ---- entity-relationship --------------------------------------------------
class ErAttribute(BaseModel):
    name: str = Field(description="snake_case column name, e.g. 'member_id'")
    type: str = Field(description='Short data type, e.g. "INT", "VARCHAR(100)", "DATE"')
    key: Literal["PK", "FK", "UK", ""] = Field(description="PK primary key, FK foreign key, UK unique, or empty")


class ErEntity(BaseModel):
    name: str = Field(description="PascalCase singular noun, no spaces")
    attributes: list[ErAttribute]


class ErRelation(BaseModel):
    source: str = Field(description="Entity name")
    target: str = Field(description="Entity name")
    cardinality_source: Literal["one", "zero_or_one", "many", "one_or_many"] = Field(
        description="How many SOURCE rows take part in one relationship")
    cardinality_target: Literal["one", "zero_or_one", "many", "one_or_many"] = Field(
        description="How many TARGET rows take part in one relationship")
    label: str = Field(description="Short verb phrase, max 20 characters, e.g. 'places'")


class ErModel(BaseModel):
    entities: list[ErEntity]
    relations: list[ErRelation]


# ---- data flow (DFD, Yourdon / DeMarco notation) ---------------------------
class DfdExternal(BaseModel):
    id: str = Field(description="e1, e2, ...")
    name: str = Field(description="Max 28 characters, e.g. 'Customer'")


class DfdProcess(BaseModel):
    id: str = Field(description="Level 0: '0'. Level 1: '1', '2', ... Level 2: '1.1', '1.2', ...")
    name: str = Field(description="Verb + noun, max 28 characters, e.g. 'Process Order'")


class DfdStore(BaseModel):
    id: str = Field(description="D1, D2, ...")
    name: str = Field(description="Max 28 characters, e.g. 'Orders'")


class DfdFlow(BaseModel):
    source: str = Field(description="Id of an external, process or store")
    target: str = Field(description="Id of an external, process or store")
    label: str = Field(description="The data that moves, a noun phrase, max 28 characters")


class DfdModel(BaseModel):
    level: Literal[0, 1, 2]
    title: str = Field(description="e.g. 'Level 1 DFD: Order System'")
    parent: str = Field(description="Level 2 only: id of the Level 1 process being exploded, else empty")
    externals: list[DfdExternal]
    processes: list[DfdProcess]
    stores: list[DfdStore]
    flows: list[DfdFlow]


class DfdSet(BaseModel):
    """Level 1 and the Level 2 explosions, generated in one call so ids stay consistent."""
    level1: DfdModel
    level2: list[DfdModel]


# ---- API ------------------------------------------------------------------
class DiagramGenerateRequest(BaseModel):
    srs_id: int | None = None
    types: list[Literal["usecase", "class", "er", "dfd", "sequence", "activity", "state", "deployment"]] | None = None

