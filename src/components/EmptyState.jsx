export default function EmptyState({ hasIdeas, searchQuery, selectedTag, onClearFilters }) {
  // Search/filter no results
  if (hasIdeas && (searchQuery || selectedTag)) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center animate-pop-in">
        <div className="relative mb-6">
          <div
            className="w-20 h-20 flex items-center justify-center bg-pop-pink border-4 border-pop-black shadow-pop-lg"
            style={{ clipPath: 'polygon(50% 0%, 61% 18%, 80% 10%, 73% 29%, 95% 25%, 82% 41%, 100% 50%, 82% 59%, 95% 75%, 73% 71%, 80% 90%, 61% 82%, 50% 100%, 39% 82%, 20% 90%, 27% 71%, 5% 75%, 18% 59%, 0% 50%, 18% 41%, 5% 25%, 27% 29%, 20% 10%, 39% 18%)' }}
          >
            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        <h3 className="font-display text-3xl text-pop-black tracking-wide uppercase mb-2">没找到!</h3>
        <p className="text-sm text-gray-600 mb-6 font-sans max-w-xs">
          {searchQuery && !selectedTag && `搜索 "${searchQuery}" 没有结果`}
          {selectedTag && !searchQuery && `标签 "${selectedTag}" 下暂无内容`}
          {searchQuery && selectedTag && `在 "${selectedTag}" 下搜索 "${searchQuery}" 没有结果`}
        </p>
        <button onClick={onClearFilters} className="btn-pop-yellow text-sm">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          清除筛选
        </button>
      </div>
    )
  }

  // First time - no ideas at all
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center animate-pop-in">
      <div className="relative mb-8">
        {/* Star burst background */}
        <div
          className="w-24 h-24 flex items-center justify-center bg-pop-yellow border-4 border-pop-black shadow-pop-lg"
          style={{ clipPath: 'polygon(50% 0%, 61% 18%, 80% 10%, 73% 29%, 95% 25%, 82% 41%, 100% 50%, 82% 59%, 95% 75%, 73% 71%, 80% 90%, 61% 82%, 50% 100%, 39% 82%, 20% 90%, 27% 71%, 5% 75%, 18% 59%, 0% 50%, 18% 41%, 5% 25%, 27% 29%, 20% 10%, 39% 18%)' }}
        >
          <svg className="w-12 h-12 text-pop-red" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L14.5 8.5L21 9.5L16 14.5L17.5 21L12 17.5L6.5 21L8 14.5L3 9.5L9.5 8.5L12 2Z" />
          </svg>
        </div>
      </div>
      <h3 className="font-display text-4xl text-pop-black tracking-wide uppercase mb-2">空的!</h3>
      <p className="text-sm text-gray-600 max-w-xs font-sans mb-8">
        在上方输入框写下你的第一个想法<br/>每一个闪念都值得被记录
      </p>
      <div className="flex flex-wrap justify-center gap-2 max-w-md">
        {[
          { text: '用 #标签 快速分类', bg: 'bg-pop-red', dark: false },
          { text: '⌘+Enter 快速提交', bg: 'bg-pop-blue', dark: false },
          { text: '支持编辑和置顶', bg: 'bg-pop-green', dark: false },
        ].map((tip, i) => (
          <span
            key={i}
            className={`text-xs font-bold font-sans uppercase ${tip.bg} ${tip.dark ? 'text-pop-black' : 'text-white'} border-2 border-pop-black px-3 py-1.5 shadow-pop-sm`}
            style={{ transform: `rotate(${i % 2 === 0 ? -2 : 2}deg)` }}
          >
            {tip.text}
          </span>
        ))}
      </div>
    </div>
  )
}
