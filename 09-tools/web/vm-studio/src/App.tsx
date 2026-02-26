import { Dashboard } from './components/Dashboard';
import { Editor } from './components/Editor';
import { TemplateLibrary } from './components/TemplateLibrary';
import { useStore } from './store';

function App() {
  const { currentView } = useStore();

  return (
    <div className="min-h-screen bg-gray-50">
      {currentView === 'dashboard' && <Dashboard />}
      {currentView === 'templates' && <TemplateLibrary />}
      {currentView === 'editor' && <Editor />}
    </div>
  );
}

export default App;
