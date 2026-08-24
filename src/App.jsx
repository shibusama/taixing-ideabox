import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import Header from './components/Header'
import IdeaInput from './components/IdeaInput'
import IdeaList from './components/IdeaList'
import BoardView from './components/BoardView'
import VideoTools from './components/VideoTools'
import PlansView from './components/PlansView'
import Sidebar from './components/Sidebar'
import SearchBar from './components/SearchBar'
import EmptyState from './components/EmptyState'
import { useIdeas } from './hooks/useIdeas'

export default function App() {
  const {
    ideas, archived, allTags, stats,
    addIdea, updateIdea, deleteIdea, restoreIdea, togglePin,
    purgeArchived, exportData, importData,
  } = useIdeas()

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [view, setView] = useState('list')
  const [toast, setToast] = useState(null)
  const toastTimer = useRef(null)

  const showToast = useCallback((message, action) => {
    if (toastTimer.current) clearTimeout(toastTimer.current)
    setToast({ message, action })
    toastTimer.current = setTimeout(() => setToast(null), 4000)
  }, [])

  const handleDelete = useCallback((id) => {
    deleteIdea(id)
    showToast('已删除!', {
      label: '撤销',
      onClick: () => {
        restoreIdea(id)
        setToast(null)
      },
    })
  }, [deleteIdea, restoreIdea, showToast])

  const filteredIdeas = useMemo(() => {
    let result = ideas
    if (selectedTag) {
      result = result.filter(i => i.tags.includes(selectedTag))
    }
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(i =>
        i.content.toLowerCase().includes(query) ||
        i.tags.some(t => t.toLowerCase().includes(query))
      )
    }
    return [...result].sort((a, b) => {
      if (a.pinned !== b.pinned) return b.pinned ? 1 : -1
      return b.createdAt - a.createdAt
    })
  }, [ideas, searchQuery, selectedTag])

  const handleExport = useCallback(async () => {
    try {
      const data = await exportData()
      const blob = new Blob([data], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ideabox-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
      showToast('数据已导出!')
    } catch (err) {
      showToast('导出失败: ' + err.message)
    }
  }, [exportData, showToast])

  const handleImport = useCallback(async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = async (event) => {
      const success = await importData(event.target.result)
      showToast(success ? '导入成功!' : '导入失败!')
    }
    reader.readAsText(file)
    e.target.value = ''
  }, [importData, showToast])

  const clearFilters = useCallback(() => {
    setSearchQuery('')
    setSelectedTag(null)
  }, [])

  // Board view: drag card to a tag column -> add that tag
  const handleAddTag = useCallback((id, tag) => {
    const idea = ideas.find(i => i.id === id)
    if (!idea || idea.tags.includes(tag)) return
    updateIdea(id, { tags: [...idea.tags, tag] })
    showToast(`已添加标签 #${tag}`)
  }, [ideas, updateIdea, showToast])

  // Board view: drag card to untagged column -> clear all tags (with undo)
  const handleClearTags = useCallback((id) => {
    const idea = ideas.find(i => i.id === id)
    if (!idea || idea.tags.length === 0) return
    const prevTags = idea.tags
    updateIdea(id, { tags: [] })
    showToast('已移除全部标签', {
      label: '撤销',
      onClick: () => {
        updateIdea(id, { tags: prevTags })
        setToast(null)
      },
    })
  }, [ideas, updateIdea, showToast])

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') setSidebarOpen(false)
    }
    if (sidebarOpen) {
      window.addEventListener('keydown', handler)
      return () => window.removeEventListener('keydown', handler)
    }
  }, [sidebarOpen])

  const hasIdeas = ideas.length > 0
  const showEmpty = filteredIdeas.length === 0

  return (
    <div className="min-h-screen">
      <div className="relative">
        <Header
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          sidebarOpen={sidebarOpen}
          view={view}
          onViewChange={setView}
        />

        <div className={`mx-auto px-4 sm:px-6 lg:px-8 py-6 ${view === 'video' || view === 'plans' ? 'max-w-[1600px]' : 'max-w-7xl'}`}>
          <div className="flex gap-8">
            {/* Sidebar - desktop (hidden in full-width plan/video views) */}
            {view === 'plans' || view === 'video' ? (
              <main className="w-full min-w-0">
                {view === 'video' ? (
                  <VideoTools />
                ) : (
                  <PlansView />
                )}
              </main>
            ) : (
              <>
            <div className="hidden lg:block w-72 flex-shrink-0">
              <div className="sticky top-20">
                <Sidebar
                  stats={stats}
                  allTags={allTags}
                  selectedTag={selectedTag}
                  onSelectTag={setSelectedTag}
                  onExport={handleExport}
                  onImport={handleImport}
                  onPurgeArchived={() => {
                    purgeArchived()
                    showToast('回收站已清空!')
                  }}
                  archivedCount={archived.length}
                />
              </div>
            </div>

            {/* Main content */}
            <main className="flex-1 min-w-0 mx-auto lg:mx-0 max-w-3xl">
              {/* Quick capture */}
              <div className="mb-6">
                <IdeaInput onAdd={addIdea} />
              </div>

              {/* Search bar */}
              {hasIdeas && (
                <div className="mb-6">
                  <SearchBar
                    value={searchQuery}
                    onChange={setSearchQuery}
                    onClear={() => setSearchQuery('')}
                    resultCount={showEmpty ? 0 : filteredIdeas.length}
                  />
                </div>
              )}

              {/* Active filter indicator */}
              {(searchQuery || selectedTag) && !showEmpty && (
                <div className="flex items-center gap-2 mb-4 text-sm font-sans font-bold text-pop-black animate-slide-down">
                  <span className="bg-pop-black text-white px-2 py-0.5 border-2 border-pop-black text-xs uppercase tracking-wide">
                    筛选中
                  </span>
                  {selectedTag && (
                    <span className="tag-pop bg-pop-pink text-white border-pop-black">
                      #{selectedTag}
                      <button onClick={() => setSelectedTag(null)} className="ml-0.5">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  )}
                  {searchQuery && (
                    <span className="text-pop-black">"{searchQuery}"</span>
                  )}
                  <button onClick={clearFilters} className="btn-ghost-pop text-xs ml-auto">
                    全部清除
                  </button>
                </div>
              )}

              {/* Content */}
              {showEmpty ? (
                <EmptyState
                  hasIdeas={hasIdeas}
                  searchQuery={searchQuery}
                  selectedTag={selectedTag}
                  onClearFilters={clearFilters}
                />
              ) : view === 'board' ? (
                <BoardView
                  ideas={filteredIdeas}
                  onEdit={updateIdea}
                  onDelete={handleDelete}
                  onTogglePin={togglePin}
                  onAddTag={handleAddTag}
                  onClearTags={handleClearTags}
                  searchQuery={searchQuery}
                />
              ) : (
                <IdeaList
                  ideas={filteredIdeas}
                  onEdit={updateIdea}
                  onDelete={handleDelete}
                  onTogglePin={togglePin}
                  searchQuery={searchQuery}
                />
              )}
            </main>
            </>
            )}
          </div>
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <>
          <div
            className="fixed inset-0 bg-pop-black/60 z-40 lg:hidden animate-fade-in"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="fixed left-0 top-0 bottom-0 w-72 max-w-[80vw] z-50 lg:hidden p-4 overflow-y-auto bg-cream border-r-4 border-pop-black animate-slide-down">
            <div className="flex items-center justify-between mb-4">
              <span className="font-display text-lg text-pop-black tracking-wide uppercase">菜单</span>
              <button
                onClick={() => setSidebarOpen(false)}
                className="bg-white border-2 border-pop-black p-1.5 shadow-pop-sm hover:bg-pop-red hover:text-white transition-colors"
                aria-label="关闭菜单"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <Sidebar
              stats={stats}
              allTags={allTags}
              selectedTag={selectedTag}
              onSelectTag={(tag) => {
                setSelectedTag(tag)
                setSidebarOpen(false)
              }}
              onExport={handleExport}
              onImport={handleImport}
              onPurgeArchived={() => {
                purgeArchived()
                showToast('回收站已清空!')
              }}
              archivedCount={archived.length}
            />
          </div>
        </>
      )}

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-pop-in">
          <div className="bg-white border-3 border-pop-black shadow-pop-lg px-4 py-3 flex items-center gap-3">
            <div className="w-3 h-3 bg-pop-green border-2 border-pop-black" />
            <span className="text-sm font-bold font-sans text-pop-black">{toast.message}</span>
            {toast.action && (
              <button
                onClick={toast.action.onClick}
                className="btn-pop-blue text-xs px-3 py-1 ml-2"
              >
                {toast.action.label}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
