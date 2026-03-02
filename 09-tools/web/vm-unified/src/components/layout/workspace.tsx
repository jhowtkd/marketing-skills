import { AnimatePresence, motion } from 'framer-motion'
import { useStore } from '@/hooks/use-store'

export function Workspace() {
  const { viewMode } = useStore()

  return (
    <div className="h-full overflow-auto p-4">
      <AnimatePresence mode="wait">
        {viewMode === 'guided' ? (
          <motion.div
            key="guided"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <GuidedMode />
          </motion.div>
        ) : (
          <motion.div
            key="dev"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <DevMode />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Placeholders - implementar nas próximas tasks
function GuidedMode() {
  const { chat, setChatRequest, setChatGenerating } = useStore()

  return (
    <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold text-vm-ink mb-2">
        What do you want to create?
      </h1>
      <p className="text-vm-ink-muted mb-8 text-center">
        Describe your goal and I&apos;ll suggest the best templates for your marketing workflow.
      </p>

      <div className="w-full">
        <div className="relative">
          <textarea
            value={chat.request}
            onChange={(e) => setChatRequest(e.target.value)}
            className="w-full h-32 p-4 rounded-vm-lg bg-vm-surface border border-vm-border text-vm-ink placeholder:text-vm-ink-subtle focus:outline-none focus:ring-2 focus:ring-vm-primary/20 resize-none"
            placeholder="e.g., Landing page for B2B consulting leads..."
          />
          <button
            onClick={() => setChatGenerating(true)}
            disabled={!chat.request.trim() || chat.isGenerating}
            className="absolute bottom-3 right-3 px-4 py-1.5 rounded-vm-md bg-vm-primary text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {chat.isGenerating ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
  )
}

function DevMode() {
  const { getActiveThread, getActiveRun } = useStore()
  const thread = getActiveThread()
  const run = getActiveRun()

  if (!thread) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-vm-ink">No thread selected</p>
          <p className="text-vm-ink-muted text-sm mt-1">
            Select a thread from the navigation panel
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-3 rounded-vm-lg bg-vm-surface border border-vm-border">
          <p className="text-xs text-vm-ink-subtle uppercase tracking-wider">Thread</p>
          <p className="text-sm text-vm-ink font-medium mt-1">{thread.name}</p>
        </div>
        <div className="p-3 rounded-vm-lg bg-vm-surface border border-vm-border">
          <p className="text-xs text-vm-ink-subtle uppercase tracking-wider">Status</p>
          <p className="text-sm text-vm-success font-medium mt-1">
            {run?.status || 'No run'}
          </p>
        </div>
        <div className="p-3 rounded-vm-lg bg-vm-surface border border-vm-border">
          <p className="text-xs text-vm-ink-subtle uppercase tracking-wider">Stage</p>
          <p className="text-sm text-vm-ink font-medium mt-1">
            {run?.currentStage || '-'}
          </p>
        </div>
      </div>

      <div className="flex-1 rounded-vm-lg bg-vm-surface border border-vm-border p-4">
        <p className="text-vm-ink-muted text-center">
          DAG visualization coming soon...
        </p>
      </div>
    </div>
  )
}
