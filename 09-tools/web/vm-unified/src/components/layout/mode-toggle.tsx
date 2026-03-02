import { Code, MessageSquare } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { cn } from '@/lib/utils'

export function ModeToggle() {
  const { viewMode, toggleViewMode } = useStore()

  return (
    <button
      onClick={toggleViewMode}
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-vm-md transition-colors',
        'bg-vm-surface border border-vm-border hover:bg-vm-surface-elevated'
      )}
      title={`Switch to ${viewMode === 'guided' ? 'Dev' : 'Guided'} mode (⌘D)`}
    >
      {viewMode === 'guided' ? (
        <>
          <MessageSquare className="w-4 h-4 text-vm-primary" />
          <span className="text-sm text-vm-ink">Guided</span>
        </>
      ) : (
        <>
          <Code className="w-4 h-4 text-vm-primary" />
          <span className="text-sm text-vm-ink">Dev</span>
        </>
      )}
    </button>
  )
}
