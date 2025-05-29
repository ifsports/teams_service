from pydantic import BaseModel

import uuid

from datetime import datetime

from typing import List

from teams.models.teams import TeamStatusEnum


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    abbreviation: str
    created_at: datetime
    status: TeamStatusEnum
    members: List[uuid.UUID]

    model_config = {
        "from_attributes": True
    }