"""Structured requirements model. Deliberately flat (no dicts, no recursion)
so Gemini's structured-output mode accepts it."""
from typing import Literal

from pydantic import BaseModel, Field


class Actor(BaseModel):
    name: str
    description: str


class FR(BaseModel):
    id: str = Field(description="FR-001, FR-002, ...")
    title: str
    statement: str = Field(description='Must start like "The system shall ..."')
    priority: Literal["must", "should", "could"]
    actor: str
    acceptance_criteria: list[str]


class NFR(BaseModel):
    id: str = Field(description="NFR-001, NFR-002, ...")
    category: Literal[
        "performance", "security", "usability", "reliability",
        "maintainability", "compatibility", "scalability",
    ]
    statement: str
    metric: str = Field(description="A measurable target, e.g. '95% of requests under 2 s'")


class UseCase(BaseModel):
    id: str = Field(description="UC-001, UC-002, ...")
    name: str
    actor: str
    description: str
    fr_ids: list[str]
    preconditions: list[str]
    main_flow: list[str]
    alternate_flows: list[str]


class Entity(BaseModel):
    name: str
    description: str
    attributes: list[str]
    relations: list[str] = Field(description="e.g. 'Order has many OrderItem'")


class Term(BaseModel):
    term: str
    definition: str


class Requirements(BaseModel):
    title: str
    purpose: str
    scope: str
    product_perspective: str
    definitions: list[Term]
    actors: list[Actor]
    functional_requirements: list[FR]
    non_functional_requirements: list[NFR]
    use_cases: list[UseCase]
    entities: list[Entity]
    constraints: list[str]
    assumptions: list[str]
    external_interfaces: list[str]
    open_issues: list[str]


# ---- question step -------------------------------------------------------
class Question(BaseModel):
    id: str
    question: str
    options: list[str]


class QuestionList(BaseModel):
    questions: list[Question]


# ---- API request / response bodies ---------------------------------------
class AnswerIn(BaseModel):
    question: str = Field(max_length=500)
    answer: str = Field(max_length=600)


class QuestionsRequest(BaseModel):
    description: str = Field(min_length=20, max_length=4000)


class GenerateRequest(BaseModel):
    description: str = Field(min_length=20, max_length=4000)
    answers: list[AnswerIn] = Field(default_factory=list, max_length=12)


class Issue(BaseModel):
    level: Literal["error", "warning"]
    code: str
    message: str
