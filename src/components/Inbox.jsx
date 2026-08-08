import { useEffect, useRef, useState } from 'react'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'
import { API_BASE } from '../config'

const transformer = new Transformer()

// 轻量 Markdown 渲染（复用 VideoNote 的思路）
function renderMarkdown(md) {
  const lines = md.split('\n')
  const out = []
  for (const raw of lines) {
    const line = raw.trimEnd()
    if (!line.trim()) continue
    const h = line.match(/^(#{1,6})\s+(.*)$/)
    if (h) {
      const lv = Math.min(h[1].length, 4)
      out.push(`<h${lv}>${h[2]}</h${lv}>`)
      continue
    }
    const quote = line.match(/^>\s?(.*)$/)
    if (quote) { out.push(`<blockquote>${quote[1]}</blockquote>`); continue }
    const bullet = line.match(/^[-*]\s+(.*)$/)
    if (bullet) { out.push(`<li>${bullet[1]}</li>`); continue }
    out.push(`<p>${line}</p>`)
  }
  return out.join('\n')
}

function MindmapView({ md }) {
  const svgRef = useRef(null)
  const mmRef = useRef(null)
  useEffect(() => {
    if (!svgRef.current || !md) return
    const { root } = transformer.transform(md)
    if (mmRef.current) { mmRef.current.destroy(); mmRef.current = null; svgRef.current.innerHTML = '' }
    const svg = svgRef.current
    svg.setAttribute('width', '100%')
    svg.setAttribute('height', '100%')
    const mm = Markmap.create(svg, { autoFit: true, duration: 0, initialExpandLevel: 99 })
    mm.setData(root)
    mmRef.current = mm
    mm.fit()
    requestAnimationFrame(() => mm.fit())
    setTimeout(() => mm.fit(), 150)
    return () => { mm.destroy(); mmRef.current = null; if (svgRef.current) svgRef.current.innerHTML = '' }
  }, [md])
  return <svg ref={svgRef} className="w-full h-full block" xmlns="http://www.w3.org/2000/svg" />
}

export default function Inbox() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null) // 展开的 {key, url}
  const [content, setContent] = useState(null)
  const [contentLoading, setContentLoading] = useState(false)
  const [tab, setTab] = useState('mindmap')

  const loadList = async () => {
    setLoading(true)
    try {
      const resp = await fetch(`${API_BASE}/api/inbox-list`)
      const data = await resp.json()
      setItems(data.items || [])
    } catch (e) {
      console.error('inbox list failed', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadList() }, [])

  const fetchContent = async (key, url, kind) => {
    setSelected({ key, url })
    setContentLoading(true)
    setContent(null)
    setTab(kind)
    try {
      const body = JSON.stringify({ url })
      const ep = kind === 'mindmap' ? '/api/mindmap' : kind === 'note' ? '/api/note' : '/api/cover'
      const resp = await fetch(`${API_BASE}${ep}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body,
      })
      const data = await resp.json()
      if (data.result) setContent(data.result)
      else if (data.error) setContent({ error: data.error })
    } catch (e) {
      setContent({ error: e.message })
    } finally {
      setContentLoading(false)
    }
  }

  return (
    <div className="animate-slide-up">
      <div className="pop-panel bg-white p-4 sm:p-5 mb-6">
        <div className="flex items-center justify-between">
          <span className="font-display text-pop-black tracking-wide uppercase">收件箱</span>
          <button type="button" onClick={loadList} className="text-xs font-mono font-bold border-2 border-pop-black px-2 py-1 hover:bg-pop-black hover:text-white transition-colors">
            刷新
          </button>
        </div>
        <p className="mt-1 text-[11px] font-mono font-bold text-pop-black/50">
          从微信收进的链接，点击可查看思维导图 / 笔记 / AI 封面
        </p>
      </div>

      {loading && (
        <div className="pop-panel bg-white p-8 text-center animate-pop-in">
          <div className="inline-block w-10 h-10 border-3 border-pop-black border-t-transparent animate-spin mb-3" />
          <p className="font-display text-lg text-pop-black tracking-wide">加载收件箱…</p>
        </div>
      )}

      {!loading && items.length === 0 && (
        <div className="pop-panel bg-white p-8 text-center text-pop-black/50 font-sans text-sm">
          还没有收进的链接。用微信把链接发给「灵感匣收件助手」吧。
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="space-y-3">
          {items.map(item => {
            const done = Object.values(item.statuses).filter(s => s === 'done').length
            return (
              <div key={item.key} className="pop-panel bg-white p-4 animate-pop-in">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-sans font-bold text-pop-black break-all flex-1">{item.url}</span>
                  <span className="text-[10px] font-mono font-bold bg-pop-green text-white border-2 border-pop-black px-1.5 py-0.5">
                    {done}/3 完成
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-1.5 text-[10px] font-mono font-bold">
                  {(['mindmap','note','cover']).map(k => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => fetchContent(item.key, item.url, k)}
                      className={`px-2 py-1 border-2 border-pop-black transition-colors ${
                        tab === k && selected?.key === item.key ? 'bg-pop-blue text-white' : 'bg-white text-pop-black hover:bg-pop-yellow'
                      }`}
                    >
                      {k === 'mindmap' ? '导图' : k === 'note' ? '笔记' : '封面'}
                    </button>
                  ))}
                </div>

                {selected?.key === item.key && (
                  <div className="mt-3 border-t-2 border-pop-black/20 pt-3">
                    {contentLoading && <p className="text-xs font-mono text-pop-black/50">加载中…</p>}
                    {!contentLoading && content && content.error && (
                      <p className="text-xs font-mono text-pop-red">加载失败: {content.error}</p>
                    )}
                    {!contentLoading && content && !content.error && tab === 'mindmap' && content.mindmap_md && (
                      <div className="w-full border-2 border-pop-black bg-cream overflow-hidden" style={{ height: '50vh', minHeight: '300px' }}>
                        <MindmapView md={content.mindmap_md} />
                      </div>
                    )}
                    {!contentLoading && content && !content.error && tab === 'note' && content.note_md && (
                      <div className="note-body" dangerouslySetInnerHTML={{ __html: renderMarkdown(content.note_md) }} />
                    )}
                    {!contentLoading && content && !content.error && tab === 'cover' && content.image_url && (
                      <div className="border-2 border-pop-black bg-cream overflow-hidden">
                        <img src={content.image_url} alt="AI 封面" className="w-full h-auto block" />
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
