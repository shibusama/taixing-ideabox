import { useMemo, useState } from 'react'
import IdeaCard from './IdeaCard'
import { getTagColor } from '../data/tags'

export default function BoardView({
  ideas,
  onEdit,
  onDelete,
  onTogglePin,
  onAddTag,
  onClearTags,
  searchQuery,
}) {
  const [expandedTags, setExpandedTags] = useState(new Set())
  const [draggingId, setDraggingId] = useState(null)
  const [dragOverKey, setDragOverKey] = useState(null)

  // Build columns: one per tag found in ideas + an "untagged" column at the end
  const columns = useMemo(() => {
    const tagSet = new Set()
    const untagged = []
    for (const idea of ideas) {
      if (idea.tags.length === 0) {
        untagged.push(idea)
      } else {
        idea.tags.forEach(t => tagSet.add(t))
      }
    }

    const tagColumns = [...tagSet].map(tag => ({
      key: `tag:${tag}`,
      title: tag,
      tag,
      ideas: ideas.filter(i => i.tags.includes(tag)),
    }))

    const untaggedColumn = untagged.length
      ? [{ key: 'untagged', title: '未标签', tag: null, ideas: untagged }]
      : []

    return [...tagColumns, ...untaggedColumn]
  }, [ideas])

  if (ideas.length === 0) return null

  const toggleTag = (key) => {
    setExpandedTags(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const isInteractiveTarget = (e) => e.target.closest('button, textarea, input, a')

  const handleDragStart = (e, idea) => {
    if (isInteractiveTarget(e)) {
      e.preventDefault()
      return
    }
    setDraggingId(idea.id)
    e.dataTransfer.setData('text/plain', idea.id)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDrop = (e, column) => {
    e.preventDefault()
    const id = e.dataTransfer.getData('text/plain')
    if (id) {
      if (column.tag) {
        onAddTag(id, column.tag)
      } else {
        onClearTags(id)
      }
    }
    setDragOverKey(null)
    setDraggingId(null)
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {columns.map(column => {
        const color = column.tag ? getTagColor(column.tag) : null
        const isOver = dragOverKey === column.key
        const isExpanded = expandedTags.has(column.key)

        return (
          <div
            key={column.key}
            className={`bg-white border-3 border-pop-black shadow-pop transition-all duration-150
              ${isExpanded ? '' : 'h-44'}
              ${isOver ? 'shadow-pop-xl -translate-y-1' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              e.dataTransfer.dropEffect = 'move'
              if (dragOverKey !== column.key) setDragOverKey(column.key)
            }}
            onDragLeave={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget)) {
                setDragOverKey(prev => (prev === column.key ? null : prev))
              }
            }}
            onDrop={(e) => handleDrop(e, column)}
          >
            {/* Tag header — click to toggle */}
            <div
              className={`flex items-center gap-2 px-3 py-3 border-b-3 border-pop-black cursor-pointer select-none
                ${isOver ? 'halftone-yellow' : ''}
                ${isExpanded ? '' : 'hover:bg-pop-black/5'}`}
              onClick={() => toggleTag(column.key)}
            >
              <span
                className={`w-4 h-4 border-2 border-pop-black flex-shrink-0 ${color ? color.solid : 'bg-gray-300'}`}
              />
              <span className="font-display text-lg uppercase tracking-wide text-pop-black flex-1 truncate leading-none">
                {column.tag ? `#${column.tag}` : '未标签'}
              </span>
              <span className="text-xs font-mono font-bold bg-pop-black text-white px-1.5 py-0.5 leading-none">
                {column.ideas.length}
              </span>
              <span className="text-xs font-mono text-pop-black/50 ml-1">
                {isExpanded ? '▼' : '▶'}
              </span>
            </div>

            {/* Collapsed: show badges */}
            {!isExpanded && (
              <div className="p-3">
                <div className="flex flex-wrap gap-1.5">
                  {column.ideas.slice(0, 15).map(idea => {
                    // Show a tiny snippet of each idea
                    const snippet = idea.content.replace(/^#\w+\s*/, '').slice(0, 20)
                    return (
                      <span
                        key={idea.id}
                        className={`inline-block text-xs font-mono px-2 py-1 border border-pop-black/30 ${
                          color ? color.bg : 'bg-gray-100'
                        }`}
                      >
                        {snippet}{idea.content.length > 20 ? '…' : ''}
                      </span>
                    )
                  })}
                  {column.ideas.length > 15 && (
                    <span className="text-xs font-mono text-pop-black/40 px-1">
                      +{column.ideas.length - 15}
                    </span>
                  )}
                  {column.ideas.length === 0 && (
                    <div className="text-center text-xs font-mono font-bold text-pop-black/30 uppercase tracking-widest py-3 w-full border-2 border-dashed border-pop-black/20">
                      拖到这里
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Expanded: full idea cards */}
            {isExpanded && (
              <div className="p-3 space-y-3 max-h-96 overflow-y-auto">
                {column.ideas.map(idea => (
                  <div
                    key={idea.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, idea)}
                    onDragEnd={() => {
                      setDraggingId(null)
                      setDragOverKey(null)
                    }}
                    className={`cursor-grab active:cursor-grabbing transition-opacity duration-150
                      ${draggingId === idea.id ? 'opacity-40' : ''}`}
                  >
                    <IdeaCard
                      idea={idea}
                      onEdit={onEdit}
                      onDelete={onDelete}
                      onTogglePin={onTogglePin}
                      searchQuery={searchQuery}
                    />
                  </div>
                ))}
                {column.ideas.length === 0 && (
                  <div className="text-center text-xs font-mono font-bold text-pop-black/30 uppercase tracking-widest py-6 border-2 border-dashed border-pop-black/20">
                    拖到这里
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}