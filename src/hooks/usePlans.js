// Plans management hook - CRUD backed by the FastAPI server (SQLite)
// Plan module: 计划列表 / 树节点 / 进展流
import { useCallback, useEffect, useState } from 'react'
import { API_BASE } from '../config'

async function api(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* keep status text */ }
    throw new Error(detail)
  }
  return resp.json()
}

// 状态中文标签
export const STATUS_LABELS = {
  active: '进行中',
  done: '已完成',
  pending: '未开始',
  onhold: '搁置',
  abandoned: '放弃',
}

// 进展动作中文标签
export const LOG_LABELS = {
  create: '创建',
  add: '分叉',
  complete: '完成',
  onhold: '搁置',
  resume: '恢复',
  abandon: '放弃',
  note: '进展',
}

export function usePlans() {
  const [plans, setPlans] = useState([])
  const [current, setCurrent] = useState(null) // { plan, nodes, logs }
  const [loaded, setLoaded] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const refreshList = useCallback(async () => {
    try {
      const list = await api('/api/plans')
      setPlans(list)
    } catch (err) {
      console.error('[usePlans] fetch plans failed:', err)
    }
  }, [])

  const refreshDetail = useCallback(async (planId) => {
    try {
      setLoadingDetail(true)
      const detail = await api(`/api/plans/${planId}`)
      setCurrent(detail)
      // 顺手同步列表里的该计划状态/计数
      setPlans(prev => prev.map(p => {
        if (p.id === planId) {
          const done = detail.plan.status === 'done'
          return {
            ...p,
            status: detail.plan.status,
            nodeCount: detail.nodes.length,
            doneCount: done ? detail.nodes.length : detail.nodes.filter(n => n.status === 'done').length,
            title: detail.plan.title,
            updatedAt: detail.plan.updatedAt,
          }
        }
        return p
      }))
    } catch (err) {
      console.error('[usePlans] fetch plan detail failed:', err)
    } finally {
      setLoadingDetail(false)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    ;(async () => {
      try {
        await refreshList()
      } finally {
        setLoaded(true)
      }
    })()
  }, [refreshList])

  const createPlan = useCallback(async ({ title, goal = '', domain = '', priority = '' }) => {
    const p = await api('/api/plans', {
      method: 'POST',
      body: JSON.stringify({ title, goal, domain, priority }),
    })
    await refreshList()
    return p
  }, [refreshList])

  const updatePlan = useCallback(async (planId, updates) => {
    const p = await api(`/api/plans/${planId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
    await refreshList()
    return p
  }, [refreshList])

  const deletePlan = useCallback(async (planId) => {
    await api(`/api/plans/${planId}`, { method: 'DELETE' })
    await refreshList()
    if (current && current.plan.id === planId) setCurrent(null)
  }, [refreshList, current])

  const addNode = useCallback(async (planId, { title, parentId }) => {
    await api(`/api/plans/${planId}/nodes`, {
      method: 'POST',
      body: JSON.stringify({ title, parent_id: parentId }),
    })
    await refreshDetail(planId)
  }, [refreshDetail])

  const nodeAction = useCallback(async (planId, nodeId, action) => {
    await api(`/api/plans/${planId}/nodes/${nodeId}/${action}`, { method: 'POST' })
    await refreshDetail(planId)
  }, [refreshDetail])

  const updateNode = useCallback(async (planId, nodeId, title) => {
    await api(`/api/plans/${planId}/nodes/${nodeId}`, {
      method: 'PUT',
      body: JSON.stringify({ title }),
    })
    await refreshDetail(planId)
  }, [refreshDetail])

  const deleteNode = useCallback(async (planId, nodeId) => {
    await api(`/api/plans/${planId}/nodes/${nodeId}`, { method: 'DELETE' })
    await refreshDetail(planId)
  }, [refreshDetail])

  const addLog = useCallback(async (planId, { content, nodeId }) => {
    await api(`/api/plans/${planId}/logs`, {
      method: 'POST',
      body: JSON.stringify({ content, node_id: nodeId || null }),
    })
    await refreshDetail(planId)
  }, [refreshDetail])

  return {
    plans, current, loaded, loadingDetail,
    refreshList, refreshDetail, setCurrent,
    createPlan, updatePlan, deletePlan,
    addNode, nodeAction, updateNode, deleteNode, addLog,
  }
}
