from pydantic import BaseModel

import uuid


class TeamMemberResponse(BaseModel):
    team_id: uuid.UUID
    user_id: uuid.UUID

    model_config = {
        "from_attributes": True
    }