import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services import deployment_catalog as D

_DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,98}[a-z0-9])?$")


class StackIn(BaseModel):
    frontend: str
    backend: str
    database: str
    scale: str = "small"
    extras: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("frontend", "backend", "database", "scale")
    @classmethod
    def _known(cls, v, info):
        if v not in D.option_values(info.field_name):
            raise ValueError(f"Unknown {info.field_name} option.")
        return v

    @field_validator("extras")
    @classmethod
    def _extras(cls, v):
        allowed = {c for c, _ in D.EXTRAS}
        if any(x not in allowed for x in v):
            raise ValueError("Unknown optional component.")
        return list(dict.fromkeys(v))      # drop duplicates, keep order


class GenerateIn(BaseModel):
    stack: StackIn
    selected: dict[str, str] = Field(default_factory=dict)
    domain: str | None = Field(default=None, max_length=100)
    environments: list[str] = Field(default_factory=lambda: ["production"], max_length=3)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("domain")
    @classmethod
    def _domain(cls, v):
        v = (v or "").strip().lower()
        if not v:
            return None
        if not _DOMAIN.match(v):
            raise ValueError("Enter a domain like example.com (no http:// or spaces).")
        return v

    @field_validator("environments")
    @classmethod
    def _envs(cls, v):
        if not v or any(e not in D.ENVIRONMENTS for e in v):
            raise ValueError("Choose at least one valid environment.")
        return [e for e in D.ENVIRONMENTS if e in v]


class DocIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: Literal["plan", "configuration", "supporting"] = "supporting"
    content: str = Field(default="", max_length=20000)
    url: str | None = Field(default=None, max_length=500)

    @field_validator("url")
    @classmethod
    def _url(cls, v):
        v = (v or "").strip()
        if not v:
            return None
        if not re.match(r"^https?://[^\s]+$", v, re.I):     # blocks javascript: and other schemes
            raise ValueError("Links must start with http:// or https://")
        return v


class DocUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: Literal["plan", "configuration", "supporting"] | None = None
    content: str | None = Field(default=None, max_length=20000)
    url: str | None = Field(default=None, max_length=500)

    _url = field_validator("url")(DocIn._url.__func__)


class AddToCostingIn(BaseModel):
    months: int = Field(default=12, ge=1, le=60)
