from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base

class CurriculumRow(Base):
    __tablename__ = "curricula"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    grade_level = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    items = relationship("CurriculumItemRow", back_populates="curriculum", cascade="all, delete-orphan", order_by="CurriculumItemRow.sequence")

class CurriculumItemRow(Base):
    __tablename__ = "curriculum_items"
    id = Column(String, primary_key=True)
    curriculum_id = Column(String, ForeignKey("curricula.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    subject_id = Column(String, nullable=False)  # Not enforcing foreign key to allow flexible reference, but could
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    day_offset = Column(Integer, nullable=True)

    curriculum = relationship("CurriculumRow", back_populates="items")
    resources = relationship("CurriculumItemResourceRow", back_populates="item", cascade="all, delete-orphan")

class CurriculumItemResourceRow(Base):
    __tablename__ = "curriculum_item_resources"
    id = Column(String, primary_key=True)
    item_id = Column(String, ForeignKey("curriculum_items.id"), nullable=False)
    resource_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)

    item = relationship("CurriculumItemRow", back_populates="resources")
