export default function App() {
  return (
    <div data-vm-ui="react" className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-lg font-semibold text-slate-900">VM Workspace</h1>
          <p className="mt-1 text-sm text-slate-500">UI React (WIP)</p>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-700">
            Scaffold OK. Proximo passo: integrar <code>/api/v2/*</code>.
          </p>
        </div>
      </main>
    </div>
  );
}
