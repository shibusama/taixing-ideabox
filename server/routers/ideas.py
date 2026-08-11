"""Ideas CRUD routes (soft delete / archive / tags / export / import)."""

import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import SessionLocal
from helpers import _now_ms, _new_id, _rebuild_tags
from models import Idea, Tag

router = APIRouter()


class IdeaPayload(BaseModel):
    content: str
    tags: list[str] = []
    pinned: bool = False
    id: str | None = None
    createdAt: float | None = None
    updatedAt: float | None = None


@router.get("/api/ideas")
def list_ideas():
    with SessionLocal() as db:
        rows = (
            db.query(Idea)
            .filter(Idea.deleted_at.is_(None))
            .order_by(Idea.pinned.desc(), Idea.created_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]


@router.get("/api/ideas/archived")
def list_archived():
    with SessionLocal() as db:
        rows = (
            db.query(Idea)
            .filter(Idea.deleted_at.is_not(None))
            .order_by(Idea.deleted_at.desc())
            .all()
        )
        return [r.to_dict(include_deleted=True) for r in rows]


@router.post("/api/ideas")
def create_idea(payload: IdeaPayload):
    now = _now_ms()
    idea = Idea(
        id=payload.id or _new_id(),
        content=payload.content.strip(),
        tags=list(dict.fromkeys(payload.tags)),
        pinned=1 if payload.pinned else 0,
        created_at=payload.createdAt or now,
        updated_at=payload.updatedAt or now,
        deleted_at=None,
    )
    with SessionLocal() as db:
        db.add(idea)
        _rebuild_tags(db)
        db.commit()
        return idea.to_dict()


@router.put("/api/ideas/{idea_id}")
def update_idea(idea_id: str, payload: IdeaPayload):
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None or idea.deleted_at is not None:
            raise HTTPException(404, "idea not found")
        if payload.content is not None:
            idea.content = payload.content.strip()
        if payload.tags is not None:
            idea.tags = list(dict.fromkeys(payload.tags))
        if payload.pinned is not None:
            idea.pinned = 1 if payload.pinned else 0
        idea.updated_at = _now_ms()
        _rebuild_tags(db)
        db.commit()
        return idea.to_dict()


@router.delete("/api/ideas/{idea_id}")
def delete_idea(idea_id: str):
    """Soft delete -> move to archive."""
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(404, "idea not found")
        idea.deleted_at = _now_ms()
        idea.updated_at = _now_ms()
        _rebuild_tags(db)
        db.commit()
        return {"ok": True}


@router.post("/api/ideas/{idea_id}/restore")
def restore_idea(idea_id: str):
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(404, "idea not found")
        idea.deleted_at = None
        idea.updated_at = _now_ms()
        _rebuild_tags(db)
        db.commit()
        return idea.to_dict()


@router.post("/api/ideas/{idea_id}/pin")
def toggle_pin(idea_id: str):
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None or idea.deleted_at is not None:
            raise HTTPException(404, "idea not found")
        idea.pinned = 0 if idea.pinned else 1
        idea.updated_at = _now_ms()
        db.commit()
        return idea.to_dict()


@router.delete("/api/archived")
def purge_archived():
    """Permanently delete archived ideas."""
    with SessionLocal() as db:
        db.query(Idea).filter(Idea.deleted_at.is_not(None)).delete()
        db.commit()
        return {"ok": True}


@router.get("/api/tags")
def list_tags():
    with SessionLocal() as db:
        return [
            {"name": t.name, "count": t.count}
            for t in db.query(Tag).order_by(Tag.count.desc(), Tag.name).all()
        ]


@router.get("/api/export")
def export_data():
    with SessionLocal() as db:
        ideas = db.query(Idea).all()
        return {
            "ideas": [i.to_dict() for i in ideas if i.deleted_at is None],
            "archived": [i.to_dict(include_deleted=True) for i in ideas if i.deleted_at is not None],
            "exportedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


@router.post("/api/import")
def import_data(payload: dict):
    """Replace all ideas+archived with the given dataset."""
    ideas_in = payload.get("ideas", []) or []
    archived_in = payload.get("archived", []) or []
    now = _now_ms()
    with SessionLocal() as db:
        db.query(Idea).delete()
        for item in ideas_in + archived_in:
            deleted = item.get("deletedAt")
            db.add(
                Idea(
                    id=item.get("id") or _new_id(),
                    content=str(item.get("content", "")).strip(),
                    tags=list(dict.fromkeys(item.get("tags", []) or [])),
                    pinned=1 if item.get("pinned") else 0,
                    created_at=float(item.get("createdAt") or now),
                    updated_at=float(item.get("updatedAt") or now),
                    deleted_at=float(deleted) if deleted is not None else None,
                )
            )
        _rebuild_tags(db)
        db.commit()
        return {"ok": True, "imported": len(ideas_in) + len(archived_in)}