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
    kind = Column(String, nullable=True)   # mindmap | cover
    key = Column(String, nullable=True)    # url_hash，按链接聚合状态
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)


# ---------------------------------------------------------------------------
# 行动计划模块 (Action Plan)
# 一个计划 = 一棵树（PlanNode）+ 一条进展流（PlanLog）
# "动态演进"：每记一条进展 → 系统自动推进状态 & 向上汇总
# ---------------------------------------------------------------------------

# 节点/计划状态
PLAN_ACTIVE = "active"       # 进行中
PLAN_DONE = "done"           # 已完成
PLAN_PENDING = "pending"     # 未开始
PLAN_ONHOLD = "onhold"       # 搁置
PLAN_ABANDONED = "abandoned" # 放弃

# 进展动作类型
LOG_CREATE = "create"        # 创建
LOG_COMPLETE = "complete"    # 完成
LOG_ADD = "add"              # 新增分支
LOG_ONHOLD = "onhold"        # 搁置
LOG_RESUME = "resume"        # 恢复
LOG_ABANDON = "abandon"      # 放弃
LOG_NOTE = "note"            # 手动备注/进展


class Plan(Base):
    """一个行动计划。"""
    __tablename__ = "plans"

    id = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    goal = Column(Text, nullable=True)          # 目标
    domain = Column(Text, nullable=True)        # 领域分类（漫剧/博客/安全...）
    status = Column(String, nullable=False, default=PLAN_ACTIVE)
    priority = Column(Text, nullable=True)      # 高/中/低
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "domain": self.domain,
            "status": self.status,
            "priority": self.priority,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class PlanNode(Base):
    """计划树上的一个节点（分支）。root 节点 parent_id 为 None。"""
    __tablename__ = "plan_nodes"

    id = Column(String, primary_key=True)
    plan_id = Column(String, nullable=False)
    parent_id = Column(String, nullable=True)   # None = 根节点
    title = Column(Text, nullable=False)
    status = Column(String, nullable=False, default=PLAN_ACTIVE)
    completed_at = Column(Float, nullable=True)
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "planId": self.plan_id,
            "parentId": self.parent_id,
            "title": self.title,
            "status": self.status,
            "completedAt": self.completed_at,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class PlanLog(Base):
    """计划下的进展流（一条条事件）。"""
    __tablename__ = "plan_logs"

    id = Column(String, primary_key=True)
    plan_id = Column(String, nullable=False)
    node_id = Column(String, nullable=True)     # 关联的节点（可选）
    action = Column(String, nullable=False)
    content = Column(Text, nullable=True)       # 具体描述
    created_at = Column(Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "planId": self.plan_id,
            "nodeId": self.node_id,
            "action": self.action,
            "content": self.content,
            "createdAt": self.created_at,
        }
