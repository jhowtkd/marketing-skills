import { Header } from '@/components/layout/header'
import { NavigationPanel } from '@/components/layout/navigation-panel'
import { Workspace } from '@/components/layout/workspace'
import { CommandRail } from '@/components/layout/command-rail'

function App() {
  return (
    <div className="h-screen flex flex-col bg-vm-bg">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <aside className="w-64 border-r border-vm-border bg-vm-bg shrink-0">
          <NavigationPanel />
        </aside>
        <main className="flex-1 min-w-0 bg-vm-bg">
          <Workspace />
        </main>
        <aside className="w-72 shrink-0">
          <CommandRail />
        </aside>
      </div>
    </div>
  )
}

export default App
