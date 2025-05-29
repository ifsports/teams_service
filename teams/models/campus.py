from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from shared.database import Base


class Campus(Base):
    __tablename__ = 'campus'

    code: str = Column(String(100), primary_key=True)

    teams = relationship("Team", back_populates="campus",  cascade="all, delete-orphan")