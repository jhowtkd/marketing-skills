import { ChatHomeView } from './components/ChatHomeView';
import { Dashboard } from './components/Dashboard';
import { Editor } from './components/Editor';
import { TemplateSuggestionView } from './components/TemplateSuggestionView';
import { TemplateLibrary } from './components/TemplateLibrary';
import { useStore } from './store';

function App() {
  const { currentView, phase, selectedTemplate } = useStore();

  if (phase === 'chat_input') {
    return <ChatHomeView />;
  }

  if (phase === 'template_suggestion') {
    return <TemplateSuggestionView />;
  }

  if (phase === 'generating' || phase === 'deliverable_ready' || phase === 'refining') {
    if (currentView === 'templates' || (phase === 'generating' && !selectedTemplate)) {
      return (
        <div className="min-h-screen bg-gray-50">
          <TemplateLibrary />
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-gray-50">
        <Editor />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {currentView === 'dashboard' && <Dashboard />}
      {currentView === 'templates' && <TemplateLibrary />}
      {currentView === 'editor' && <Editor />}
    </div>
  );
}

export default App;
