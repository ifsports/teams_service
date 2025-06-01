from pydantic import BaseModel

import uuid


class TeamMemberResponse(BaseModel):
    user_id: str


class TeamMemberDeleteRequest(BaseModel):
    user_id: str
    reason: str


class TeamMemberCreateRequest(BaseModel):
    user_id: str