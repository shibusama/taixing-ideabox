/**
 * API 地址解析（部署可配置）
 *
 * 优先级：
 *   1. 构建时注入的 window.APP_CONFIG.apiBase（Nginx 部署时在 index.html 里配置）
 *   2. Vite 环境变量 VITE_API_BASE（.env 或构建命令传入）
 *   3. 默认值：同源 /api（生产 Nginx 反代），开发环境回退 127.0.0.1:8000
 */
function resolveApiBase() {
  // 1. 运行时注入（最灵活，改 index.html 即可切换后端，无需重新构建）
  if (typeof window !== 'undefined' && window.APP_CONFIG && window.APP_CONFIG.apiBase) {
    return window.APP_CONFIG.apiBase
  }
  // 2. Vite 构建期环境变量
  if (import.meta.env && import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  // 3. 默认：开发环境连本地后端 8000；生产环境同源（请求路径自带 /api，无需前缀）
  const isDev = import.meta.env && import.meta.env.DEV
  if (isDev) {
    return 'http://127.0.0.1:8000'
  }
  return ''
}

export const API_BASE = resolveApiBase()
