import uuid

from sqlalchemy import Column, UUID, String, DateTime, Table, ForeignKey

from datetime import datetime, timezone

from enum import Enum

from sqlalchemy.orm import relationship

from shared.database import Base


class TeamStatusEnum(str, Enum):
    pendent = 'pendent'
    active = 'active'
    closed = 'closed'


class Team(Base):
    __tablename__ = "teams"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: str = Column(String(100), nullable=False)
    abbreviation: str = Column(String(3), nullable=False)
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    status: TeamStatusEnum = Column(
        String(20),
        default=TeamStatusEnum.pendent,
    )
    members = relationship("TeamMember", back_populates="team")