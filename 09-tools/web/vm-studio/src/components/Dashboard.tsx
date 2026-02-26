import { Clock, FileText, Plus, Trash2 } from 'lucide-react';
import { formatDate, getStatusColor, getStatusLabel } from '../lib/utils';
import { useStore } from '../store';
import { Button } from './ui/Button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/Card';

export function Dashboard() {
  const { projects, setView, loadProject, deleteProject } = useStore();

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Meus Projetos</h1>
          <p className="text-gray-600 mt-1">
            {projects.length === 0
              ? 'Vamos criar seu primeiro projeto de marketing?'
              : `${projects.length} projeto${projects.length === 1 ? '' : 's'}`}
          </p>
        </div>
        <Button onClick={() => setView('templates')} size="lg">
          <Plus className="w-5 h-5 mr-2" />
          Novo Projeto
        </Button>
      </div>

      {projects.length === 0 && (
        <Card className="p-12 text-center">
          <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-primary-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Nenhum projeto ainda</h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Escolha um template e crie conteúdo de marketing profissional em minutos.
          </p>
          <Button onClick={() => setView('templates')}>
            <Plus className="w-4 h-4 mr-2" />
            Escolher Template
          </Button>
        </Card>
      )}

      {projects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Card key={project.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="line-clamp-1">{project.name}</CardTitle>
                    <CardDescription>{project.templateName}</CardDescription>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm('Tem certeza que deseja excluir este projeto?')) {
                        deleteProject(project.id);
                      }
                    }}
                    className="text-gray-400 hover:text-red-500 transition-colors p-1"
                    aria-label={`Excluir projeto ${project.name}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {formatDate(project.updatedAt)}
                  </span>
                </div>
              </CardContent>
              <CardFooter className="flex items-center justify-between">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                  {getStatusLabel(project.status)}
                </span>
                <Button variant="secondary" size="sm" onClick={() => loadProject(project)}>
                  Abrir
                </Button>
              </CardFooter>
            </Card>
          ))}

          <button
            onClick={() => setView('templates')}
            className="border-2 border-dashed border-gray-300 rounded-xl p-6 flex flex-col items-center justify-center gap-3 text-gray-500 hover:border-primary-500 hover:text-primary-600 transition-colors min-h-[200px]"
          >
            <Plus className="w-8 h-8" />
            <span className="font-medium">Criar novo projeto</span>
          </button>
        </div>
      )}
    </div>
  );
}
