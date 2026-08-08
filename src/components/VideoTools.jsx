import { useState } from 'react'
import Inbox from './Inbox'
import VideoMindmap from './VideoMindmap'
import VideoNote from './VideoNote'
import VideoCover from './VideoCover'

const TABS = [
  { key: 'inbox', label: '收件箱' },
  { key: 'mindmap', label: '思维导图' },
  { key: 'note', label: 'Markdown 笔记' },
  { key: 'cover', label: 'AI 封面' },
]

export default function VideoTools() {
  const [tab, setTab] = useState('inbox')

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

      {tab === 'inbox' ? <Inbox />
        : tab === 'mindmap' ? <VideoMindmap />
        : tab === 'note' ? <VideoNote />
        : <VideoCover />}
    </div>
  )
}
