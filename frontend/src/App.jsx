import { useState } from 'react';
import ProjectListPage from './pages/ProjectListPage.jsx';
import ProjectCreatePage from './pages/ProjectCreatePage.jsx';
import TemplateManagePage from './pages/TemplateManagePage.jsx';
import ProjectDetailPage from './pages/ProjectDetailPage.jsx';
import SiteDetailPage from './pages/SiteDetailPage.jsx';
import RiskOverviewPage from './pages/RiskOverviewPage.jsx';
import SystemCheckPage from './pages/SystemCheckPage.jsx';

export default function App() {
  // view: 'projects' | 'create' | 'templates' | 'checks' | 'project' | 'site'
  const [view, setView] = useState('projects');
  const [projectId, setProjectId] = useState(null);
  const [siteId, setSiteId] = useState(null);
  const [projectSubView, setProjectSubView] = useState('sites');

  const goProjects = () => {
    setView('projects');
    setProjectId(null);
    setSiteId(null);
  };

  const openProject = (id) => {
    setProjectId(id);
    setSiteId(null);
    setProjectSubView('sites');
    setView('project');
  };

  const openSite = (id) => {
    setSiteId(id);
    setView('site');
  };

  const renderMain = () => {
    switch (view) {
      case 'create':
        return (
          <ProjectCreatePage
            onCreated={(project) => openProject(project.id)}
            onCancel={goProjects}
          />
        );
      case 'templates':
        return <TemplateManagePage />;
      case 'checks':
        return <SystemCheckPage />;
      case 'project':
        return projectSubView === 'risk' ? (
          <RiskOverviewPage projectId={projectId} />
        ) : (
          <ProjectDetailPage projectId={projectId} onOpenSite={openSite} />
        );
      case 'site':
        return (
          <SiteDetailPage
            siteId={siteId}
            onBack={() => {
              setSiteId(null);
              setView('project');
            }}
          />
        );
      case 'projects':
      default:
        return (
          <ProjectListPage
            onOpenProject={openProject}
            onCreateProject={() => setView('create')}
          />
        );
    }
  };

  const inProject = view === 'project' || view === 'site';

  return (
    <>
      <nav className="top-nav">
        <span className="brand">现场踏勘简报协作系统</span>
        <button
          className={view === 'projects' || inProject ? 'active' : ''}
          onClick={goProjects}
        >
          项目列表
        </button>
        <button
          className={view === 'create' ? 'active' : ''}
          onClick={() => setView('create')}
        >
          新建项目
        </button>
        <button
          className={view === 'templates' ? 'active' : ''}
          onClick={() => setView('templates')}
        >
          模板管理
        </button>
        <button
          className={view === 'checks' ? 'active' : ''}
          onClick={() => setView('checks')}
        >
          系统检查
        </button>
      </nav>

      {inProject && (
        <div className="sub-nav">
          <span className="sub-title">项目 #{projectId}</span>
          <button
            className={projectSubView === 'sites' ? 'active' : ''}
            onClick={() => {
              setProjectSubView('sites');
              setView('project');
            }}
          >
            地点
          </button>
          <button
            className={projectSubView === 'risk' ? 'active' : ''}
            onClick={() => {
              setProjectSubView('risk');
              setView('project');
            }}
          >
            风险概览
          </button>
        </div>
      )}

      <main className="main">{renderMain()}</main>
    </>
  );
}
