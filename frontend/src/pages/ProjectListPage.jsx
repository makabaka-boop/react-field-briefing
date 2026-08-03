import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { StatusBadge, RiskLabel } from '../components/Badges'
import { STATUSES, STATUS_LABELS, RISK_LEVELS, RISK_LABELS, getAvailableTransitions } from '../api/state'

export default function ProjectListPage() {
  const [projects, setProjects] = useState([])
  const [filters, setFilters] = useState({ status: '', region: '', max_risk_level: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { loadProjects() }, [filters])

  async function loadProjects() {
    setLoading(true)
    try {
      const params = {}
      if (filters.status) params.status = filters.status
      if (filters.region) params.region = filters.region
      if (filters.max_risk_level) params.max_risk_level = filters.max_risk_level
      const data = await api.listProjects(params)
      setProjects(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleTransition(p, target) {
    try {
      await api.transitionProject(p.id, target)
      await loadProjects()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>项目列表</h1>
        <Link to="/projects/new" className="btn btn-primary">+ 新建项目</Link>
      </div>

      {error && <div className="error-msg">{error}</div>}

      <div className="filters">
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label>项目状态</label>
          <select value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })}>
            <option value="">全部状态</option>
            {STATUSES.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
          </select>
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label>区域筛选</label>
          <input
            value={filters.region}
            onChange={e => setFilters({ ...filters, region: e.target.value })}
            placeholder="输入区域名称"
          />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label>最高风险等级</label>
          <select value={filters.max_risk_level} onChange={e => setFilters({ ...filters, max_risk_level: e.target.value })}>
            <option value="">全部</option>
            {RISK_LEVELS.map(r => <option key={r} value={r}>{RISK_LABELS[r]}</option>)}
            <option value="none">无观察项</option>
          </select>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center' }}>加载中...</div>
        ) : projects.length === 0 ? (
          <div className="empty-state">暂无项目</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>项目编号</th>
                <th>项目名称</th>
                <th>负责人</th>
                <th>状态</th>
                <th>观察项</th>
                <th>未复核</th>
                <th>已驳回</th>
                <th>最高风险</th>
                <th>最近更新</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {projects.map(p => {
                const rs = p.risk_summary || {}
                return (
                  <tr key={p.id}>
                    <td><Link to={`/projects/${p.id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>{p.project_code}</Link></td>
                    <td>{p.project_name}</td>
                    <td>{p.owner_name}</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td>{rs.total_findings ?? 0}</td>
                    <td>
                      {rs.unreviewed_count > 0
                        ? <span style={{ color: 'var(--warning)', fontWeight: 500 }}>{rs.unreviewed_count}</span>
                        : 0}
                    </td>
                    <td>
                      {rs.rejected_count > 0
                        ? <span style={{ color: 'var(--danger)', fontWeight: 500 }}>{rs.rejected_count}</span>
                        : 0}
                    </td>
                    <td>
                      {rs.max_risk_level && rs.max_risk_level !== 'none'
                        ? <RiskLabel level={rs.max_risk_level} />
                        : <span style={{ color: 'var(--text-secondary)' }}>—</span>}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {rs.last_updated ? rs.last_updated.replace('T', ' ').slice(0, 16) : '—'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        <Link to={`/projects/${p.id}`} className="btn btn-sm">查看</Link>
                        {getAvailableTransitions(p.status, true).map(t => (
                          <button key={t} className="btn btn-sm" onClick={() => handleTransition(p, t)}>
                            → {STATUS_LABELS[t]}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
