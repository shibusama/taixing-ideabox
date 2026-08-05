import { useState, useRef, useEffect, useCallback } from 'react'
import { getTagColor, SUGGESTED_TAGS } from '../data/tags'
import { extractTags } from '../utils/helpers'

export default function IdeaInput({ onAdd }) {
  const [content, setContent] = useState('')
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [showTagInput, setShowTagInput] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef(null)
  const tagInputRef = useRef(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 240) + 'px'
    }
  }, [content])

  useEffect(() => {
    if (showTagInput && tagInputRef.current) {
      tagInputRef.current.focus()
    }
  }, [showTagInput])

  const handleSubmit = useCallback(() => {
    const trimmed = content.trim()
    if (!trimmed) return

    const inlineTags = extractTags(trimmed)
    const allTags = [...new Set([...tags, ...inlineTags])]

    onAdd(trimmed, allTags)
    setContent('')
    setTags([])
    setTagInput('')
    setShowTagInput(false)
  }, [content, tags, onAdd])

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
    if (e.key === 'Escape') {
      textareaRef.current?.blur()
    }
  }

  const handleTagKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const value = tagInput.trim()
      if (value && !tags.includes(value)) {
        setTags(prev => [...prev, value])
      }
      setTagInput('')
    }
    if (e.key === 'Backspace' && !tagInput && tags.length > 0) {
      setTags(prev => prev.slice(0, -1))
    }
    if (e.key === 'Escape') {
      setShowTagInput(false)
    }
  }

  const addSuggestedTag = (tag) => {
    if (!tags.includes(tag)) {
      setTags(prev => [...prev, tag])
    }
  }

  const removeTag = (tag) => {
    setTags(prev => prev.filter(t => t !== tag))
  }

  const charCount = content.length
  const maxLength = 2000

  return (
    <div className={`relative transition-all duration-150 ${isFocused ? '-translate-x-0.5 -translate-y-0.5' : ''}`}>
      <div className="relative pop-card rounded-none p-4 sm:p-5" style={isFocused ? { boxShadow: '8px 8px 0 0 #0a0a0a' } : {}}>
        {/* Comic "NEW!" badge */}
        {isFocused && (
          <div className="absolute -top-4 -right-3 z-10 animate-bounce-in">
            <div
              className="w-14 h-14 flex items-center justify-center bg-pop-pink border-3 border-pop-black"
              style={{ clipPath: 'polygon(50% 0%, 61% 18%, 80% 10%, 73% 29%, 95% 25%, 82% 41%, 100% 50%, 82% 59%, 95% 75%, 73% 71%, 80% 90%, 61% 82%, 50% 100%, 39% 82%, 20% 90%, 27% 71%, 5% 75%, 18% 59%, 0% 50%, 18% 41%, 5% 25%, 27% 29%, 20% 10%, 39% 18%)' }}
            >
              <span className="font-display text-white text-lg leading-none">NEW!</span>
            </div>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value.slice(0, maxLength))}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="灵感来了？写下你的想法…"
          rows={2}
          aria-label="灵感输入框"
          className="w-full bg-transparent text-pop-black placeholder-gray-400
                     resize-none border-none outline-none
                     text-base sm:text-lg leading-relaxed font-sans
                     min-h-[56px]"
        />

        {/* Tags display */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3 animate-slide-down">
            {tags.map(tag => {
              const color = getTagColor(tag)
              return (
                <span
                  key={tag}
                  className={`tag-pop ${color.solid}`}
                >
                  #{tag}
                  <button
                    onClick={() => removeTag(tag)}
                    className="ml-0.5 hover:scale-125 transition-transform"
                    aria-label={`移除标签 ${tag}`}
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )
            })}
          </div>
        )}

        {/* Tag input */}
        {showTagInput && (
          <div className="mt-3 flex items-center gap-2 animate-slide-down">
            <input
              ref={tagInputRef}
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              placeholder="输入标签后回车…"
              className="flex-1 input-pop px-3 py-1.5 text-sm"
              aria-label="标签输入"
            />
          </div>
        )}

        {/* Suggested tags */}
        {!showTagInput && tags.length === 0 && (
          <div className="hidden sm:flex flex-wrap gap-1.5 mt-2">
            {SUGGESTED_TAGS.slice(0, 5).map((tag, i) => {
              const color = getTagColor(tag)
              return (
                <button
                  key={tag}
                  onClick={() => addSuggestedTag(tag)}
                  className={`tag-pop ${color.solid}`}
                  style={{ transform: `rotate(${i % 2 === 0 ? -1 : 1}deg)` }}
                >
                  + {tag}
                </button>
              )
            })}
          </div>
        )}

        {/* Action bar */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t-3 border-pop-black">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowTagInput(!showTagInput)}
              className={`btn-ghost-pop text-sm ${showTagInput ? 'bg-pop-blue text-white' : ''}`}
              aria-label="添加标签"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <span className="hidden sm:inline font-bold uppercase tracking-wide">标签</span>
            </button>

            {charCount > 0 && (
              <span className={`text-xs font-mono font-bold ${charCount > maxLength * 0.8 ? 'text-pop-red' : 'text-gray-500'}`}>
                {charCount} / {maxLength}
              </span>
            )}
          </div>

          <button
            onClick={handleSubmit}
            disabled={!content.trim()}
            className="btn-pop-red text-sm"
            aria-label="保存灵感"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            <span>记录!</span>
            <kbd className="hidden sm:inline text-[10px] opacity-70 font-mono">⌘↵</kbd>
          </button>
        </div>
      </div>
    </div>
  )
}
