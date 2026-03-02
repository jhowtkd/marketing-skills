import { Header } from '@/components/layout/header'
import { NavigationPanel } from '@/components/layout/navigation-panel'
import { Workspace } from '@/components/layout/workspace'
import { CommandRail } from '@/components/layout/command-rail'
import { ToastContainer } from '@/components/ui/toast-container'
import { useKeyboard } from '@/hooks/use-keyboard'
import { useToast } from '@/hooks/ui/use-toast'

function App() {
  useKeyboard()
  const { toasts, removeToast } = useToast()

  return (
    <div className="h-screen flex flex-col bg-vm-bg">
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <aside className="w-64 border-r border-vm-border bg-vm-bg shrink-0" data-panel="navigation">
          <NavigationPanel />
        </aside>
        <main className="flex-1 min-w-0 bg-vm-bg" data-panel="workspace">
          <Workspace />
        </main>
        <aside className="w-72 shrink-0" data-panel="command">
          <CommandRail />
        </aside>
      </div>
    </div>
  )
}

export default App
