import { ChevronRight, Search } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { ModeToggle } from './mode-toggle'

export function Header() {
  const { activeBrandId, activeProjectId, activeThreadId, brands, projects, threads } = useStore()

  const activeBrand = brands.find(b => b.id === activeBrandId)
  const activeProject = projects.find(p => p.id === activeProjectId)
  const activeThread = threads.find(t => t.id === activeThreadId)

  return (
    <header className="h-14 border-b border-vm-border bg-vm-bg flex items-center px-4 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-vm-md bg-vm-primary flex items-center justify-center">
          <span className="text-white font-bold text-sm">VM</span>
        </div>
        <span className="font-semibold text-vm-ink">Vibe Marketing</span>
      </div>

      {/* Breadcrumb */}
      <nav className="ml-8 flex items-center gap-1 text-sm">
        {activeBrand ? (
          <>
            <span className="text-vm-ink font-medium">{activeBrand.name}</span>
            {activeProject && (
              <>
                <ChevronRight className="w-4 h-4 text-vm-ink-subtle" />
                <span className="text-vm-ink">{activeProject.name}</span>
              </>
            )}
            {activeThread && (
              <>
                <ChevronRight className="w-4 h-4 text-vm-ink-subtle" />
                <span className="text-vm-primary">{activeThread.name}</span>
              </>
            )}
          </>
        ) : (
          <span className="text-vm-ink-subtle">No brand selected</span>
        )}
      </nav>

      {/* Right Actions */}
      <div className="ml-auto flex items-center gap-2">
        <button className="p-2 rounded-vm-md hover:bg-vm-hover transition-colors">
          <Search className="w-4 h-4 text-vm-ink-muted" />
        </button>
        <ModeToggle />
      </div>
    </header>
  )
}
