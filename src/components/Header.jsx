export default function Header({ onToggleSidebar, sidebarOpen, view, onViewChange }) {
  return (
    <header className="sticky top-0 z-30 bg-pop-yellow border-b-4 border-pop-black">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo + Title */}
          <div className="flex items-center gap-3">
            <button
              onClick={onToggleSidebar}
              className="lg:hidden p-2 -ml-2 bg-white border-3 border-pop-black shadow-pop-sm hover:bg-pop-red hover:text-white transition-colors"
              aria-label="切换侧边栏"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <div className="flex items-center gap-3">
              {/* Logo - star burst */}
              <div className="relative">
                <div
                  className="w-11 h-11 flex items-center justify-center"
                  style={{
                    background: '#ff2e3b',
                    clipPath: 'polygon(50% 0%, 61% 18%, 80% 10%, 73% 29%, 95% 25%, 82% 41%, 100% 50%, 82% 59%, 95% 75%, 73% 71%, 80% 90%, 61% 82%, 50% 100%, 39% 82%, 20% 90%, 27% 71%, 5% 75%, 18% 59%, 0% 50%, 18% 41%, 5% 25%, 27% 29%, 20% 10%, 39% 18%)',
                  }}
                >
                  <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L14.5 8.5L21 9.5L16 14.5L17.5 21L12 17.5L6.5 21L8 14.5L3 9.5L9.5 8.5L12 2Z" />
                  </svg>
                </div>
              </div>
              <div>
                <h1 className="text-display text-2xl text-pop-black leading-none">
                  灵感匣
                </h1>
                <p className="text-[10px] text-pop-black/60 leading-none mt-1 font-mono font-bold tracking-widest">
                  IDEA BOX
                </p>
              </div>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            {/* View toggle */}
            <div className="flex items-center border-2 border-pop-black shadow-pop-sm bg-white">
              <button
                onClick={() => onViewChange('list')}
                className={`p-2 transition-colors ${view === 'list' ? 'bg-pop-blue text-white' : 'bg-white text-pop-black hover:bg-pop-yellow'}`}
                aria-label="列表视图"
                title="列表视图"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01" />
                </svg>
              </button>
              <button
                onClick={() => onViewChange('board')}
                className={`p-2 transition-colors ${view === 'board' ? 'bg-pop-blue text-white' : 'bg-white text-pop-black hover:bg-pop-yellow'}`}
                aria-label="看板视图"
                title="看板视图"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h6a1 1 0 011 1v16a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM13 4a1 1 0 011-1h6a1 1 0 011 1v10a1 1 0 01-1 1h-6a1 1 0 01-1-1V4z" />
                </svg>
              </button>
              <button
                onClick={() => onViewChange('video')}
                className={`p-2 transition-colors ${view === 'video' ? 'bg-pop-blue text-white' : 'bg-white text-pop-black hover:bg-pop-yellow'}`}
                aria-label="视频导图"
                title="视频导图"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 text-xs font-bold font-mono bg-white border-2 border-pop-black px-2.5 py-1 shadow-pop-sm">
              <span className="w-2 h-2 bg-pop-green border border-pop-black" />
              <span>SAVED LOCALLY</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
