import { useState } from 'react'
import ProjectsView from './components/ProjectsView'
import TemplatesView from './components/TemplatesView'
import OverviewView from './components/OverviewView'
import ProjectDetailView from './components/ProjectDetailView'
import SystemCheckView from './components/SystemCheckView'

type View =
  | { name: 'projects' }
  | { name: 'templates' }
  | { name: 'overview' }
  | { name: 'checks' }
  | { name: 'project'; id: number }

export default function App() {
  const [view, setView] = useState<View>({ name: 'projects' })

  return (
    <div className="app">
      <header className="topbar">
        <h1 onClick={() => setView({ name: 'projects' })}>Field Briefing</h1>
        <nav>
          <button
            className={view.name === 'projects' || view.name === 'project' ? 'active' : ''}
            onClick={() => setView({ name: 'projects' })}
          >
            Projects
          </button>
          <button
            className={view.name === 'templates' ? 'active' : ''}
            onClick={() => setView({ name: 'templates' })}
          >
            Templates
          </button>
          <button
            className={view.name === 'overview' ? 'active' : ''}
            onClick={() => setView({ name: 'overview' })}
          >
            Risk Overview
          </button>
          <button
            className={view.name === 'checks' ? 'active' : ''}
            onClick={() => setView({ name: 'checks' })}
          >
            System Check
          </button>
        </nav>
      </header>
      <main className="container">
        {view.name === 'projects' && (
          <ProjectsView onOpen={(id) => setView({ name: 'project', id })} />
        )}
        {view.name === 'templates' && <TemplatesView />}
        {view.name === 'overview' && <OverviewView />}
        {view.name === 'checks' && <SystemCheckView />}
        {view.name === 'project' && (
          <ProjectDetailView projectId={view.id} onBack={() => setView({ name: 'projects' })} />
        )}
      </main>
    </div>
  )
}
