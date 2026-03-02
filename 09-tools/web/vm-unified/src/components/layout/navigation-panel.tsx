import { ChevronDown, ChevronRight, Plus, MoreHorizontal, Loader2 } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { useBrands } from '@/hooks/api/use-brands'
import { useProjects } from '@/hooks/api/use-projects'
import { useThreads } from '@/hooks/api/use-threads'
import { cn } from '@/lib/utils'

export function NavigationPanel() {
  const {
    activeBrandId,
    activeProjectId,
    activeThreadId,
    selectBrand,
    selectProject,
    selectThread,
  } = useStore()

  const { data: brands = [], isLoading: isLoadingBrands } = useBrands()
  const { data: projects = [], isLoading: isLoadingProjects } = useProjects(activeBrandId)
  const { data: threads = [], isLoading: isLoadingThreads } = useThreads(activeProjectId)

  const getBrandProjects = (brandId: string) =>
    projects.filter(p => p.brandId === brandId)

  const getProjectThreads = (projectId: string) =>
    threads.filter(t => t.projectId === projectId)

  if (isLoadingBrands) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-vm-ink-muted" />
      </div>
    )
  }

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
                  <ChevronRight className="w-3.5 h-3.5 text-vm-ink-muted" />
                )}
                <span className="text-sm font-medium flex-1 text-left">{brand.name}</span>
                <button
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-vm-hover rounded transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="w-3.5 h-3.5" />
                </button>
              </button>

              {isActive && (
                <div className="ml-4 mt-0.5 space-y-0.5 border-l border-vm-border pl-2">
                  {isLoadingProjects ? (
                    <div className="px-2 py-1.5">
                      <Loader2 className="w-4 h-4 animate-spin text-vm-ink-muted" />
                    </div>
                  ) : (
                    brandProjects.map((project) => {
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

                          {isProjectActive && (
                            <div className="ml-4 mt-0.5 space-y-0.5">
                              {isLoadingThreads ? (
                                <div className="px-2 py-1.5">
                                  <Loader2 className="w-3 h-3 animate-spin text-vm-ink-muted" />
                                </div>
                              ) : (
                                projectThreads.map((thread) => {
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
                                })
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })
                  )}
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
