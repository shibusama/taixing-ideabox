"""行动计划模块路由：计划 / 树节点 / 进展流。

核心设计（动态演进）：
- 一个计划 = 一棵树（PlanNode，靠 parent_id 表达层级）+ 一条进展流（PlanLog）。
- 用户只有几个动作：建计划、加子节点（分叉）、完成/搁置/放弃/恢复、追加进展。
- 每次动作自动写入一条进展，并触发"向上推进"：某节点所有子节点都完成 → 父节点自动完成。
- 历史永不覆盖，只往后追加 → 每次进展都带来计划的新变动。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import SessionLocal
from helpers import _now_ms, _new_id
from models import (
    Plan, PlanNode, PlanLog,
    PLAN_ACTIVE, PLAN_DONE, PLAN_PENDING, PLAN_ONHOLD, PLAN_ABANDONED,
    LOG_CREATE, LOG_COMPLETE, LOG_ADD, LOG_ONHOLD, LOG_RESUME, LOG_ABANDON, LOG_NOTE,
)

router = APIRouter()

# 有效的单个节点状态（不含"进行中"的自动汇总逻辑，active 即进行中）
NODE_STATUSES = {PLAN_ACTIVE, PLAN_DONE, PLAN_ONHOLD, PLAN_ABANDONED}


# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------

class PlanPayload(BaseModel):
    title: str
    goal: str | None = None
    domain: str | None = None
    priority: str | None = None


class NodePayload(BaseModel):
    title: str
    parent_id: str | None = None


class LogPayload(BaseModel):
    node_id: str | None = None
    content: str | None = None


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _add_log(db, plan_id, action, node_id=None, content=None):
    db.add(PlanLog(
        id=_new_id(),
        plan_id=plan_id,
        node_id=node_id,
        action=action,
        content=content,
        created_at=_now_ms(),
    ))


def _set_done_chain(db, node: PlanNode):
    """把一个节点标记完成，并向上推进：若父节点的所有子节点都完成，则父节点也完成。"""
    node.status = PLAN_DONE
    node.completed_at = _now_ms()
    node.updated_at = _now_ms()
    _add_log(db, node.plan_id, LOG_COMPLETE, node.id, node.title)

    # 向上推进
    cur = node
    while cur.parent_id is not None:
        parent = db.get(PlanNode, cur.parent_id)
        if parent is None:
            break
        siblings = db.query(PlanNode).filter(
            PlanNode.parent_id == parent.id,
            PlanNode.id != parent.id,  # 不含自身（只用 parent 定位）
        ).all()
        # 实际子节点
        children = db.query(PlanNode).filter(PlanNode.parent_id == parent.id).all()
        if not children:
            break
        if all(c.status == PLAN_DONE for c in children):
            parent.status = PLAN_DONE
            parent.completed_at = _now_ms()
            parent.updated_at = _now_ms()
            _add_log(db, parent.plan_id, LOG_COMPLETE, parent.id, parent.title)
            cur = parent
        else:
            break


def _sync_plan_status(db, plan_id):
    """根据根节点状态同步计划状态（若计划不含任何节点则不改变）。"""
    root = db.query(PlanNode).filter(
        PlanNode.plan_id == plan_id, PlanNode.parent_id.is_(None)
    ).first()
    if root is None:
        return
    plan = db.get(Plan, plan_id)
    if plan is None:
        return
    if root.status == PLAN_DONE:
        plan.status = PLAN_DONE
    elif root.status == PLAN_ONHOLD:
        plan.status = PLAN_ONHOLD
    elif root.status == PLAN_ABANDONED:
        plan.status = PLAN_ABANDONED
    else:
        plan.status = PLAN_ACTIVE
    plan.updated_at = _now_ms()


# ---------------------------------------------------------------------------
# 计划 CRUD
# ---------------------------------------------------------------------------

@router.get("/api/plans")
def list_plans():
    with SessionLocal() as db:
        rows = db.query(Plan).order_by(Plan.updated_at.desc()).all()
        result = []
        for p in rows:
            d = p.to_dict()
            node_count = db.query(PlanNode).filter(PlanNode.plan_id == p.id).count()
            done_count = db.query(PlanNode).filter(
                PlanNode.plan_id == p.id, PlanNode.status == PLAN_DONE
            ).count()
            d["nodeCount"] = node_count
            d["doneCount"] = done_count
            result.append(d)
        return result


@router.post("/api/plans")
def create_plan(payload: PlanPayload):
    title = payload.title.strip()
    if not title:
        raise HTTPException(400, "计划标题不能为空")
    now = _now_ms()
    plan = Plan(
        id=_new_id(),
        title=title,
        goal=(payload.goal or "").strip() or None,
        domain=(payload.domain or "").strip() or None,
        priority=(payload.priority or "").strip() or None,
        status=PLAN_ACTIVE,
        created_at=now,
        updated_at=now,
    )
    with SessionLocal() as db:
        db.add(plan)
        db.commit()
        # 自动生成根节点
        root = PlanNode(
            id=_new_id(),
            plan_id=plan.id,
            parent_id=None,
            title=title,
            status=PLAN_ACTIVE,
            created_at=now,
            updated_at=now,
        )
        db.add(root)
        _add_log(db, plan.id, LOG_CREATE, root.id, f"创建计划「{title}」")
        db.commit()
        return plan.to_dict()


@router.get("/api/plans/{plan_id}")
def get_plan(plan_id: str):
    with SessionLocal() as db:
        plan = db.get(Plan, plan_id)
        if plan is None:
            raise HTTPException(404, "计划不存在")
        nodes = db.query(PlanNode).filter(PlanNode.plan_id == plan_id).all()
        logs = (
            db.query(PlanLog)
            .filter(PlanLog.plan_id == plan_id)
            .order_by(PlanLog.created_at.asc())
            .all()
        )
        return {
            "plan": plan.to_dict(),
            "nodes": [n.to_dict() for n in nodes],
            "logs": [l.to_dict() for l in logs],
        }


@router.put("/api/plans/{plan_id}")
def update_plan(plan_id: str, payload: PlanPayload):
    with SessionLocal() as db:
        plan = db.get(Plan, plan_id)
        if plan is None:
            raise HTTPException(404, "计划不存在")
        if payload.title is not None and payload.title.strip():
            plan.title = payload.title.strip()
        if payload.goal is not None:
            plan.goal = payload.goal.strip() or None
        if payload.domain is not None:
            plan.domain = payload.domain.strip() or None
        if payload.priority is not None:
            plan.priority = payload.priority.strip() or None
        plan.updated_at = _now_ms()
        db.commit()
        return plan.to_dict()


@router.delete("/api/plans/{plan_id}")
def delete_plan(plan_id: str):
    with SessionLocal() as db:
        plan = db.get(Plan, plan_id)
        if plan is None:
            raise HTTPException(404, "计划不存在")
        db.query(PlanLog).filter(PlanLog.plan_id == plan_id).delete()
        db.query(PlanNode).filter(PlanNode.plan_id == plan_id).delete()
        db.delete(plan)
        db.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# 节点 CRUD
# ---------------------------------------------------------------------------

@router.post("/api/plans/{plan_id}/nodes")
def add_node(plan_id: str, payload: NodePayload):
    title = payload.title.strip()
    if not title:
        raise HTTPException(400, "节点标题不能为空")
    with SessionLocal() as db:
        if db.get(Plan, plan_id) is None:
            raise HTTPException(404, "计划不存在")
        parent = None
        if payload.parent_id:
            parent = db.get(PlanNode, payload.parent_id)
            if parent is None or parent.plan_id != plan_id:
                raise HTTPException(400, "父节点不存在")
        now = _now_ms()
        node = PlanNode(
            id=_new_id(),
            plan_id=plan_id,
            parent_id=parent.id if parent else None,
            title=title,
            status=PLAN_ACTIVE,
            created_at=now,
            updated_at=now,
        )
        db.add(node)
        _add_log(
            db, plan_id, LOG_ADD, node.id,
            f"新增分支「{title}」" + (f" ← 挂在「{parent.title}」下" if parent else ""),
        )
        # 新增子节点后父节点若已完成则恢复为进行中
        if parent and parent.status == PLAN_DONE:
            parent.status = PLAN_ACTIVE
            parent.completed_at = None
            parent.updated_at = now
        db.commit()
        # 同步计划状态
        _sync_plan_status(db, plan_id)
        db.commit()
        return node.to_dict()


@router.post("/api/plans/{plan_id}/nodes/{node_id}/{action}")
def node_action(plan_id: str, node_id: str, action: str):
    """完成 / 搁置 / 放弃 / 恢复 一个节点。action in {done, onhold, abandon, resume}"""
    with SessionLocal() as db:
        node = db.get(PlanNode, node_id)
        if node is None or node.plan_id != plan_id:
            raise HTTPException(404, "节点不存在")
        now = _now_ms()

        if action == "done":
            # 若存在未完成的子节点，不允许直接把父节点标完成（须先完成子项）
            children = db.query(PlanNode).filter(PlanNode.parent_id == node.id).all()
            if children and not all(c.status == PLAN_DONE for c in children):
                raise HTTPException(400, "还有未完成的子分支，请先完成它们")
            _set_done_chain(db, node)
        elif action == "onhold":
            node.status = PLAN_ONHOLD
            node.completed_at = None
            node.updated_at = now
            _add_log(db, plan_id, LOG_ONHOLD, node.id, f"搁置「{node.title}」")
        elif action == "abandon":
            node.status = PLAN_ABANDONED
            node.completed_at = None
            node.updated_at = now
            _add_log(db, plan_id, LOG_ABANDON, node.id, f"放弃「{node.title}」")
        elif action == "resume":
            node.status = PLAN_ACTIVE
            node.completed_at = None
            node.updated_at = now
            _add_log(db, plan_id, LOG_RESUME, node.id, f"恢复「{node.title}」")
        else:
            raise HTTPException(400, "未知动作")
        db.commit()
        _sync_plan_status(db, plan_id)
        db.commit()
        return node.to_dict()


@router.put("/api/plans/{plan_id}/nodes/{node_id}")
def update_node(plan_id: str, node_id: str, payload: NodePayload):
    with SessionLocal() as db:
        node = db.get(PlanNode, node_id)
        if node is None or node.plan_id != plan_id:
            raise HTTPException(404, "节点不存在")
        if payload.title is not None and payload.title.strip():
            node.title = payload.title.strip()
            node.updated_at = _now_ms()
            db.commit()
        return node.to_dict()


@router.delete("/api/plans/{plan_id}/nodes/{node_id}")
def delete_node(plan_id: str, node_id: str):
    """删除节点及其全部子孙节点。"""
    with SessionLocal() as db:
        node = db.get(PlanNode, node_id)
        if node is None or node.plan_id != plan_id:
            raise HTTPException(404, "节点不存在")

        # 收集所有后代 id
        to_delete = set()
        stack = [node.id]
        while stack:
            pid = stack.pop()
            to_delete.add(pid)
            kids = db.query(PlanNode.id).filter(PlanNode.parent_id == pid).all()
            for (kid,) in kids:
                stack.append(kid)
        parent_id = node.parent_id
        db.query(PlanNode).filter(PlanNode.id.in_(to_delete)).delete(
            synchronize_session=False
        )
        _add_log(db, plan_id, LOG_NOTE, None, f"删除分支「{node.title}」及其子项")
        db.commit()

        # 若父节点因此失去全部子节点，且原本已完成 - 无需特别处理
        db.commit()
        return {"ok": True, "deleted": len(to_delete)}


# ---------------------------------------------------------------------------
# 进展流
# ---------------------------------------------------------------------------

@router.post("/api/plans/{plan_id}/logs")
def add_log(plan_id: str, payload: LogPayload):
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(400, "进展内容不能为空")
    with SessionLocal() as db:
        if db.get(Plan, plan_id) is None:
            raise HTTPException(404, "计划不存在")
        node_id = payload.node_id
        if node_id:
            n = db.get(PlanNode, node_id)
            if n is None or n.plan_id != plan_id:
                node_id = None
        _add_log(db, plan_id, LOG_NOTE, node_id, content)
        plan = db.get(Plan, plan_id)
        plan.updated_at = _now_ms()
        db.commit()
        log = db.query(PlanLog).filter(PlanLog.plan_id == plan_id).order_by(
            PlanLog.created_at.desc()
        ).first()
        return log.to_dict() if log else {"ok": True}
