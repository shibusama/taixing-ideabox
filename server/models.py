"""
SQLAlchemy ORM models for IdeaBox.

Compatible with both SQLite (local dev) and PostgreSQL (production).
"""

import os

from sqlalchemy import JSON, Column, String, Float, Boolean, Text
from db import Base

# JSONB on PostgreSQL (production); plain JSON on SQLite (local dev).
if os.environ.get("PGDATABASE_URL"):
    from sqlalchemy.dialects.postgresql import JSONB

    JSONType = JSONB
else:
    JSONType = JSON


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    tags = Column(JSONType, nullable=False, default=list)
    pinned = Column(Boolean, nullable=False, default=False)
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)
    deleted_at = Column(Float, nullable=True)

    def to_dict(self, include_deleted=False):
        d = {
            "id": self.id,
            "content": self.content,
            "tags": list(self.tags) if self.tags else [],
            "pinned": bool(self.pinned),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if include_deleted and self.deleted_at is not None:
            d["deletedAt"] = self.deleted_at
        return d


class Tag(Base):
    __tablename__ = "tags"

    name = Column(String, primary_key=True)
    count = Column(Float, nullable=False, default=0)


class Mindmap(Base):
    __tablename__ = "mindmaps"

    url_hash = Column(String, primary_key=True)
    url = Column(Text, nullable=False)
    mindmap_md = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)


class Note(Base):
    __tablename__ = "notes"

    url_hash = Column(String, primary_key=True)
    url = Column(Text, nullable=False)
    note_md = Column(Text, nullable=False)
    detail = Column(Boolean, nullable=False, default=False)
    created_at = Column(Float, nullable=False)


class Cover(Base):
    __tablename__ = "covers"

    url_hash = Column(String, primary_key=True)
    url = Column(Text, nullable=False)
    image_url = Column(Text, nullable=False)
    prompt = Column(Text, nullable=True)
    created_at = Column(Float, nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True)
    url = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    result = Column(JSONType, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)
