// Ideas management hook - CRUD operations with LocalStorage persistence
import { useCallback, useMemo } from 'react'
import { useLocalStorage } from './useLocalStorage'
import { generateId, extractTags } from '../utils/helpers'

export function useIdeas() {
  const [ideas, setIdeas] = useLocalStorage('ideabox:ideas', [])
  const [archived, setArchived] = useLocalStorage('ideabox:archived', [])

  // Add a new idea
  const addIdea = useCallback((content, explicitTags = []) => {
    const extractedTags = extractTags(content)
    const allTags = [...new Set([...extractedTags, ...explicitTags])]

    const newIdea = {
      id: generateId(),
      content: content.trim(),
      tags: allTags,
      pinned: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }

    setIdeas(prev => [newIdea, ...prev])
    return newIdea
  }, [setIdeas])

  // Update an existing idea
  const updateIdea = useCallback((id, updates) => {
    setIdeas(prev =>
      prev.map(idea =>
        idea.id === id
          ? { ...idea, ...updates, updatedAt: Date.now() }
          : idea
      )
    )
  }, [setIdeas])

  // Delete an idea (move to archived first for undo)
  const deleteIdea = useCallback((id) => {
    const idea = ideas.find(i => i.id === id)
    if (idea) {
      setArchived(prev => [{ ...idea, deletedAt: Date.now() }, ...prev])
    }
    setIdeas(prev => prev.filter(i => i.id !== id))
  }, [ideas, setIdeas, setArchived])

  // Restore from archive
  const restoreIdea = useCallback((id) => {
    const idea = archived.find(i => i.id === id)
    if (idea) {
      const { deletedAt, ...restored } = idea
      setIdeas(prev => [restored, ...prev])
      setArchived(prev => prev.filter(i => i.id !== id))
    }
  }, [archived, setIdeas, setArchived])

  // Toggle pin status
  const togglePin = useCallback((id) => {
    setIdeas(prev =>
      prev.map(idea =>
        idea.id === id ? { ...idea, pinned: !idea.pinned } : idea
      )
    )
  }, [setIdeas])

  // Permanently delete from archive
  const purgeArchived = useCallback(() => {
    setArchived([])
  }, [setArchived])

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
  const exportData = useCallback(() => {
    return JSON.stringify({ ideas, archived, exportedAt: new Date().toISOString() }, null, 2)
  }, [ideas, archived])

  // Import data from JSON
  const importData = useCallback((jsonString) => {
    try {
      const data = JSON.parse(jsonString)
      if (data.ideas) setIdeas(data.ideas)
      if (data.archived) setArchived(data.archived)
      return true
    } catch {
      return false
    }
  }, [setIdeas, setArchived])

  return {
    ideas,
    archived,
    allTags,
    stats,
    addIdea,
    updateIdea,
    deleteIdea,
    restoreIdea,
    togglePin,
    purgeArchived,
    exportData,
    importData,
  }
}
