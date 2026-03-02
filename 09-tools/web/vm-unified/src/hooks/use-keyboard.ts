import { useEffect, useCallback } from 'react'
import { useStore } from './use-store'

export function useKeyboard() {
  const { toggleViewMode, selectBrand } = useStore()

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const { key, metaKey, ctrlKey } = event
    const mod = metaKey || ctrlKey

    // Mode toggle: ⌘D
    if (mod && key === 'd') {
      event.preventDefault()
      toggleViewMode()
      return
    }

    // Focus panels: ⌘1, ⌘2, ⌘3
    if (mod && key === '1') {
      event.preventDefault()
      ;(document.querySelector('[data-panel="navigation"]') as HTMLElement)?.focus()
      return
    }

    if (mod && key === '2') {
      event.preventDefault()
      ;(document.querySelector('[data-panel="workspace"]') as HTMLElement)?.focus()
      return
    }

    if (mod && key === '3') {
      event.preventDefault()
      ;(document.querySelector('[data-panel="command"]') as HTMLElement)?.focus()
      return
    }

    // Escape: clear selection
    if (key === 'Escape') {
      selectBrand(null)
      return
    }

    // Help: ?
    if (key === '?' && !mod) {
      event.preventDefault()
      // TODO: Show keyboard shortcuts modal
      console.log('Show keyboard shortcuts')
    }
  }, [toggleViewMode, selectBrand])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
