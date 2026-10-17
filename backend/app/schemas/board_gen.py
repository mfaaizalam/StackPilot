from typing import Literal

from pydantic import BaseModel


class GenerateBoardRequest(BaseModel):
    srs_id: int | None = None          # default: latest SRS version of the board
    # create  = board must be empty (default, never touches existing work)
    # sync    = keep everything, add tasks only for requirements that have no task yet
    # replace = delete ALL columns/tasks of this board, then build fresh
    mode: Literal["create", "sync", "replace"] = "create"
    include_nfr: bool = True           # also create tasks for non-functional requirements
