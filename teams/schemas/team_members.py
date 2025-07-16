from pydantic import BaseModel

import uuid


class TeamMemberResponse(BaseModel):
    user_id: str


class TeamMemberDeleteRequest(BaseModel):
    reason: str


class TeamMemberCreateRequest(BaseModel):
    user_id: str