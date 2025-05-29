from pydantic import BaseModel

import uuid


class TeamMemberResponse(BaseModel):
    user_id: uuid.UUID


class TeamMemberRequest(BaseModel):
    user_id: uuid.UUID