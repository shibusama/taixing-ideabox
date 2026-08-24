import { useState, useMemo, useCallback } from 'react'
import { usePlans, STATUS_LABELS, LOG_LABELS } from '../hooks/usePlans'

// ---------------------------------------------------------------------------
// 状态徽标颜色
// ---------------------------------------------------------------------------
const STATUS_COLOR = {
  active: 'bg-pop-green text-white',
  done: 'bg-pop-blue text-white',
  onhold: 'bg-pop-orange text-white',
  abandoned: 'bg-pop-red text-white',
  pending: 'bg-pop-yellow text-pop-black',
}

function StatusBadge({ status }) {
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-display uppercase tracking-wide border-2 border-pop-black ${STATUS_COLOR[status] || 'bg-pop-yellow text-pop-black'}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

// ---------------------------------------------------------------------------
// 新建计划表单（胶囊区域）
// ---------------------------------------------------------------------------
function NewPlanForm({ onCreate, onCancel }) {
  const [title, setTitle] = useState('')
  const [goal, setGoal] = useState('')
  const [domain, setDomain] = useState('')
  const [priority, setPriority] = useState('中')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    if (!title.trim()) { setError('标题不能为空'); return }
    setBusy(true)
    try {
      await onCreate({ title, goal, domain, priority })
      setTitle(''); setGoal(''); setDomain('')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="pop-card p-4 mb-6 animate-pop-in">
      <div className="flex items-center gap-2 mb-3">
        <span className="star-burst text-sm"><svg className="w-3.5 h-3.5 text-pop-black" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2L14.5 8.5L21 9.5L16 14.5L17.5 21L12 17.5L6.5 21L8 14.5L3 9.5L9.5 8.5L12 2Z"/></svg></span>
        <h2 className="font-display text-lg text-pop-black uppercase tracking-wide">新建行动计划</h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <input
          className="input-pop px-3 py-2 text-sm sm:col-span-3"
          placeholder="计划标题（如：漫剧第一卷 / 博客周更 / 渗透测试学习）"
          value={title}
          onChange={e => { setTitle(e.target.value); setError('') }}
        />
        <input
          className="input-pop px-3 py-2 text-sm sm:col-span-3"
          placeholder="目标（一句话：要达成什么）"
          value={goal}
          onChange={e => setGoal(e.target.value)}
        />
        <input
          className="input-pop px-3 py-2 text-sm"
          placeholder="领域（漫剧/博客/安全…）"
          value={domain}
          onChange={e => setDomain(e.target.value)}
        />
        <select className="input-pop px-3 py-2 text-sm" value={priority} onChange={e => setPriority(e.target.value)}>
          <option value="高">优先级 · 高</option>
          <option value="中">优先级 · 中</option>
          <option value="低">优先级 · 低</option>
        </select>
      </div>
      {error && <p className="mt-2 text-xs font-bold text-pop-red font-sans">⚠ {error}</p>}
      <div className="flex gap-2 mt-3">
        <button className="btn-pop-green text-sm px-4 py-1.5" onClick={submit} disabled={busy}>
          {busy ? '创建中…' : '+ 创建'}
        </button>
        {onCancel && (
          <button className="btn-ghost-pop text-sm" onClick={onCancel}>取消</button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// 计划卡片（列表）
// ---------------------------------------------------------------------------
function PlanCard({ plan, onOpen, onDelete }) {
  const pct = plan.nodeCount ? Math.round((plan.doneCount / plan.nodeCount) * 100) : 0
  return (
    <div className="pop-card p-4 flex flex-col gap-3 group">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <StatusBadge status={plan.status} />
          {plan.domain && (
            <span className="tag-pop bg-pop-pink text-white border-pop-black">{plan.domain}</span>
          )}
          {plan.priority && plan.priority !== '中' && (
            <span className="text-[10px] font-bold font-mono text-pop-black/60 uppercase">{plan.priority}优先级</span>
          )}
        </div>
        <button
          onClick={() => onDelete(plan.id)}
          className="text-pop-black/40 hover:text-pop-red transition-colors opacity-0 group-hover:opacity-100"
          title="删除计划"
          aria-label="删除计划"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <button onClick={() => onOpen(plan.id)} className="text-left">
        <h3 className="font-display text-xl text-pop-black uppercase tracking-wide leading-tight">{plan.title}</h3>
        {plan.goal && <p className="text-sm font-sans text-pop-black/70 mt-0.5">{plan.goal}</p>}
      </button>

      {/* 进度条 */}
      <div className="mt-1">
        <div className="flex items-center justify-between text-[10px] font-bold font-mono text-pop-black/60 mb-1 uppercase">
          <span>完成度</span><span>{plan.doneCount}/{plan.nodeCount} · {pct}%</span>
        </div>
        <div className="h-3 bg-pop-yellow border-2 border-pop-black">
          <div className="h-full bg-pop-green border-r-2 border-pop-black transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <button onClick={() => onOpen(plan.id)} className="btn-pop-blue text-xs px-3 py-1 mt-1 self-start">
        打开 → 查看分支
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// 树的渲染（递归，使用 EditableTree）
// ---------------------------------------------------------------------------
function EditableTree({ nodes, planId, onAction, onAddChild, onDelete, onRename }) {
  const [expanded, setExpanded] = useState({})
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [addingParent, setAddingParent] = useState(null)
  const [newTitle, setNewTitle] = useState('')

  const toggle = useCallback((id) => {
    setExpanded(prev => ({ ...prev, [id]: prev[id] === false }))
  }, [])

  const startEdit = useCallback((node) => {
    setEditingId(node.id)
    setEditTitle(node.title)
  }, [])

  const submitEdit = async () => {
    if (editTitle.trim()) {
      await onRename(editingId, editTitle.trim())
    }
    setEditingId(null)
  }

  const startAdd = useCallback((parentId) => {
    setAddingParent(parentId)
    setNewTitle('')
  }, [])

  const submitAdd = async () => {
    if (newTitle.trim() && addingParent != null) {
      await onAddChild(addingParent, newTitle.trim())
    }
    setAddingParent(null)
    setNewTitle('')
  }

  const roots = nodes.filter(n => n.parentId === null)

  const renderNode = (node, depth) => {
    const children = nodes.filter(n => n.parentId === node.id)
    const isExpanded = expanded[node.id] !== false
    const editing = editingId === node.id

    return (
      <div key={node.id} className="relative">
        <div className="flex items-center gap-2 py-1 group" style={{ paddingLeft: `${depth * 20}px` }}>
          <div className="flex-shrink-0 w-5 flex items-center justify-center">
            {children.length ? (
              <button onClick={() => toggle(node.id)} className="w-5 h-5 flex items-center justify-center bg-white border-2 border-pop-black hover:bg-pop-yellow" title={isExpanded ? '收起' : '展开'}>
                <svg className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6"/></svg>
              </button>
            ) : (
              <span className="w-5 h-5 flex items-center justify-center text-pop-black/20">
                <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/></svg>
              </span>
            )}
          </div>

          {editing ? (
            <div className="flex-1 flex items-center gap-1">
              <input autoFocus className="input-pop px-2 py-1 text-sm flex-1" value={editTitle} onChange={e => setEditTitle(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') submitEdit(); if (e.key === 'Escape') setEditingId(null) }} />
              <button className="btn-pop-green text-[10px] px-2 py-1" onClick={submitEdit}>保存</button>
              <button className="btn-ghost-pop text-[10px] px-2 py-1" onClick={() => setEditingId(null)}>取消</button>
            </div>
          ) : (
            <div className={`flex-1 flex items-center gap-2 flex-wrap bg-white border-2 border-pop-black px-2 py-1 shadow-pop-sm ${node.status === 'abandoned' ? 'opacity-50' : ''}`}>
              <span className={`font-display text-sm uppercase tracking-wide text-pop-black ${node.status === 'done' ? 'line-through decoration-2' : ''}`}>{node.title}</span>
              <span className={`w-2.5 h-2.5 border-2 border-pop-black ${node.status === 'done' ? 'bg-pop-green' : node.status === 'onhold' ? 'bg-pop-orange' : node.status === 'abandoned' ? 'bg-pop-red' : 'bg-pop-yellow'}`} title={STATUS_LABELS[node.status]} />
              <span className="ml-auto flex items-center gap-1">
                {node.status !== 'done' && node.status !== 'abandoned' && (
                  <button onClick={() => onAction(node.id, 'done')} disabled={!children.every(c => c.status === 'done') || children.length === 0 && false} className={`text-[10px] font-display uppercase border-2 border-pop-black px-1.5 py-0.5 hover:shadow-pop-sm ${children.length && !children.every(c=>c.status==='done') ? 'opacity-30 cursor-not-allowed' : 'bg-pop-green text-white'}`} title="标记完成">完成</button>
                )}
                {node.status === 'active' && (
                  <>
                    <button onClick={() => onAction(node.id, 'onhold')} className="text-[10px] font-display uppercase bg-pop-orange text-white border-2 border-pop-black px-1.5 py-0.5 hover:shadow-pop-sm">搁置</button>
                    <button onClick={() => onAction(node.id, 'abandon')} className="text-[10px] font-display uppercase bg-pop-red text-white border-2 border-pop-black px-1.5 py-0.5 hover:shadow-pop-sm">放弃</button>
                  </>
                )}
                {(node.status === 'done' || node.status === 'onhold' || node.status === 'abandoned') && (
                  <button onClick={() => onAction(node.id, 'resume')} className="text-[10px] font-display uppercase bg-pop-yellow text-pop-black border-2 border-pop-black px-1.5 py-0.5 hover:shadow-pop-sm">恢复</button>
                )}
                <button onClick={() => startAdd(node.id)} className="text-[10px] font-display uppercase bg-pop-blue text-white border-2 border-pop-black px-1.5 py-0.5 hover:shadow-pop-sm">+分支</button>
                <button onClick={() => startEdit(node)} className="text-[10px] font-display uppercase bg-pop-black text-white border-2 border-pop-black px-1.5 py-0.5 hover:opacity-80">改</button>
                <button onClick={() => { if (confirm('删除该分支及其全部子项？')) onDelete(node.id) }} className="text-[10px] font-display uppercase bg-white text-pop-black border-2 border-pop-black px-1.5 py-0.5 hover:bg-pop-red hover:text-white">✕</button>
              </span>
            </div>
          )}
        </div>

        {/* 新增子节点输入 */}
        {addingParent === node.id && (
          <div className="flex items-center gap-1 ml-[25px] mb-1 mt-0.5" style={{ paddingLeft: `${depth * 20}px` }}>
            <input autoFocus className="input-pop px-2 py-1 text-sm flex-1" placeholder="新分支名称…" value={newTitle} onChange={e => setNewTitle(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') submitAdd(); if (e.key === 'Escape') setAddingParent(null) }} />
            <button className="btn-pop-green text-[10px] px-2 py-1" onClick={submitAdd}>添加</button>
            <button className="btn-ghost-pop text-[10px] px-2 py-1" onClick={() => setAddingParent(null)}>取消</button>
          </div>
        )}

        {children.length > 0 && isExpanded && (
          <div className="ml-2 border-l-2 border-dashed border-pop-black/30 pl-1">
            {children.map(c => renderNode(c, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      {roots.length === 0 ? (
        <p className="text-sm text-pop-black/60 font-sans">还没有分支，点击某个节点「+分支」开始分叉。</p>
      ) : (
        roots.map(r => renderNode(r, 0))
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 单个计划详情（树 + 时间线）
// ---------------------------------------------------------------------------
function PlansDetail({ plan, nodes, logs, onBack, onNodeAction, onAddChild, onDeleteNode, onRenameNode, onAddLog, onEditPlan }) {
  const [logContent, setLogContent] = useState('')
  const [editMode, setEditMode] = useState(false)
  const [form, setForm] = useState({ title: plan.title, goal: plan.goal || '', domain: plan.domain || '', priority: plan.priority || '中' })
  const root = nodes.find(n => n.parentId === null)

  const saveLog = async () => {
    if (!logContent.trim()) return
    await onAddLog({ content: logContent.trim(), nodeId: root ? root.id : null })
    setLogContent('')
  }

  const savePlan = async () => {
    if (!form.title.trim()) return
    await onEditPlan(form)
    setEditMode(false)
  }

  return (
    <div className="animate-pop-in">
      {/* 返回 + 标题 */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <button onClick={onBack} className="btn-ghost-pop text-sm">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7"/></svg>
          全部计划
        </button>
        <StatusBadge status={plan.status} />
        {plan.domain && <span className="tag-pop bg-pop-pink text-white border-pop-black">{plan.domain}</span>}
        <button onClick={() => setEditMode(!editMode)} className="btn-ghost-pop text-sm ml-auto">✎ 编辑计划</button>
      </div>

      {editMode ? (
        <div className="pop-card p-4 mb-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <input className="input-pop px-3 py-2 text-sm sm:col-span-3" placeholder="标题" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
            <input className="input-pop px-3 py-2 text-sm sm:col-span-3" placeholder="目标" value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })} />
            <input className="input-pop px-3 py-2 text-sm" placeholder="领域" value={form.domain} onChange={e => setForm({ ...form, domain: e.target.value })} />
            <select className="input-pop px-3 py-2 text-sm" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
              <option value="高">高</option><option value="中">中</option><option value="低">低</option>
            </select>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="btn-pop-green text-sm px-4 py-1.5" onClick={savePlan}>保存</button>
            <button className="btn-ghost-pop text-sm" onClick={() => setEditMode(false)}>取消</button>
          </div>
        </div>
      ) : (
        <h2 className="font-display text-3xl text-pop-black uppercase tracking-wide mb-1 leading-tight break-words">{plan.title}</h2>
      )}
      {!editMode && plan.goal && <p className="text-sm font-sans text-pop-black/70 mb-4">{plan.goal}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左：计划树 */}
        <div className="pop-panel p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-display text-lg text-pop-black uppercase tracking-wide flex items-center gap-2">
              <span className="w-3 h-3 bg-pop-green border-2 border-pop-black" /> 分支树
            </h3>
            <button onClick={() => { const r = nodes.find(n => n.parentId === null); if (r) onAddChild(r.id) }} className="btn-pop-blue text-xs px-3 py-1">
              + 根下分支
            </button>
          </div>
          <EditableTree
            nodes={nodes}
            planId={plan.id}
            onAction={(nodeId, action) => onNodeAction(nodeId, action)}
            onAddChild={(parentId, title) => onAddChild(parentId, title)}
            onDelete={(nodeId) => onDeleteNode(nodeId)}
            onRename={(nodeId, title) => onRenameNode(nodeId, title)}
          />
        </div>

        {/* 右：进展流时间线 */}
        <div className="pop-panel p-4 flex flex-col">
          <h3 className="font-display text-lg text-pop-black uppercase tracking-wide mb-3 flex items-center gap-2">
            <span className="w-3 h-3 bg-pop-yellow border-2 border-pop-black" /> 进展流
          </h3>

          {/* 新增进展 */}
          <div className="flex gap-2 mb-3">
            <input
              className="input-pop px-2 py-1.5 text-sm flex-1"
              placeholder="记录一条进展 / 想法 / 下一步…"
              value={logContent}
              onChange={e => setLogContent(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') saveLog() }}
            />
            <button className="btn-pop-green text-xs px-3 py-1.5" onClick={saveLog} disabled={!logContent.trim()}>记录</button>
          </div>

          {/* 时间线 */}
          <div className="flex-1 overflow-y-auto max-h-[480px] pr-1">
            {logs.length === 0 ? (
              <p className="text-sm text-pop-black/60 font-sans">还没有进展记录。创建分支、完成任务、或在上方记一条吧。</p>
            ) : (
              <div className="relative border-l-3 border-pop-black ml-1 pl-4 space-y-3">
                {[...logs].reverse().map(log => (
                  <div key={log.id} className="relative">
                    <span className="absolute -left-[21px] top-1 w-3 h-3 bg-white border-2 border-pop-black" />
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="tag-pop text-[10px] py-0 px-1.5" style={{ background: LOG_COLORS[log.action] || '#ffd60a', color: '#fff' }}>{LOG_LABELS[log.action] || log.action}</span>
                        <span className="text-[10px] font-mono text-pop-black/50">{fmtTime(log.createdAt)}</span>
                      </div>
                      <p className="text-sm font-sans text-pop-black mt-0.5">{log.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const LOG_COLORS = {
  create: '#00d97e',
  add: '#2d7dff',
  complete: '#2d7dff',
  onhold: '#ff8c1a',
  resume: '#00d97e',
  abandon: '#ff2e3b',
  note: '#ffd60a',
}

function fmtTime(ms) {
  if (!ms) return ''
  const d = new Date(ms)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ---------------------------------------------------------------------------
// 主视图：列表 ↔ 详情 切换
// ---------------------------------------------------------------------------
export default function PlansView() {
  const {
    plans, current, loaded,
    refreshList, refreshDetail, setCurrent,
    createPlan, updatePlan, deletePlan,
    addNode, nodeAction, updateNode, deleteNode, addLog,
  } = usePlans()

  const [showNew, setShowNew] = useState(false)

  const openPlan = useCallback((planId) => {
    refreshDetail(planId)
  }, [refreshDetail])

  const closePlan = useCallback(() => {
    setCurrent(null)
    refreshList()
  }, [setCurrent, refreshList])

  const handleCreate = useCallback(async (data) => {
    const p = await createPlan(data)
    setShowNew(false)
    reopenIfNeeded(p.id)
  }, [createPlan])

  // 打开详情所需的动作，都代理到 hook
  const handleNodeAction = useCallback((nodeId, action) => {
    if (!current) return
    return nodeAction(current.plan.id, nodeId, action)
  }, [current, nodeAction])

  const handleAddChild = useCallback((parentId, title) => {
    if (!current) return
    return addNode(current.plan.id, { title, parentId })
  }, [current, addNode])

  const handleDeleteNode = useCallback((nodeId) => {
    if (!current) return
    return deleteNode(current.plan.id, nodeId)
  }, [current, deleteNode])

  const handleRenameNode = useCallback((nodeId, title) => {
    if (!current) return
    return updateNode(current.plan.id, nodeId, title)
  }, [current, updateNode])

  const handleAddLog = useCallback(({ content, nodeId }) => {
    if (!current) return
    return addLog(current.plan.id, { content, nodeId })
  }, [current, addLog])

  const handleEditPlan = useCallback((data) => {
    if (!current) return
    return updatePlan(current.plan.id, data)
  }, [current, updatePlan])

  const reopenIfNeeded = useCallback((planId) => {
    const p = plans.find(x => x.id === planId)
    if (p) refreshDetail(planId)
  }, [plans, refreshDetail])

  if (!loaded) {
    return <div className="text-center py-16 font-display text-pop-black text-xl uppercase">加载中…</div>
  }

  // 详情模式
  if (current) {
    return (
      <PlansDetail
        plan={current.plan}
        nodes={current.nodes}
        logs={current.logs}
        onBack={closePlan}
        onNodeAction={handleNodeAction}
        onAddChild={handleAddChild}
        onDeleteNode={handleDeleteNode}
        onRenameNode={handleRenameNode}
        onAddLog={handleAddLog}
        onEditPlan={handleEditPlan}
      />
    )
  }

  // 列表模式
  return (
    <div className="animate-slide-up">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h2 className="font-display text-2xl text-pop-black uppercase tracking-wide text-balance">行动计划</h2>
          <p className="text-xs font-mono text-pop-black/60 mt-0.5">每做一步记一条进展，树会自己生长、状态自动推进。</p>
        </div>
        <button onClick={() => setShowNew(!showNew)} className="btn-pop-red text-sm px-4 py-2">
          {showNew ? '收起' : '+ 新建计划'}
        </button>
      </div>

      {showNew && (
        <NewPlanForm onCreate={handleCreate} onCancel={() => setShowNew(false)} />
      )}

      {plans.length === 0 ? (
        <div className="pop-card p-8 text-center">
          <div className="font-display text-2xl text-pop-black uppercase mb-2">还没有行动计划</div>
          <p className="text-sm font-sans text-pop-black/60 mb-4">点击右上角「+ 新建计划」，建立一个属于你的行动树（漫剧 / 博客 / 网络安全…）。</p>
          <button onClick={() => setShowNew(true)} className="btn-pop-green text-sm px-4 py-2">开始第一个计划</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {plans.map(p => (
            <PlanCard key={p.id} plan={p} onOpen={openPlan} onDelete={(id) => { if (confirm('删除该计划及其全部分支、记录？')) deletePlan(id) }} />
          ))}
        </div>
      )}
    </div>
  )
}
