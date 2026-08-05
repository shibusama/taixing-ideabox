"""SQLAlchemy models for IdeaBox.

Tables:
  ideas    - inspiration items, soft-delete via deleted_at
  tags     - tag counter (denormalized from ideas.tags JSON)
  mindmaps - video mindmap cache (replaces cache/*.json)
  tasks    - persistent mindmap task states (survives restarts)
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


def _now() -> datetime:
    return datetime.now()


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    pinned: Mapped[bool] = mapped_column(Integer, default=0)  # SQLite bool->int
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)
    deleted_at: Mapped[float] = mapped_column(Float, nullable=True)  # soft delete

    def to_dict(self, include_deleted=False):
        d = {
            "id": self.id,
            "content": self.content,
            "tags": self.tags or [],
            "pinned": bool(self.pinned),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if include_deleted:
            d["deletedAt"] = self.deleted_at
        return d


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)


class Mindmap(Base):
    __tablename__ = "mindmaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url_hash: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    mindmap_md: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/running/done/error
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
