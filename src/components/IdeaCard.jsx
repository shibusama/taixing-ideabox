import { useState, useRef, useEffect } from 'react'
import { getTagColor } from '../data/tags'
import { formatRelativeTime, formatFullDate, highlightMatch, stripTags } from '../utils/helpers'

export default function IdeaCard({ idea, onEdit, onDelete, onTogglePin, searchQuery }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState(idea.content)
  const [showActions, setShowActions] = useState(false)
  const editRef = useRef(null)

  useEffect(() => {
    if (isEditing && editRef.current) {
      editRef.current.style.height = 'auto'
      editRef.current.style.height = editRef.current.scrollHeight + 'px'
      editRef.current.focus()
      editRef.current.setSelectionRange(editContent.length, editContent.length)
    }
  }, [isEditing])

  const handleSave = () => {
    const trimmed = editContent.trim()
    if (trimmed && trimmed !== idea.content) {
      onEdit(idea.id, { content: trimmed })
    }
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditContent(idea.content)
    setIsEditing(false)
  }

  const displayContent = stripTags(idea.content)
  const highlightedContent = searchQuery
    ? highlightMatch(displayContent, searchQuery)
    : displayContent

  // Rotate cards slightly for that comic feel
  const rotation = (idea.id.charCodeAt(0) % 2 === 0) ? '0.3deg' : '-0.3deg'

  return (
    <div
      className={`pop-card rounded-none p-4 sm:p-5 group relative animate-pop-in
        ${idea.pinned ? 'bg-pop-yellow' : 'bg-white'}`}
      style={{ transform: `rotate(${rotation})` }}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Pin badge - comic star */}
      {idea.pinned && (
        <div className="absolute -top-3 -right-3 z-10 animate-bounce-in">
          <div
            className="w-10 h-10 flex items-center justify-center bg-pop-red border-3 border-pop-black shadow-pop-sm"
            style={{ clipPath: 'polygon(50% 0%, 61% 18%, 80% 10%, 73% 29%, 95% 25%, 82% 41%, 100% 50%, 82% 59%, 95% 75%, 73% 71%, 80% 90%, 61% 82%, 50% 100%, 39% 82%, 20% 90%, 27% 71%, 5% 75%, 18% 59%, 0% 50%, 18% 41%, 5% 25%, 27% 29%, 20% 10%, 39% 18%)' }}
          >
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M16 3l5 5-3 1-3 3-1 5-3-3-5 5v-5l-3-3 5-1 3-3 1-3z" />
            </svg>
          </div>
        </div>
      )}

      {/* Content */}
      {isEditing ? (
        <div className="animate-scale-in">
          <textarea
            ref={editRef}
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleSave()
              if (e.key === 'Escape') handleCancel()
            }}
            className="w-full bg-cream text-pop-black rounded-none p-3
                       resize-none border-3 border-pop-black outline-none
                       focus:shadow-pop text-base leading-relaxed font-sans"
            rows={3}
          />
          <div className="flex items-center gap-2 mt-2">
            <button onClick={handleSave} className="btn-pop-green text-xs px-3 py-1">
              保存!
            </button>
            <button onClick={handleCancel} className="btn-ghost-pop text-xs">
              取消
            </button>
            <span className="text-[10px] text-gray-500 ml-auto font-mono font-bold">⌘↵ 保存 · ESC 取消</span>
          </div>
        </div>
      ) : (
        <p
          className="text-pop-black leading-relaxed whitespace-pre-wrap break-words text-[15px] sm:text-base font-sans overflow-hidden"
          dangerouslySetInnerHTML={{ __html: highlightedContent }}
        />
      )}

      {/* Tags */}
      {idea.tags.length > 0 && !isEditing && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {idea.tags.map(tag => {
            const color = getTagColor(tag)
            return (
              <span key={tag} className={`tag-pop ${color.solid} cursor-default`}>
                #{tag}
              </span>
            )
          })}
        </div>
      )}

      {/* Footer */}
      {!isEditing && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t-2 border-pop-black/10">
          <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-gray-600">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <time title={formatFullDate(idea.createdAt)} className="whitespace-nowrap">
              {formatRelativeTime(idea.createdAt)}
            </time>
          </div>

          <div className={`flex items-center gap-1 transition-opacity duration-150 ${
            showActions ? 'opacity-100' : 'opacity-0 sm:opacity-0'
          }`}>
            <button
              onClick={() => onTogglePin(idea.id)}
              className={`p-1.5 border-2 border-pop-black transition-all hover:shadow-pop-sm
                ${idea.pinned ? 'bg-pop-red text-white' : 'bg-white text-pop-black hover:bg-pop-yellow'}`}
              aria-label={idea.pinned ? '取消置顶' : '置顶'}
              title={idea.pinned ? '取消置顶' : '置顶'}
            >
              <svg className="w-4 h-4" fill={idea.pinned ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16 3l5 5-3 1-3 3-1 5-3-3-5 5v-5l-3-3 5-1 3-3 1-3z" />
              </svg>
            </button>
            <button
              onClick={() => setIsEditing(true)}
              className="p-1.5 border-2 border-pop-black bg-white text-pop-black transition-all hover:bg-pop-blue hover:text-white hover:shadow-pop-sm"
              aria-label="编辑"
              title="编辑"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              onClick={() => onDelete(idea.id)}
              className="p-1.5 border-2 border-pop-black bg-white text-pop-black transition-all hover:bg-pop-red hover:text-white hover:shadow-pop-sm"
              aria-label="删除"
              title="删除"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
