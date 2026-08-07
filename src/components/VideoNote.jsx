import { useState } from 'react'
import { API_BASE } from '../config'

// 轻量 Markdown 渲染（零依赖）：支持标题/列表/引用/加粗/行内代码/分隔线
function renderInline(text) {
  return text
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
}

function renderMarkdown(md) {
  const lines = md.split('\n')
  const out = []
  let list = []
  let listType = null
  const flushList = () => {
    if (!list.length) return
    out.push(`<ul class="note-list">${list.join('')}</ul>`)
    list = []
    listType = null
  }
  for (const raw of lines) {
    const line = raw.trimEnd()
    if (!line.trim()) {
      flushList()
      out.push('')
      continue
    }
    const h1 = line.match(/^(#{1,6})\s+(.*)$/)
    if (h1) {
      flushList()
      const level = h1[1].length
      out.push(`<h${Math.min(level, 4)} class="note-h${Math.min(level, 4)}">${renderInline(h1[2])}</h${Math.min(level, 4)}>`)
      continue
    }
    const quote = line.match(/^>\s?(.*)$/)
    if (quote) {
      flushList()
      out.push(`<blockquote class="note-quote">${renderInline(quote[1])}</blockquote>`)
      continue
    }
    const bullet = line.match(/^[-*]\s+(.*)$/)
    if (bullet) {
      if (listType !== 'ul') flushList()
      listType = 'ul'
      list.push(`<li>${renderInline(bullet[1])}</li>`)
      continue
    }
    const num = line.match(/^\d+[.、)]\s+(.*)$/)
    if (num) {
      if (listType !== 'ol') flushList()
      listType = 'ol'
      list.push(`<li>${renderInline(num[1])}</li>`)
      continue
    }
    const hr = line.match(/^(-{3,}|\*{3,})$/u)
    if (hr) {
      flushList()
      out.push('<hr class="note-hr" />')
      continue
    }
    flushList()
    out.push(`<p class="note-p">${renderInline(line)}</p>`)
  }
  flushList()
  return out.join('\n')
}

export default function VideoNote() {
  const [url, setUrl] = useState('')
  const [detail, setDetail] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [noteMd, setNoteMd] = useState('')
  const [cached, setCached] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed || loading) return

    setLoading(true)
    setError(null)
    setNoteMd('')

    try {
      const resp = await fetch(`${API_BASE}/api/note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmed, detail }),
      })
      const data = await resp.json()
      if (data.error) throw new Error(data.error)
      // Cache hit: result returned directly
      if (data.result) {
        setNoteMd(data.result.note_md)
        setCached(data.result.cached)
        setLoading(false)
        return
      }
      const { task_id } = data

      // Poll until done
      for (let i = 0; i < 120; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const poll = await fetch(`${API_BASE}/api/note/${task_id}`)
        const state = await poll.json()
        if (state.status === 'done') {
          setNoteMd(state.result.note_md)
          setCached(state.result.cached)
          setLoading(false)
          return
        }
        if (state.status === 'error') {
          throw new Error(state.error || '生成失败')
        }
      }
      throw new Error('生成超时，请稍后重试')
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="animate-slide-up">
      {/* Input panel */}
      <div className="pop-panel bg-white p-4 sm:p-5 mb-6">
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="粘贴视频号 / 抖音视频链接，生成 Markdown 笔记"
            className="input-pop flex-1 px-3 py-2.5 text-sm font-sans"
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="btn-pop-blue text-sm px-5 py-2.5 flex-shrink-0"
          >
            {loading ? '生成中…' : '生成笔记!'}
          </button>
        </form>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-pop-black/50 cursor-pointer">
            <input
              type="checkbox"
              checked={detail}
              onChange={(e) => setDetail(e.target.checked)}
              className="accent-pop-black"
            />
            详细模式（含结构分析）
          </label>
          <span className="text-[11px] font-mono font-bold text-pop-black/50">
            后端: {API_BASE} · 首次生成需下载视频+转写，约 1-3 分钟
          </span>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="pop-panel bg-white p-8 text-center animate-pop-in">
          <div className="inline-block w-10 h-10 border-3 border-pop-black border-t-transparent animate-spin mb-3" />
          <p className="font-display text-lg text-pop-black tracking-wide">正在生成笔记…</p>
          <p className="text-xs font-mono font-bold text-pop-black/50 mt-1">下载 · 提取音频 · 转写 · 生成笔记</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="pop-panel bg-pop-red text-white p-4 mb-4 animate-pop-in">
          <p className="font-display text-base tracking-wide">生成失败!</p>
          <p className="text-xs font-sans mt-1 break-all opacity-90">{error}</p>
        </div>
      )}

      {/* Note */}
      {noteMd && (
        <div className="pop-panel bg-white p-4 sm:p-6 animate-pop-in">
          <div className="flex items-center justify-between mb-3 px-1">
            <span className="font-display text-pop-black tracking-wide uppercase">
              Markdown 笔记
            </span>
            <div className="flex items-center gap-2">
              {cached && (
                <span className="text-[10px] font-mono font-bold bg-pop-green text-white border-2 border-pop-black px-1.5 py-0.5">
                  已缓存
                </span>
              )}
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard?.writeText(noteMd)
                }}
                className="text-[10px] font-mono font-bold border-2 border-pop-black px-1.5 py-0.5 hover:bg-pop-black hover:text-white transition-colors"
              >
                复制
              </button>
            </div>
          </div>
          <div className="note-body" dangerouslySetInnerHTML={{ __html: renderMarkdown(noteMd) }} />
        </div>
      )}
    </div>
  )
}
