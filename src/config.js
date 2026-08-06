/**
 * API 地址解析。
 *
 * 开发与生产统一同源：前端构建产物由后端静态托管，请求路径自带 /api 前缀，无需单独配置后端地址。
 * 如需切换后端（如 Nginx 部署），可在 index.html 里注入 window.APP_CONFIG.apiBase。
 */
function resolveApiBase() {
  if (typeof window !== 'undefined' && window.APP_CONFIG && window.APP_CONFIG.apiBase) {
    return window.APP_CONFIG.apiBase
  }
  return ''
}

export const API_BASE = resolveApiBase()
