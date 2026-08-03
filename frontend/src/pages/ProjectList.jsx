import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { RISK_LABELS, RISK_LEVELS, STATUS_LABELS, STATUSES } from '../state/statusMachine.js';
import { RiskBadge, StatusBadge } from '../components/Badge.jsx';

export default function ProjectList() {
  const [items, setItems] = useState([]);
  const [filters, setFilters] = useState({ status: '', region: '', min_risk_level: '' });
  const [error, setError] = useState('');

  async function load() {
    setError('');
    try {
      const res = await api.listProjects(filters);
      setItems(res.items);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.status, filters.region, filters.min_risk_level]);

  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });

  return (
    <div>
      <div className="card">
        <h2>项目列表</h2>
        <div className="filters">
          <div className="field">
            <label>状态</label>
            <select value={filters.status} onChange={set('status')}>
              <option value="">全部</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>{STATUS_LABELS[s]}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>区域</label>
            <input value={filters.region} onChange={set('region')} placeholder="按地点区域筛选" />
          </div>
          <div className="field">
            <label>最低最高风险</label>
            <select value={filters.min_risk_level} onChange={set('min_risk_level')}>
              <option value="">全部</option>
              {RISK_LEVELS.map((r) => (
                <option key={r} value={r}>{RISK_LABELS[r]}</option>
              ))}
            </select>
          </div>
        </div>
        {error && <div className="form-error">{error}</div>}
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>名称</th>
              <th>负责人</th>
              <th>状态</th>
              <th>地点数</th>
              <th>在办观察项</th>
              <th>未复核</th>
              <th>已驳回</th>
              <th>最高风险</th>
              <th>最近更新</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => {
              const rs = p.risk_summary || {};
              return (
                <tr key={p.id}>
                  <td>{p.project_code}</td>
                  <td>{p.project_name}</td>
                  <td>{p.owner_name}</td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>{p.site_count}</td>
                  <td>{rs.open_finding_count ?? 0}</td>
                  <td>{rs.unreviewed_count ?? 0}</td>
                  <td>{rs.rejected_count ?? 0}</td>
                  <td><RiskBadge level={p.highest_risk_level} /></td>
                  <td className="muted">{rs.last_updated_at || '—'}</td>
                  <td><Link to={`/projects/${p.id}`}>查看</Link></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!items.length && <p className="muted">暂无项目。</p>}
      </div>
    </div>
  );
}
