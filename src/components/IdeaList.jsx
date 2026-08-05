import IdeaCard from './IdeaCard'
import { groupByDate } from '../utils/helpers'

export default function IdeaList({ ideas, onEdit, onDelete, onTogglePin, searchQuery }) {
  if (ideas.length === 0) return null

  const pinned = ideas.filter(i => i.pinned)
  const unpinned = ideas.filter(i => !i.pinned)
  const groups = groupByDate(unpinned)

  return (
    <div className="space-y-8">
      {/* Pinned section */}
      {pinned.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <div className="bg-pop-red border-2 border-pop-black px-2.5 py-0.5 shadow-pop-sm">
              <span className="font-display text-white text-base tracking-wide uppercase">置顶!</span>
            </div>
            <span className="text-xs text-pop-black/60 font-mono font-bold">{pinned.length}</span>
          </div>
          <div className="grid gap-4">
            {pinned.map((idea) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                onEdit={onEdit}
                onDelete={onDelete}
                onTogglePin={onTogglePin}
                searchQuery={searchQuery}
              />
            ))}
          </div>
        </section>
      )}

      {/* Date grouped sections */}
      {Object.entries(groups).map(([dateLabel, dateIdeas]) => (
        <section key={dateLabel}>
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-pop-blue border-2 border-pop-black px-2.5 py-0.5 shadow-pop-sm">
              <span className="font-display text-white text-base tracking-wide uppercase">{dateLabel}</span>
            </div>
            <div className="flex-1 h-1 bg-pop-black" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #0a0a0a 0, #0a0a0a 4px, transparent 4px, transparent 8px)' }} />
            <span className="text-xs text-pop-black/60 font-mono font-bold">{dateIdeas.length}</span>
          </div>
          <div className="grid gap-4">
            {dateIdeas.map((idea) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                onEdit={onEdit}
                onDelete={onDelete}
                onTogglePin={onTogglePin}
                searchQuery={searchQuery}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
