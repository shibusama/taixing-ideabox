import { useState } from 'react'
import VideoMindmap from './VideoMindmap'
import VideoNote from './VideoNote'

const TABS = [
  { key: 'mindmap', label: '思维导图' },
  { key: 'note', label: 'Markdown 笔记' },
]

export default function VideoTools() {
  const [tab, setTab] = useState('mindmap')

  return (
    <div>
      {/* Tab switch */}
      <div className="flex items-center border-2 border-pop-black shadow-pop-sm bg-white mb-6">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 py-2.5 font-display text-sm tracking-wide transition-colors ${
              tab === t.key
                ? 'bg-pop-blue text-white'
                : 'bg-white text-pop-black hover:bg-pop-yellow'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'mindmap' ? <VideoMindmap /> : <VideoNote />}
    </div>
  )
}
