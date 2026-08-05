// Ideas management hook - CRUD operations backed by the FastAPI server (SQLite)
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { extractTags } from '../utils/helpers'

const API_BASE = 'http://127.0.0.1:8000'

async function api(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* keep status text */ }
    throw new Error(detail)
  }
  return resp.json()
}

export function useIdeas() {
  const [ideas, setIdeas] = useState([])
  const [archived, setArchived] = useState([])
  const [loaded, setLoaded] = useState(false)

  // Serialize write operations so undo/redo and rapid updates stay in order
  const opQueue = useRef(Promise.resolve())
  const enqueue = useCallback((fn) => {
    const run = opQueue.current.then(fn).catch((err) => {
      console.error('[useIdeas] operation failed:', err)
    })
    opQueue.current = run.then(() => undefined)
    return run
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [list, arch] = await Promise.all([
        api('/api/ideas'),
        api('/api/ideas/archived'),
      ])
      setIdeas(list)
      setArchived(arch)
    } catch (err) {
      console.error('[useIdeas] refresh failed:', err)
    }
  }, [])

  // Initial load + one-time migration: if DB is empty but the browser still
  // has legacy LocalStorage data (ideabox:ideas), push it into the DB once.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [list, arch] = await Promise.all([
          api('/api/ideas'),
          api('/api/ideas/archived'),
        ])
        if (list.length === 0 && arch.length === 0) {
          const legacyIdeas = JSON.parse(localStorage.getItem('ideabox:ideas') || '[]')
          const legacyArchived = JSON.parse(localStorage.getItem('ideabox:archived') || '[]')
          if (legacyIdeas.length > 0 || legacyArchived.length > 0) {
            await api('/api/import', {
              method: 'POST',
              body: JSON.stringify({ ideas: legacyIdeas, archived: legacyArchived }),
            })
            console.log('[useIdeas] legacy LocalStorage data migrated to DB')
          }
        }
      } catch (err) {
        console.warn('[useIdeas] migration check skipped:', err)
      } finally {
        if (!cancelled) {
          await refresh()
          setLoaded(true)
        }
      }
    })()
    return () => { cancelled = true }
  }, [refresh])

  // Add a new idea
  const addIdea = useCallback((content, explicitTags = []) => {
    const extractedTags = extractTags(content)
    const allTags = [...new Set([...extractedTags, ...explicitTags])]
    return enqueue(async () => {
      await api('/api/ideas', {
        method: 'POST',
        body: JSON.stringify({
          content: content.trim(),
          tags: allTags,
          pinned: false,
        }),
      })
      await refresh()
    })
  }, [enqueue, refresh])

  // Update an existing idea
  const updateIdea = useCallback((id, updates) => {
    return enqueue(async () => {
      await api(`/api/ideas/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      })
      await refresh()
    })
  }, [enqueue, refresh])

  // Delete an idea (soft delete -> archive)
  const deleteIdea = useCallback((id) => {
    return enqueue(async () => {
      await api(`/api/ideas/${id}`, { method: 'DELETE' })
      await refresh()
    })
  }, [enqueue, refresh])

  // Restore from archive
  const restoreIdea = useCallback((id) => {
    return enqueue(async () => {
      await api(`/api/ideas/${id}/restore`, { method: 'POST' })
      await refresh()
    })
  }, [enqueue, refresh])

  // Toggle pin status
  const togglePin = useCallback((id) => {
    return enqueue(async () => {
      await api(`/api/ideas/${id}/pin`, { method: 'POST' })
      await refresh()
    })
  }, [enqueue, refresh])

  // Permanently delete from archive
  const purgeArchived = useCallback(() => {
    return enqueue(async () => {
      await api('/api/archived', { method: 'DELETE' })
      await refresh()
    })
  }, [enqueue, refresh])

  // Get all tags with counts
  const allTags = useMemo(() => {
    const tagMap = {}
    for (const idea of ideas) {
      for (const tag of idea.tags) {
        tagMap[tag] = (tagMap[tag] || 0) + 1
      }
    }
    return Object.entries(tagMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
  }, [ideas])

  // Stats
  const stats = useMemo(() => {
    const now = Date.now()
    const dayAgo = now - 24 * 60 * 60 * 1000
    const weekAgo = now - 7 * 24 * 60 * 60 * 1000

    return {
      total: ideas.length,
      today: ideas.filter(i => i.createdAt > dayAgo).length,
      thisWeek: ideas.filter(i => i.createdAt > weekAgo).length,
      pinned: ideas.filter(i => i.pinned).length,
      tags: allTags.length,
      archived: archived.length,
    }
  }, [ideas, archived, allTags])

  // Export all data as JSON
  const exportData = useCallback(async () => {
    const data = await api('/api/export')
    return JSON.stringify(
      { ideas: data.ideas, archived: data.archived, exportedAt: data.exportedAt },
      null,
      2
    )
  }, [])

  // Import data from JSON
  const importData = useCallback((jsonString) => {
    return enqueue(async () => {
      let data
      try {
        data = JSON.parse(jsonString)
      } catch {
        return false
      }
      if (!data.ideas) return false
      await api('/api/import', {
        method: 'POST',
        body: JSON.stringify({ ideas: data.ideas, archived: data.archived || [] }),
      })
      await refresh()
      return true
    })
  }, [enqueue, refresh])

  return {
    ideas,
    archived,
    allTags,
    stats,
    loaded,
    addIdea,
    updateIdea,
    deleteIdea,
    restoreIdea,
    togglePin,
    purgeArchived,
    exportData,
    importData,
    refresh,
  }
}
