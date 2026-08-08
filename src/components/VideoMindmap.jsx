import { useEffect, useRef, useState } from 'react'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'
import { API_BASE } from '../config'

const transformer = new Transformer()

export default function VideoMindmap() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [mindmapMd, setMindmapMd] = useState('')
  const [cached, setCached] = useState(false)
  const [progress, setProgress] = useState('')
  const svgRef = useRef(null)
  const mmRef = useRef(null)

  // Render markmap whenever the markdown changes
  useEffect(() => {
    if (!svgRef.current || !mindmapMd) return
    const { root } = transformer.transform(mindmapMd)
    if (mmRef.current) {
      mmRef.current.destroy()
      mmRef.current = null
      svgRef.current.innerHTML = ''
    }
    // Make sure SVG has explicit dimensions before Markmap reads them
    const svg = svgRef.current
    svg.setAttribute('width', '100%')
    svg.setAttribute('height', '100%')
    const mm = Markmap.create(svg, {
      autoFit: true,
      duration: 0,
      initialExpandLevel: 99,
    })
    mm.setData(root)
    mmRef.current = mm
    // Multiple fit calls: container layout may not be settled when effect runs
    mm.fit()
    requestAnimationFrame(() => mm.fit())
    setTimeout(() => mm.fit(), 150)
    return () => {
      mm.destroy()
      mmRef.current = null
      if (svgRef.current) svgRef.current.innerHTML = ''
    }
  }, [mindmapMd])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed || loading) return

    setLoading(true)
    setError(null)
    setMindmapMd('')
    setProgress('')

    try {
      const resp = await fetch(`${API_BASE}/api/mindmap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmed }),
      })
      const data = await resp.json()
      if (data.error) throw new Error(data.error)
      // Cache hit: result returned directly, no task to poll
      if (data.result) {
        setMindmapMd(data.result.mindmap_md)
        setCached(true)
        setLoading(false)
        return
      }
      const { task_id } = data

      // Poll until done
      for (let i = 0; i < 120; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const poll = await fetch(`${API_BASE}/api/mindmap/${task_id}`)
        const state = await poll.json()
        if (state.progress) setProgress(state.progress)
        if (state.status === 'done') {
          setMindmapMd(state.result.mindmap_md)
          setCached(state.result.cached)
          setLoading(false)
          return
        }
        if (state.status === 'error') {
          throw new Error(state.error || '解析失败')
        }
      }
      throw new Error('解析超时，请稍后重试')
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
            placeholder="粘贴视频号 / 抖音视频链接，例如 https://weixin.qq.com/sph/xxx"
            className="input-pop flex-1 px-3 py-2.5 text-sm font-sans"
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="btn-pop-blue text-sm px-5 py-2.5 flex-shrink-0"
          >
            {loading ? '解析中…' : '生成导图!'}
          </button>
        </form>
        <p className="mt-2 text-[11px] font-mono font-bold text-pop-black/50">
          后端: {API_BASE} · 首次解析需下载视频+转写，约 1-3 分钟
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="pop-panel bg-white p-8 text-center animate-pop-in">
          <div className="inline-block w-10 h-10 border-3 border-pop-black border-t-transparent animate-spin mb-3" />
          <p className="font-display text-lg text-pop-black tracking-wide">
            {progress || '正在解析视频…'}
          </p>
          <p className="text-xs font-mono font-bold text-pop-black/50 mt-1">下载 · 提取音频 · 转写 · 生成导图</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="pop-panel bg-pop-red text-white p-4 mb-4 animate-pop-in">
          <p className="font-display text-base tracking-wide">解析失败!</p>
          <p className="text-xs font-sans mt-1 break-all opacity-90">{error}</p>
        </div>
      )}

      {/* Mindmap */}
      {mindmapMd && (
        <div className="pop-panel bg-white p-3 sm:p-4 animate-pop-in">
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="font-display text-pop-black tracking-wide uppercase">
              思维导图
            </span>
            {cached && (
              <span className="text-[10px] font-mono font-bold bg-pop-green text-white border-2 border-pop-black px-1.5 py-0.5">
                已缓存
              </span>
            )}
          </div>
          <div className="w-full border-2 border-pop-black bg-cream overflow-hidden" style={{ height: '60vh', minHeight: '400px' }}>
            <svg
              ref={svgRef}
              className="w-full h-full block"
              xmlns="http://www.w3.org/2000/svg"
            />
          </div>
          <p className="mt-2 text-[11px] font-mono font-bold text-pop-black/50">
            拖动空白处平移 · 滚轮缩放 · 点击节点展开/收起
          </p>
        </div>
      )}
    </div>
  )
}
