export default function Header({ onToggleSidebar, sidebarOpen }) {
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
