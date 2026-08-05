// Tag color palette - Pop Art bold colors
export const TAG_COLORS = [
  { name: 'red',     bg: 'bg-pop-red/10',     text: 'text-pop-red',     border: 'border-pop-red',     solid: 'bg-pop-red text-white' },
  { name: 'blue',    bg: 'bg-pop-blue/10',    text: 'text-pop-blue',    border: 'border-pop-blue',    solid: 'bg-pop-blue text-white' },
  { name: 'yellow',  bg: 'bg-pop-yellow/15',  text: 'text-pop-black',   border: 'border-pop-yellow',  solid: 'bg-pop-yellow text-pop-black' },
  { name: 'pink',    bg: 'bg-pop-pink/10',    text: 'text-pop-pink',    border: 'border-pop-pink',    solid: 'bg-pop-pink text-white' },
  { name: 'green',   bg: 'bg-pop-green/10',   text: 'text-pop-green',   border: 'border-pop-green',   solid: 'bg-pop-green text-white' },
  { name: 'orange',  bg: 'bg-pop-orange/10',  text: 'text-pop-orange',  border: 'border-pop-orange',  solid: 'bg-pop-orange text-white' },
  { name: 'purple',  bg: 'bg-pop-purple/10',  text: 'text-pop-purple',  border: 'border-pop-purple',  solid: 'bg-pop-purple text-white' },
  { name: 'cyan',    bg: 'bg-pop-cyan/10',    text: 'text-pop-cyan',    border: 'border-pop-cyan',    solid: 'bg-pop-cyan text-pop-black' },
]

// Deterministic color assignment based on tag name hash
export function getTagColor(tagName) {
  let hash = 0
  for (let i = 0; i < tagName.length; i++) {
    hash = ((hash << 5) - hash) + tagName.charCodeAt(i)
    hash |= 0
  }
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}

// Common suggested tags for quick add
export const SUGGESTED_TAGS = ['灵感', '想法', '创意', '待办', '阅读', '项目', '学习', '生活']
