import React, { useCallback, useEffect, useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type {
  Finding, ProjectDetail, Review, RiskLevel, Site, SiteRiskItem, Status, TimelineEvent,
} from '../types'
import { ALL_RISK_LEVELS, ALL_STATUSES, FINDING_TRANSITIONS } from '../types'
import FindingForm from './FindingForm'
import ReviewSidebar from './ReviewSidebar'
import SiteDetail from './SiteDetail'
import SiteTimeline from './SiteTimeline'
import Timeline from './Timeline'

export default function ProjectDetailView({ projectId, onBack }: { projectId: number; onBack: () => void }) {
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [sites, setSites] = useState<Site[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [siteRisks, setSiteRisks] = useState<SiteRiskItem[]>([])
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])

  const [regionFilter, setRegionFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState<Status | ''>('')
  const [riskFilter, setRiskFilter] = useState<RiskLevel | ''>('')
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null)
  const [showFindingForm, setShowFindingForm] = useState(false)
  const [selectedFindingId, setSelectedFindingId] = useState<number | null>(null)
  const [reviews, setReviews] = useState<Review[]>([])
  const [timelineSiteId, setTimelineSiteId] = useState<number | null>(null)
  const [tab, setTab] = useState<'findings' | 'timeline' | 'risks'>('findings')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([
        api.getProject(projectId),
        api.listSites({ project_id: projectId }),
      ])
      setProject(p)
      setSites(s)
      const [f, risks, tl] = await Promise.all([
        api.listFindings({ project_id: projectId, status: statusFilter || undefined, risk_level: riskFilter || undefined }),
        api.siteRisks(projectId),
        api.timeline(projectId),
      ])
      setFindings(f)
      setSiteRisks(risks)
      setTimeline(tl)
    } catch (e) {
      setError((e as ApiClientError).message)
    }
  }, [projectId, statusFilter, riskFilter])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (selectedFindingId === null) { setReviews([]); return }
    api.listReviews(selectedFindingId).then(setReviews)
  }, [selectedFindingId])

  const regions = Array.from(new Set(sites.map((s) => s.region).filter(Boolean)))
  const filteredSites = regionFilter ? sites.filter((s) => s.region === regionFilter) : sites
  const visibleFindings = findings.filter((f) => {
    const siteOk = selectedSiteId ? f.site_id === selectedSiteId : true
    return siteOk
  })

  async function changeFindingStatus(id: number, status: Status) {
    try {
      await api.updateFindingStatus(id, status, project?.owner_name || 'analyst')
      load()
    } catch (e) {
      setError((e as ApiClientError).message)
    }
  }

  async function submitFinding(id: number, actor: string) {
    try {
      await api.submitFinding(id, actor || project?.owner_name || 'analyst')
      load()
    } catch (e) {
      setError((e as ApiClientError).message)
    }
  }

  if (!project) return <div className="panel">Loading…</div>

  return (
    <div>
      <div className="panel">
        <button className="btn ghost" onClick={onBack} style={{ paddingLeft: 0 }}>← Back to projects</button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginTop: 8 }}>
          <div>
            <h2 style={{ margin: 0 }}>{project.project_name}</h2>
            <div className="muted">
              <span className="pill">{project.project_code}</span>
              Owner: {project.owner_name} · Created {new Date(project.created_at).toLocaleString()}
            </div>
          </div>
          <span className={`badge ${project.status}`}>{project.status}</span>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="panel">
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button className={`btn small ${tab === 'findings' ? '' : 'secondary'}`} onClick={() => setTab('findings')}>Findings & Sites</button>
          <button className={`btn small ${tab === 'risks' ? '' : 'secondary'}`} onClick={() => setTab('risks')}>Site Risk</button>
          <button className={`btn small ${tab === 'timeline' ? '' : 'secondary'}`} onClick={() => setTab('timeline')}>Timeline</button>
        </div>

        {tab === 'findings' && (
          <div className="layout-2col">
            <div>
              <div className="toolbar">
                <div className="form-group">
                  <label>Region</label>
                  <select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)}>
                    <option value="">All regions</option>
                    {regions.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Finding Status</label>
                  <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as Status | '')}>
                    <option value="">All statuses</option>
                    {ALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Risk Level</label>
                  <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value as RiskLevel | '')}>
                    <option value="">All risks</option>
                    {ALL_RISK_LEVELS.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>&nbsp;</label>
                  <button className="btn" onClick={() => setShowFindingForm((v) => !v)}>
                    {showFindingForm ? 'Cancel' : '+ New Finding'}
                  </button>
                </div>
              </div>

              {showFindingForm && (
                <FindingForm
                  sites={filteredSites}
                  defaultSiteId={selectedSiteId || filteredSites[0]?.id}
                  onSaved={() => { setShowFindingForm(false); load() }}
                  onCancel={() => setShowFindingForm(false)}
                />
              )}

              <h3>Sites ({filteredSites.length})</h3>
              <table>
                <thead><tr><th>Code</th><th>Name</th><th>Region</th><th>Address</th><th></th></tr></thead>
                <tbody>
                  {filteredSites.map((s) => (
                    <React.Fragment key={s.id}>
                      <tr style={{ background: selectedSiteId === s.id ? '#eff6ff' : undefined }}>
                        <td>{s.site_code}</td>
                        <td>{s.site_name}</td>
                        <td>{s.region || '—'}</td>
                        <td className="muted">{s.address_text || '—'}</td>
                        <td>
                          <button className="btn small secondary" onClick={() => setSelectedSiteId(selectedSiteId === s.id ? null : s.id)}>
                            {selectedSiteId === s.id ? 'Hide findings' : 'View findings'}
                          </button>
                          <button
                            className="btn small secondary"
                            style={{ marginLeft: 6 }}
                            onClick={() => setTimelineSiteId(timelineSiteId === s.id ? null : s.id)}
                          >
                            {timelineSiteId === s.id ? 'Hide timeline' : 'Timeline'}
                          </button>
                          <SiteDetail siteId={s.id} onChanged={load} />
                        </td>
                      </tr>
                      {timelineSiteId === s.id && (
                        <tr>
                          <td colSpan={5}>
                            <strong>Site #{s.id} observation timeline</strong>
                            <SiteTimeline siteId={s.id} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>

              <h3 style={{ marginTop: 24 }}>
                Findings {selectedSiteId ? `for site #${selectedSiteId}` : '(all visible sites)'} — {visibleFindings.length}
              </h3>
              <table>
                <thead>
                  <tr><th>ID</th><th>Site</th><th>Category</th><th>Risk</th><th>Status</th><th>Reporter</th><th>Reported At</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {visibleFindings.map((f) => {
                    const site = sites.find((s) => s.id === f.site_id)
                    return (
                      <tr key={f.id}>
                        <td>#{f.id}</td>
                        <td>{site?.site_code}</td>
                        <td>{f.category}</td>
                        <td><span className={`badge ${f.risk_level}`}>{f.risk_level}</span></td>
                        <td><span className={`badge ${f.finding_status}`}>{f.finding_status}</span></td>
                        <td>{f.reported_by || '—'}</td>
                        <td className="muted">{new Date(f.reported_at).toLocaleString()}</td>
                        <td>
                          {f.finding_status === 'draft' && (
                            <button className="btn small" onClick={() => submitFinding(f.id, f.reported_by || 'analyst')}>Submit</button>
                          )}
                          <select
                            value=""
                            onChange={(e) => { if (e.target.value) changeFindingStatus(f.id, e.target.value as Status); e.target.value = '' }}
                            style={{ width: 'auto', display: 'inline-block', marginLeft: 6 }}
                          >
                            <option value="">Status…</option>
                            {FINDING_TRANSITIONS[f.finding_status].map((s) => <option key={s} value={s}>{s}</option>)}
                          </select>
                          <button className="btn small secondary" onClick={() => setSelectedFindingId(selectedFindingId === f.id ? null : f.id)}>
                            {selectedFindingId === f.id ? 'Close' : 'Review'}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                  {visibleFindings.length === 0 && (
                    <tr><td colSpan={8} className="muted" style={{ textAlign: 'center' }}>No findings match the filters.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <ReviewSidebar
              findingId={selectedFindingId}
              reviews={reviews}
              onReviewed={() => { load(); if (selectedFindingId) api.listReviews(selectedFindingId).then(setReviews) }}
            />
          </div>
        )}

        {tab === 'risks' && (
          <table>
            <thead><tr><th>Site Code</th><th>Name</th><th>Region</th><th>Total</th><th>Low</th><th>Medium</th><th>High</th><th>Critical</th><th>Highest</th></tr></thead>
            <tbody>
              {siteRisks.map((r) => (
                <tr key={r.site_id}>
                  <td>{r.site_code}</td>
                  <td>{r.site_name}</td>
                  <td>{r.region || '—'}</td>
                  <td>{r.total_findings}</td>
                  <td>{r.by_risk.low}</td>
                  <td>{r.by_risk.medium}</td>
                  <td>{r.by_risk.high}</td>
                  <td>{r.by_risk.critical}</td>
                  <td><span className={`badge ${r.highest_risk}`}>{r.highest_risk}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === 'timeline' && <Timeline events={timeline} />}
      </div>
    </div>
  )
}
