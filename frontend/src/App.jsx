import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import ProjectListPage from './pages/ProjectListPage'
import ProjectCreatePage from './pages/ProjectCreatePage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import TemplateManagePage from './pages/TemplateManagePage'
import SiteDetailPage from './pages/SiteDetailPage'
import RiskOverviewPage from './pages/RiskOverviewPage'
import SystemCheckPage from './pages/SystemCheckPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <header className="app-header">
          <h1>现场踏勘简报</h1>
          <nav className="app-nav">
            <NavLink to="/projects" className={({ isActive }) => isActive ? 'active' : ''}>项目</NavLink>
            <NavLink to="/templates" className={({ isActive }) => isActive ? 'active' : ''}>模板</NavLink>
            <NavLink to="/overview" className={({ isActive }) => isActive ? 'active' : ''}>风险概览</NavLink>
            <NavLink to="/system-check" className={({ isActive }) => isActive ? 'active' : ''}>系统检查</NavLink>
          </nav>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Navigate to="/projects" replace />} />
            <Route path="/projects" element={<ProjectListPage />} />
            <Route path="/projects/new" element={<ProjectCreatePage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/sites/:id" element={<SiteDetailPage />} />
            <Route path="/templates" element={<TemplateManagePage />} />
            <Route path="/overview" element={<RiskOverviewPage />} />
            <Route path="/system-check" element={<SystemCheckPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
