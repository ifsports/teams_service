import uuid

from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.orm import relationship

from shared.database import Base


class TeamMember(Base):
    __tablename__ = 'team_members'

    team_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey('teams.id'), primary_key=True)
    user_id: str = Column(String, primary_key=True)

    team = relationship("Team", back_populates="members")
