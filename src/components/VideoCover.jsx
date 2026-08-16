import { useState } from 'react'
import { API_BASE } from '../config'

export default function VideoCover() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [cover, setCover] = useState(null)
  const [cached, setCached] = useState(false)
  const [progress, setProgress] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed || loading) return

    setLoading(true)
    setError(null)
    setCover(null)
    setProgress('')

    try {
      const resp = await fetch(`${API_BASE}/api/cover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmed }),
      })
      const data = await resp.json()
      if (data.error) throw new Error(data.error)
      // Cache hit: result returned directly
      if (data.result) {
        setCover(data.result)
        setCached(data.result.cached)
        setLoading(false)
        return
      }
      const { task_id } = data

      // Poll until done
      for (let i = 0; i < 120; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const poll = await fetch(`${API_BASE}/api/cover/${task_id}`)
        const state = await poll.json()
        if (state.progress) setProgress(state.progress)
        if (state.status === 'done') {
          setCover(state.result)
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
            placeholder="粘贴视频号 / 抖音视频链接，生成信息海报"
            className="input-pop flex-1 px-3 py-2.5 text-sm font-sans"
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="btn-pop-blue text-sm px-5 py-2.5 flex-shrink-0"
          >
            {loading ? '生成中…' : '生成海报!'}
          </button>
        </form>
        <p className="mt-2 text-[11px] font-mono font-bold text-pop-black/50">
          后端: {API_BASE} · AI 分析视频内容 → 生成信息海报 · 约 1-3 分钟
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="pop-panel bg-white p-8 text-center animate-pop-in">
          <div className="inline-block w-10 h-10 border-3 border-pop-black border-t-transparent animate-spin mb-3" />
          <p className="font-display text-lg text-pop-black tracking-wide">
            {progress || '正在生成海报…'}
          </p>
          <p className="text-xs font-mono font-bold text-pop-black/50 mt-1">工作流解析 · 生成海报</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="pop-panel bg-pop-red text-white p-4 mb-4 animate-pop-in">
          <p className="font-display text-base tracking-wide">生成失败!</p>
          <p className="text-xs font-sans mt-1 break-all opacity-90">{error}</p>
        </div>
      )}

      {/* Cover image */}
      {cover && cover.image_url && (
        <div className="pop-panel bg-white p-4 sm:p-6 animate-pop-in">
          <div className="flex items-center justify-between mb-3 px-1">
            <span className="font-display text-pop-black tracking-wide uppercase">
              信息海报
            </span>
            <div className="flex items-center gap-2">
              {cached && (
                <span className="text-[10px] font-mono font-bold bg-pop-green text-white border-2 border-pop-black px-1.5 py-0.5">
                  已缓存
                </span>
              )}
              <a
                href={cover.image_url}
                target="_blank"
                rel="noreferrer"
                className="text-[10px] font-mono font-bold border-2 border-pop-black px-1.5 py-0.5 hover:bg-pop-black hover:text-white transition-colors"
              >
                新窗口打开
              </a>
            </div>
          </div>
          <div className="border-2 border-pop-black bg-cream overflow-hidden">
            <img
              src={cover.image_url}
              alt="信息海报"
              className="w-full h-auto block"
            />
          </div>
        </div>
      )}
    </div>
  )
}
