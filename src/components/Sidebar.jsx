import { getTagColor } from '../data/tags'

export default function Sidebar({ stats, allTags, selectedTag, onSelectTag, onExport, onImport, onPurgeArchived, archivedCount }) {
  return (
    <aside className="space-y-5">
      {/* Stats card */}
      <div className="pop-panel p-5 shadow-pop">
        <h3 className="font-display text-lg text-pop-black tracking-wide uppercase mb-4 flex items-center gap-2 border-b-2 border-pop-black pb-2">
          <span className="inline-block w-4 h-4 bg-pop-red border-2 border-pop-black" />
          数据概览
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <StatTile label="总数" value={stats.total} bg="bg-pop-red" />
          <StatTile label="今日" value={stats.today} bg="bg-pop-green" />
          <StatTile label="本周" value={stats.thisWeek} bg="bg-pop-blue" />
          <StatTile label="置顶" value={stats.pinned} bg="bg-pop-yellow" textDark />
        </div>
      </div>

      {/* Tag cloud */}
      <div className="pop-panel p-5 shadow-pop">
        <h3 className="font-display text-lg text-pop-black tracking-wide uppercase mb-4 flex items-center gap-2 border-b-2 border-pop-black pb-2">
          <span className="inline-block w-4 h-4 bg-pop-blue border-2 border-pop-black" />
          标签
          {selectedTag && (
            <button
              onClick={() => onSelectTag(null)}
              className="ml-auto btn-ghost-pop text-[10px] px-2 py-0.5"
            >
              清除
            </button>
          )}
        </h3>

        {allTags.length === 0 ? (
          <p className="text-sm text-gray-500 py-2 font-sans">还没有标签，在灵感中用 # 添加吧</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {allTags.map(({ name, count }) => {
              const color = getTagColor(name)
              const isActive = selectedTag === name
              return (
                <button
                  key={name}
                  onClick={() => onSelectTag(isActive ? null : name)}
                  className={`tag-pop ${color.solid} ${
                    isActive ? 'shadow-pop-sm' : 'opacity-80 hover:opacity-100'
                  }`}
                >
                  #{name}
                  <span className="text-[10px] opacity-70 ml-0.5">{count}</span>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Data management */}
      <div className="pop-panel p-5 shadow-pop">
        <h3 className="font-display text-lg text-pop-black tracking-wide uppercase mb-4 flex items-center gap-2 border-b-2 border-pop-black pb-2">
          <span className="inline-block w-4 h-4 bg-pop-green border-2 border-pop-black" />
          数据
        </h3>
        <div className="space-y-2">
          <button
            onClick={onExport}
            className="w-full btn-ghost-pop text-sm justify-start"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            导出数据
          </button>

          <label className="w-full btn-ghost-pop text-sm justify-start cursor-pointer">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            导入数据
            <input
              type="file"
              accept=".json"
              className="hidden"
              onChange={onImport}
            />
          </label>

          {archivedCount > 0 && (
            <button
              onClick={onPurgeArchived}
              className="w-full btn-ghost-pop text-sm justify-start hover:bg-pop-red hover:text-white"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              清空回收站 ({archivedCount})
            </button>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center">
        <p className="text-xs font-mono font-bold text-pop-black/50">
          灵感匣 · LOCAL STORAGE
        </p>
      </div>
    </aside>
  )
}

function StatTile({ label, value, bg, textDark }) {
  return (
    <div className={`${bg} border-3 border-pop-black p-3 shadow-pop-sm`}>
      <div className={`text-2xl font-display tracking-wide ${textDark ? 'text-pop-black' : 'text-white'}`}>
        {value}
      </div>
      <div className={`text-xs font-bold font-sans uppercase tracking-wide mt-0.5 ${textDark ? 'text-pop-black/70' : 'text-white/80'}`}>
        {label}
      </div>
    </div>
  )
}
