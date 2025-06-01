from pydantic import BaseModel, field_validator

import uuid

from datetime import datetime

from typing import List, Optional

from teams.models.teams import TeamStatusEnum
from teams.schemas.team_members import TeamMemberResponse


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    abbreviation: str
    campus_code: str
    created_at: datetime
    status: TeamStatusEnum
    members: List[TeamMemberResponse]

    model_config = {
        "from_attributes": True
    }


class TeamCreationAcceptedResponse(BaseModel):
    message: str
    team_id: uuid.UUID


class TeamDeleteRequest(BaseModel):
    reason: str


class TeamCreateRequest(BaseModel):
    name: str
    abbreviation: str
    members: List[str]

    @field_validator('abbreviation')
    def validate_abbreviation(cls, v):
        if len(v) != 3:
            raise ValueError("A abreviação tem que ter 3 caracteres")

        return v.upper()


class TeamUpdateRequest(BaseModel):
    name: Optional[str] = None
    abbreviation: Optional[str] = None

    @field_validator('abbreviation')
    def validate_abbreviation(cls, v):
        if len(v) != 3:
            raise ValueError("A abreviação tem que ter 3 caracteres")

        return v.upper()