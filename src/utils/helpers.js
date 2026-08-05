// Utility functions for the IdeaBox app

// Format relative time in Chinese
export function formatRelativeTime(timestamp) {
  const now = Date.now()
  const diff = now - timestamp
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const weeks = Math.floor(days / 7)
  const months = Math.floor(days / 30)

  if (seconds < 10) return '刚刚'
  if (seconds < 60) return `${seconds} 秒前`
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`
  if (weeks < 4) return `${weeks} 周前`
  if (months < 12) return `${months} 个月前`
  return new Date(timestamp).toLocaleDateString('zh-CN')
}

// Format full date for tooltips
export function formatFullDate(timestamp) {
  const date = new Date(timestamp)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const h = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${h}:${min}`
}

// Check if timestamp is today
export function isToday(timestamp) {
  const date = new Date(timestamp)
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

// Check if timestamp is yesterday
export function isYesterday(timestamp) {
  const date = new Date(timestamp)
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  return (
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()
  )
}

// Extract hashtags from text (#tag format)
export function extractTags(text) {
  const matches = text.match(/#[\u4e00-\u9fa5a-zA-Z0-9_]+/g)
  return matches ? matches.map(tag => tag.substring(1)) : []
}

// Strip hashtags from text for display
export function stripTags(text) {
  return text.replace(/#[\u4e00-\u9fa5a-zA-Z0-9_]+/g, '').trim()
}

// Highlight search matches in text
export function highlightMatch(text, query) {
  if (!query || !query.trim()) return text
  const regex = new RegExp(`(${query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<mark class="bg-pop-yellow text-pop-black px-0.5" style="font-weight:700">$1</mark>')
}

// Group ideas by date
export function groupByDate(ideas) {
  const groups = {}
  for (const idea of ideas) {
    let key
    if (isToday(idea.createdAt)) {
      key = '今天'
    } else if (isYesterday(idea.createdAt)) {
      key = '昨天'
    } else {
      const date = new Date(idea.createdAt)
      key = `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
    }
    if (!groups[key]) groups[key] = []
    groups[key].push(idea)
  }
  return groups
}
