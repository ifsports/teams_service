from pydantic import BaseModel

import uuid


class TeamMemberResponse(BaseModel):
    user_id: uuid.UUID


class TeamMemberDeleteRequest(BaseModel):
    user_id: uuid.UUID
    reason: str


class TeamMemberCreateRequest(BaseModel):
    user_id: uuid.UUID