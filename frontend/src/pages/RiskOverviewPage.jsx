import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { RiskLabel } from '../components/Badges'
import { RISK_LEVELS, STATUSES, STATUS_LABELS } from '../api/state'

export default function RiskOverviewPage() {
  const [overview, setOverview] = useState(null)
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [siteRisks, setSiteRisks] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setSiteRisks(null)
    const promises = [api.getRiskOverview(selectedProject || undefined)]
    if (selectedProject) {
      promises.push(api.getProjectSitesRisk(selectedProject).catch(() => null))
    }
    Promise.all(promises)
      .then(([ov, sr]) => {
        setOverview(ov)
        if (sr) setSiteRisks(sr)
      })
      .finally(() => setLoading(false))
  }, [selectedProject])

  if (loading || !overview) return <div>加载中...</div>

  const activeStatuses = STATUSES.filter(s => s !== 'archived')

  return (
    <div>
      <h1 className="page-title">风险概览</h1>

      <div className="filters">
        <div className="form-group" style={{ marginBottom: 0, minWidth: 240 }}>
          <label>项目范围</label>
          <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)}>
            <option value="">全部项目</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.project_name}</option>)}
          </select>
        </div>
      </div>

      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
        统计口径：已排除归档（archived）观察项，归档数据仍可在地点详情页查看。
      </p>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">地点总数</div>
          <div className="value">{overview.total_sites}</div>
        </div>
        <div className="stat-card">
          <div className="label">观察项总数（不含归档）</div>
          <div className="value">{overview.total_findings}</div>
        </div>
        {RISK_LEVELS.map(level => (
          <div key={level} className="stat-card">
            <div className="label"><RiskLabel level={level} /></div>
            <div className="value">{overview.risk_counts[level] || 0}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16 }}>风险等级分布</h3>
        {overview.total_findings > 0 ? (
          <div className="risk-bar" style={{ height: 36 }}>
            {RISK_LEVELS.map(level => {
              const count = overview.risk_counts[level] || 0
              if (count === 0) return null
              const pct = (count / overview.total_findings) * 100
              return (
                <div key={level} className={`risk-${level}`} style={{ width: `${pct}%`, fontSize: 14 }}>
                  {count > 0 && `${count}`}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="empty-state">暂无观察项数据</div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16 }}>状态分布</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
          {activeStatuses.map(s => (
            <div key={s} style={{ padding: 12, border: '1px solid var(--border)', borderRadius: 8, textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{overview.status_counts[s] || 0}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                <span className={`badge badge-${s}`}>{STATUS_LABELS[s]}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {siteRisks && siteRisks.sites && siteRisks.sites.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
          <h3 style={{ padding: '16px 20px 0' }}>各地点风险明细</h3>
          <table style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>地点</th>
                <th>区域</th>
                <th>观察项</th>
                <th>未复核</th>
                <th>已驳回</th>
                <th>最高风险</th>
                <th>最近更新</th>
              </tr>
            </thead>
            <tbody>
              {siteRisks.sites.map(s => (
                <tr key={s.site_id}>
                  <td><Link to={`/sites/${s.site_id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>{s.site_name}</Link></td>
                  <td>{s.region || '-'}</td>
                  <td>{s.total_findings}</td>
                  <td>{s.unreviewed_count > 0 ? <span style={{ color: 'var(--warning)', fontWeight: 500 }}>{s.unreviewed_count}</span> : 0}</td>
                  <td>{s.rejected_count > 0 ? <span style={{ color: 'var(--danger)', fontWeight: 500 }}>{s.rejected_count}</span> : 0}</td>
                  <td>{s.max_risk_level !== 'none' ? <RiskLabel level={s.max_risk_level} /> : '—'}</td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {s.last_updated ? s.last_updated.replace('T', ' ').slice(0, 16) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedProject && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>
            <Link to={`/projects/${selectedProject}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>
              查看项目详情 →
            </Link>
          </h3>
        </div>
      )}
    </div>
  )
}
