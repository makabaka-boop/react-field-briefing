import { Link, Route, Routes } from 'react-router-dom';
import ProjectList from './pages/ProjectList.jsx';
import ProjectCreate from './pages/ProjectCreate.jsx';
import TemplateManager from './pages/TemplateManager.jsx';
import TemplateResult from './pages/TemplateResult.jsx';
import SiteDetail from './pages/SiteDetail.jsx';
import ProjectDetail from './pages/ProjectDetail.jsx';
import RiskOverview from './pages/RiskOverview.jsx';
import SystemCheck from './pages/SystemCheck.jsx';

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>现场踏勘简报协作系统</h1>
        <nav>
          <Link to="/">项目列表</Link>
          <Link to="/projects/new">新建项目</Link>
          <Link to="/templates">模板管理</Link>
          <Link to="/risk">风险概览</Link>
          <Link to="/system-check">系统检查</Link>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<ProjectList />} />
          <Route path="/projects/new" element={<ProjectCreate />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/sites/:siteId" element={<SiteDetail />} />
          <Route path="/templates" element={<TemplateManager />} />
          <Route path="/templates/result/:projectId" element={<TemplateResult />} />
          <Route path="/risk" element={<RiskOverview />} />
          <Route path="/system-check" element={<SystemCheck />} />
        </Routes>
      </main>
    </div>
  );
}
