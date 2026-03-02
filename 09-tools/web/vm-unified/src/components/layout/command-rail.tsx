import { Command, Play, CheckCircle, RotateCcw, Loader2 } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { useRuns, useResumeRun } from '@/hooks/api/use-runs'
import { Kbd } from '@/components/ui/kbd'
import { cn } from '@/lib/utils'

export function CommandRail() {
  const { activeThreadId, activeRunId } = useStore()
  const { data: runs = [], isLoading } = useRuns(activeThreadId)
  const activeRun = runs.find((r: { id: string }) => r.id === activeRunId)
  const resumeRun = useResumeRun()

  return (
    <div className="h-full flex flex-col bg-vm-surface border-l border-vm-border">
      <div className="p-3 border-b border-vm-border">
        <div className="flex items-center gap-2 px-3 py-2 rounded-vm-md bg-vm-bg border border-vm-border">
          <Command className="w-4 h-4 text-vm-ink-muted" />
          <input
            type="text"
            placeholder="Type a command..."
            className="flex-1 bg-transparent text-sm text-vm-ink placeholder:text-vm-ink-subtle outline-none"
          />
          <Kbd>⌘K</Kbd>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-vm-ink-muted" />
          </div>
        ) : activeRun ? (
          <>
            <Section title="Run Actions">
              <CommandItem 
                icon={Play} 
                label="Resume Workflow"
                onClick={() => activeRun && resumeRun.mutate({ runId: activeRun.id, threadId: activeThreadId! })}
                isLoading={resumeRun.isPending}
              />
              <CommandItem icon={CheckCircle} label="Approve Stage" />
              <CommandItem icon={RotateCcw} label="Retry Stage" />
            </Section>

            <Section title="Stage Status">
              {activeRun.stages?.map((stage) => (
                <div
                  key={stage.key}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm"
                >
                  <StatusDot status={stage.status} />
                  <span className="text-vm-ink-muted">{stage.name}</span>
                </div>
              ))}
            </Section>
          </>
        ) : (
          <div className="px-2 py-8 text-center">
            <p className="text-sm text-vm-ink-subtle">No active run</p>
            <p className="text-xs text-vm-ink-subtle mt-1">
              Select a thread to view actions
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="px-2 py-1.5 text-xs font-medium text-vm-ink-subtle uppercase tracking-wider">
        {title}
      </div>
      <div className="mt-1 space-y-0.5">{children}</div>
    </div>
  )
}

function CommandItem({
  icon: Icon,
  label,
  shortcut,
  onClick,
  isLoading,
}: {
  icon: React.ElementType
  label: string
  shortcut?: string
  onClick?: () => void
  isLoading?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className={cn(
        'w-full flex items-center gap-3 px-2 py-1.5 rounded-vm-md transition-colors group',
        'hover:bg-vm-hover text-left disabled:opacity-50 disabled:cursor-not-allowed'
      )}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 text-vm-ink-muted animate-spin" />
      ) : (
        <Icon className="w-4 h-4 text-vm-ink-muted" />
      )}
      <span className="text-sm text-vm-ink">{label}</span>
      {shortcut && (
        <span className="ml-auto text-xs text-vm-ink-subtle opacity-0 group-hover:opacity-100 transition-opacity">
          {shortcut}
        </span>
      )}
    </button>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-vm-ink-subtle',
    running: 'bg-vm-primary animate-pulse',
    waiting_approval: 'bg-vm-warning',
    completed: 'bg-vm-success',
    failed: 'bg-vm-error',
    skipped: 'bg-vm-ink-subtle',
  }
  return <div className={cn('w-2 h-2 rounded-full', colors[status] || colors.pending)} />
}
