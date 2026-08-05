/**
 * API 地址解析（部署可配置）
 *
 * 优先级：
 *   1. 构建时注入的 window.APP_CONFIG.apiBase（Nginx 部署时在 index.html 里配置）
 *   2. Vite 环境变量 VITE_API_BASE（.env 或构建命令传入）
 *   3. 默认值：空字符串（同源）。开发环境由 Vite 代理把 /api 转发到本地后端，生产同源由后端统一服务
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
  // 3. 默认：开发环境由 Vite 代理转发 /api 到本地后端；生产同源（请求路径自带 /api，无需前缀）
  return ''
}

export const API_BASE = resolveApiBase()
