import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { StatusBadge, RiskLabel } from '../components/Badges'
import RiskFilters from '../components/RiskFilters'
import FindingTable from '../components/FindingTable'
import FindingForm from '../components/FindingForm'
import ReviewSidebar from '../components/ReviewSidebar'
import Timeline from '../components/Timeline'
import { RISK_LEVELS } from '../api/state'

export default function ProjectDetailPage() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [sites, setSites] = useState([])
  const [findings, setFindings] = useState([])
  const [sitesRisk, setSitesRisk] = useState([])
  const [tab, setTab] = useState('sites')
  const [filters, setFilters] = useState({})
  const [showFindingForm, setShowFindingForm] = useState(false)
  const [editingFinding, setEditingFinding] = useState(null)
  const [selectedSiteForFinding, setSelectedSiteForFinding] = useState(null)
  const [reviewFindingId, setReviewFindingId] = useState(null)
  const [timelineFindingId, setTimelineFindingId] = useState(null)
  const [newSite, setNewSite] = useState({ site_code: '', site_name: '', address_text: '', region: '' })
  const [showSiteForm, setShowSiteForm] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { loadAll() }, [id])
  useEffect(() => { loadFindings() }, [id, filters])

  async function loadAll() {
    try {
      const [p, s, sr] = await Promise.all([
        api.getProject(id),
        api.listSites({ project_id: id }),
        api.getProjectSitesRisk(id),
      ])
      setProject(p)
      setSites(s)
      setSitesRisk(sr.sites || [])
      loadFindings()
    } catch (e) {
      setError(e.message)
    }
  }

  async function loadFindings() {
    try {
      const params = { project_id: id }
      if (filters.finding_status) params.finding_status = filters.finding_status
      if (filters.risk_level) params.risk_level = filters.risk_level
      const data = await api.listFindings(params)
      let filtered = data
      if (filters.region) {
        const regionSiteIds = sites.filter(s => s.region.includes(filters.region)).map(s => s.id)
        filtered = filtered.filter(f => regionSiteIds.includes(f.site_id))
      }
      setFindings(filtered)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleAddSite(e) {
    e.preventDefault()
    try {
      await api.createSite({ ...newSite, project_id: parseInt(id) })
      setNewSite({ site_code: '', site_name: '', address_text: '', region: '' })
      setShowSiteForm(false)
      await loadAll()
    } catch (e) {
      setError(e.message)
    }
  }

  function handleNewFinding(site) {
    setEditingFinding(null)
    setSelectedSiteForFinding(site)
    setShowFindingForm(true)
  }

  function handleEditFinding(f) {
    setEditingFinding(f)
    setSelectedSiteForFinding(null)
    setShowFindingForm(true)
  }

  async function handleFindingTransition(f, target) {
    try {
      await api.transitionFinding(f.id, target)
      await loadFindings()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDeleteSite(siteId) {
    if (!confirm('确定删除此地点？相关观察项也会被删除。')) return
    try {
      await api.deleteSite(siteId)
      await loadAll()
    } catch (e) {
      setError(e.message)
    }
  }

  if (!project) return <div>加载中...</div>

  return (
    <div>
      <Link to="/projects" className="back-link">← 返回项目列表</Link>

      {error && <div className="error-msg">{error}</div>}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: 22 }}>{project.project_name}</h1>
            <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>
              编号：{project.project_code} · 负责人：{project.owner_name} · 创建：{project.created_at}
            </div>
          </div>
          <StatusBadge status={project.status} />
        </div>
      </div>

      <div className="tabs">
        <div className={`tab ${tab === 'sites' ? 'active' : ''}`} onClick={() => setTab('sites')}>地点列表</div>
        <div className={`tab ${tab === 'findings' ? 'active' : ''}`} onClick={() => setTab('findings')}>观察项</div>
        <div className={`tab ${tab === 'risk' ? 'active' : ''}`} onClick={() => setTab('risk')}>风险分布</div>
      </div>

      {tab === 'sites' && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <button className="btn btn-primary" onClick={() => setShowSiteForm(!showSiteForm)}>
              {showSiteForm ? '取消' : '+ 添加地点'}
            </button>
          </div>

          {showSiteForm && (
            <div className="card">
              <form onSubmit={handleAddSite}>
                <div className="form-row">
                  <div className="form-group">
                    <label>地点编号 *</label>
                    <input value={newSite.site_code} onChange={e => setNewSite({ ...newSite, site_code: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label>地点名称 *</label>
                    <input value={newSite.site_name} onChange={e => setNewSite({ ...newSite, site_name: e.target.value })} required />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>地址</label>
                    <input value={newSite.address_text} onChange={e => setNewSite({ ...newSite, address_text: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>区域</label>
                    <input value={newSite.region} onChange={e => setNewSite({ ...newSite, region: e.target.value })} />
                  </div>
                </div>
                <button type="submit" className="btn btn-primary">保存地点</button>
              </form>
            </div>
          )}

          <div className="card" style={{ padding: 0 }}>
            {sites.length === 0 ? (
              <div className="empty-state">暂无地点</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>地点编号</th>
                    <th>地点名称</th>
                    <th>区域</th>
                    <th>地址</th>
                    <th>风险概览</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {sitesRisk.map(sr => {
                    const site = sites.find(s => s.id === sr.site_id) || sr
                    return (
                      <tr key={sr.site_id}>
                        <td><Link to={`/sites/${sr.site_id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>{sr.site_code}</Link></td>
                        <td>{sr.site_name}</td>
                        <td>{sr.region || '-'}</td>
                        <td>{sr.address_text || '-'}</td>
                        <td>
                          {sr.total_findings > 0 ? (
                            <span>
                              {sr.max_risk_level !== 'none' && <RiskLabel level={sr.max_risk_level} />}
                              <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-secondary)' }}>{sr.total_findings} 项</span>
                            </span>
                          ) : <span style={{ color: 'var(--text-secondary)' }}>无</span>}
                        </td>
                        <td>
                          <button className="btn btn-sm" onClick={() => handleNewFinding(site)}>+ 观察项</button>
                          <button className="btn btn-sm btn-danger" style={{ marginLeft: 4 }} onClick={() => handleDeleteSite(sr.site_id)}>删除</button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {tab === 'findings' && (
        <div>
          <RiskFilters filters={filters} onChange={setFilters} />
          <div className="card" style={{ padding: 0 }}>
            <FindingTable
              findings={findings}
              onEdit={handleEditFinding}
              onReview={f => setReviewFindingId(f.id)}
              onTransition={handleFindingTransition}
              onViewTimeline={f => setTimelineFindingId(f.id)}
              showSite
            />
          </div>
        </div>
      )}

      {tab === 'risk' && (
        <div>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="label">地点总数</div>
              <div className="value">{sites.length}</div>
            </div>
            <div className="stat-card">
              <div className="label">观察项总数（不含归档）</div>
              <div className="value">{sitesRisk.reduce((sum, s) => sum + s.total_findings, 0)}</div>
            </div>
            <div className="stat-card">
              <div className="label">未复核</div>
              <div className="value" style={{ color: 'var(--warning)' }}>
                {sitesRisk.reduce((sum, s) => sum + s.unreviewed_count, 0)}
              </div>
            </div>
            <div className="stat-card">
              <div className="label">已驳回</div>
              <div className="value" style={{ color: 'var(--danger)' }}>
                {sitesRisk.reduce((sum, s) => sum + s.rejected_count, 0)}
              </div>
            </div>
            {RISK_LEVELS.map(level => {
              const count = sitesRisk.reduce((sum, s) => sum + (s.risk_counts[level] || 0), 0)
              return (
                <div key={level} className="stat-card">
                  <div className="label"><RiskLabel level={level} /></div>
                  <div className="value">{count}</div>
                </div>
              )
            })}
          </div>
          <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
            <h3 style={{ padding: '16px 20px 0', marginBottom: 0 }}>各地点风险分布</h3>
            {sitesRisk.filter(s => s.total_findings > 0).length === 0 ? (
              <div className="empty-state">暂无风险数据</div>
            ) : (
              <table style={{ marginTop: 12 }}>
                <thead>
                  <tr>
                    <th>地点</th>
                    <th>区域</th>
                    <th>观察项</th>
                    <th>未复核</th>
                    <th>已驳回</th>
                    <th>最高风险</th>
                    <th>风险分布</th>
                    <th>最近更新</th>
                  </tr>
                </thead>
                <tbody>
                  {sitesRisk.filter(s => s.total_findings > 0).map(s => (
                    <tr key={s.site_id}>
                      <td><Link to={`/sites/${s.site_id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>{s.site_name}</Link></td>
                      <td>{s.region || '-'}</td>
                      <td>{s.total_findings}</td>
                      <td>{s.unreviewed_count > 0 ? <span style={{ color: 'var(--warning)', fontWeight: 500 }}>{s.unreviewed_count}</span> : 0}</td>
                      <td>{s.rejected_count > 0 ? <span style={{ color: 'var(--danger)', fontWeight: 500 }}>{s.rejected_count}</span> : 0}</td>
                      <td>{s.max_risk_level !== 'none' ? <RiskLabel level={s.max_risk_level} /> : '—'}</td>
                      <td style={{ minWidth: 160 }}>
                        <div className="risk-bar" style={{ height: 18 }}>
                          {RISK_LEVELS.map(level => {
                            const count = s.risk_counts[level] || 0
                            if (count === 0) return null
                            const pct = (count / s.total_findings) * 100
                            return <div key={level} className={`risk-${level}`} style={{ width: `${pct}%`, fontSize: 10 }}>{count}</div>
                          })}
                        </div>
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        {s.last_updated ? s.last_updated.replace('T', ' ').slice(0, 16) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {showFindingForm && (
        <div className="sidebar-overlay" onClick={() => setShowFindingForm(false)}>
          <div className="sidebar-panel" onClick={e => e.stopPropagation()}>
            <div className="sidebar-header">
              <h2>{editingFinding ? '编辑观察项' : '新建观察项'}</h2>
              <button className="btn btn-sm" onClick={() => setShowFindingForm(false)}>关闭</button>
            </div>
            <FindingForm
              siteId={selectedSiteForFinding?.id || editingFinding?.site_id}
              finding={editingFinding}
              onSaved={() => { setShowFindingForm(false); loadFindings(); loadAll() }}
              onCancel={() => setShowFindingForm(false)}
            />
          </div>
        </div>
      )}

      {reviewFindingId && (
        <ReviewSidebar
          findingId={reviewFindingId}
          onClose={() => setReviewFindingId(null)}
          onReviewed={() => { loadFindings() }}
        />
      )}

      {timelineFindingId && (
        <div className="sidebar-overlay" onClick={() => setTimelineFindingId(null)}>
          <div className="sidebar-panel" onClick={e => e.stopPropagation()}>
            <div className="sidebar-header">
              <h2>时间线</h2>
              <button className="btn btn-sm" onClick={() => setTimelineFindingId(null)}>关闭</button>
            </div>
            <Timeline findingId={timelineFindingId} />
          </div>
        </div>
      )}
    </div>
  )
}
