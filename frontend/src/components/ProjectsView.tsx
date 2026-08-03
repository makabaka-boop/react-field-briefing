import { useEffect, useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { ProjectListItem, Status } from '../types'
import { ALL_RISK_LEVELS, ALL_STATUSES, PROJECT_TRANSITIONS } from '../types'
import ProjectCreateForm from './ProjectCreateForm'
import TemplateProjectWizard from './TemplateProjectWizard'

export default function ProjectsView({ onOpen }: { onOpen: (id: number) => void }) {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [statusFilter, setStatusFilter] = useState<Status | ''>('')
  const [regionFilter, setRegionFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [showWizard, setShowWizard] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    try {
      const data = await api.listProjects({
        status: statusFilter || undefined,
        region: regionFilter || undefined,
        highest_risk: riskFilter || undefined,
      })
      setProjects(data)
    } catch (e) {
      setError((e as ApiClientError).message)
    }
  }

  useEffect(() => { load() }, [statusFilter, regionFilter, riskFilter])

  async function changeStatus(p: ProjectListItem, newStatus: Status) {
    try {
      await api.updateProjectStatus(p.id, newStatus, p.owner_name)
      load()
    } catch (e) {
      setError((e as ApiClientError).message)
    }
  }

  function resetFilters() {
    setStatusFilter('')
    setRegionFilter('')
    setRiskFilter('')
  }

  return (
    <div>
      <div className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Projects</h2>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn secondary" onClick={() => setShowWizard((v) => !v)}>
              {showWizard ? 'Cancel' : 'From Template'}
            </button>
            <button className="btn" onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? 'Cancel' : '+ New Project'}
            </button>
          </div>
        </div>
      </div>

      {showWizard && (
        <TemplateProjectWizard
          onCreated={(id) => { setShowWizard(false); onOpen(id) }}
          onCancel={() => setShowWizard(false)}
        />
      )}

      {showCreate && (
        <ProjectCreateForm
          onCreated={() => { setShowCreate(false); load() }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {error && <div className="error">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <div className="form-group" style={{ minWidth: 160 }}>
            <label>Status</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as Status | '')}>
              <option value="">All</option>
              {ALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ minWidth: 160 }}>
            <label>Region</label>
            <input value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)} placeholder="e.g. North" />
          </div>
          <div className="form-group" style={{ minWidth: 180 }}>
            <label>Highest risk ≥</label>
            <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
              <option value="">Any</option>
              {ALL_RISK_LEVELS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ alignSelf: 'end' }}>
            <button className="btn secondary" onClick={resetFilters}>Reset</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Owner</th>
              <th>Sites</th>
              <th>Status</th>
              <th>Findings</th>
              <th>Unreviewed</th>
              <th>Rejected</th>
              <th>Highest Risk</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td><span className="clickable" onClick={() => onOpen(p.id)}>{p.project_code}</span></td>
                <td>{p.project_name}</td>
                <td>{p.owner_name}</td>
                <td>{p.site_count}</td>
                <td><span className={`badge ${p.status}`}>{p.status}</span></td>
                <td>{p.total_findings}</td>
                <td>{p.unreviewed_count}</td>
                <td>{p.rejected_count}</td>
                <td>
                  {p.highest_risk === 'none'
                    ? <span className="muted">—</span>
                    : <span className={`badge ${p.highest_risk}`}>{p.highest_risk}</span>}
                </td>
                <td className="muted">
                  {p.last_updated_at ? new Date(p.last_updated_at).toLocaleString() : '—'}
                </td>
                <td>
                  <select
                    value=""
                    onChange={(e) => { if (e.target.value) changeStatus(p, e.target.value as Status); e.target.value = '' }}
                    style={{ width: 'auto', display: 'inline-block', marginRight: 8 }}
                  >
                    <option value="">Status…</option>
                    {PROJECT_TRANSITIONS[p.status].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <button className="btn small secondary" onClick={() => onOpen(p.id)}>Open</button>
                </td>
              </tr>
            ))}
            {projects.length === 0 && (
              <tr><td colSpan={11} className="muted" style={{ textAlign: 'center' }}>No projects match the filters.</td></tr>
            )}
          </tbody>
        </table>
        <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
          Risk statistics exclude archived findings. Archived history remains available on each site’s timeline.
        </p>
      </div>
    </div>
  )
}
