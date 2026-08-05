import { useEffect, useRef } from 'react'

export default function SearchBar({ value, onChange, onClear, resultCount }) {
  const inputRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="relative">
      {/* Search icon */}
      <div className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
        <svg className={`w-4 h-4 transition-colors ${value ? 'text-pop-red' : 'text-gray-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>

      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="搜索灵感…"
        aria-label="搜索灵感"
        className="w-full input-pop pl-10 pr-20 py-2.5 text-sm font-sans font-medium"
      />

      {/* Right side */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
        {value ? (
          <>
            {resultCount !== undefined && (
              <span className="text-xs font-mono font-bold text-pop-black bg-pop-yellow border-2 border-pop-black px-1.5">
                {resultCount}
              </span>
            )}
            <button
              onClick={onClear}
              className="text-pop-black hover:text-pop-red transition-colors p-0.5"
              aria-label="清除搜索"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </>
        ) : (
          <kbd className="hidden sm:inline text-[10px] text-pop-black font-mono font-bold border-2 border-pop-black bg-white px-1.5 py-0.5">
            /
          </kbd>
        )}
      </div>
    </div>
  )
}
