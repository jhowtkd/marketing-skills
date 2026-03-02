import { ChevronDown, ChevronRight, Plus, MoreHorizontal } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { cn } from '@/lib/utils'

export function NavigationPanel() {
  const {
    brands,
    projects,
    threads,
    activeBrandId,
    activeProjectId,
    activeThreadId,
    selectBrand,
    selectProject,
    selectThread,
  } = useStore()

  const getBrandProjects = (brandId: string) =>
    projects.filter(p => p.brandId === brandId)

  const getProjectThreads = (projectId: string) =>
    threads.filter(t => t.projectId === projectId)

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-medium text-vm-ink-subtle uppercase tracking-wider">
          Brands
        </span>
      </div>

      <div className="space-y-1">
        {brands.map((brand) => {
          const isActive = brand.id === activeBrandId
          const brandProjects = getBrandProjects(brand.id)

          return (
            <div key={brand.id} className="group">
              <button
                onClick={() => selectBrand(isActive ? null : brand.id)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded-vm-md transition-colors',
                  isActive ? 'bg-vm-primary-dim text-vm-primary' : 'hover:bg-vm-hover'
                )}
              >
                {isActive ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-vm-ink-subtle" />
                )}
                <span className="text-sm font-medium flex-1 text-left">{brand.name}</span>
                <button
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-vm-hover rounded transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="w-3.5 h-3.5" />
                </button>
              </button>

              {isActive && brandProjects.length > 0 && (
                <div className="ml-4 mt-0.5 space-y-0.5 border-l border-vm-border pl-2">
                  {brandProjects.map((project) => {
                    const isProjectActive = project.id === activeProjectId
                    const projectThreads = getProjectThreads(project.id)

                    return (
                      <div key={project.id}>
                        <button
                          onClick={() => selectProject(isProjectActive ? null : project.id)}
                          className={cn(
                            'w-full flex items-center gap-2 px-2 py-1.5 rounded-vm-md transition-colors',
                            isProjectActive ? 'text-vm-ink' : 'text-vm-ink-muted hover:text-vm-ink hover:bg-vm-hover'
                          )}
                        >
                          {isProjectActive ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                          <span className="text-sm">{project.name}</span>
                        </button>

                        {isProjectActive && projectThreads.length > 0 && (
                          <div className="ml-4 mt-0.5 space-y-0.5">
                            {projectThreads.map((thread) => {
                              const isThreadActive = thread.id === activeThreadId
                              return (
                                <button
                                  key={thread.id}
                                  onClick={() => selectThread(thread.id)}
                                  className={cn(
                                    'w-full text-left px-2 py-1.5 rounded-vm-md text-sm transition-colors',
                                    isThreadActive
                                      ? 'bg-vm-primary-dim text-vm-primary'
                                      : 'text-vm-ink-muted hover:bg-vm-hover'
                                  )}
                                >
                                  {thread.name}
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-vm-md border border-dashed border-vm-border text-sm text-vm-ink-muted hover:border-vm-primary hover:text-vm-primary transition-colors">
        <Plus className="w-4 h-4" />
        New Brand
      </button>
    </div>
  )
}
