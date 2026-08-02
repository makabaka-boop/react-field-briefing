import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client.js';
import { nextStatuses, STATUS_LABELS } from '../state/statusMachine.js';
import { RiskBadge, StatusBadge } from '../components/Badge.jsx';

// Project detail: header with status transitions, site creation, and a
// per-site risk breakdown that links into each SiteDetail page.
export default function ProjectDetail() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [risk, setRisk] = useState([]);
  const [error, setError] = useState('');
  const [newSite, setNewSite] = useState({ site_code: '', site_name: '', address_text: '', region: '' });

  async function load() {
    setError('');
    try {
      const p = await api.getProject(projectId);
      setProject(p);
      const r = await api.projectSiteRisk(projectId);
      setRisk(r.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '加载失败');
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function transition(target) {
    setError('');
    try {
      await api.transitionProject(projectId, { target_status: target });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '流转失败');
    }
  }

  async function addSite(e) {
    e.preventDefault();
    setError('');
    try {
      await api.createSite({ ...newSite, project_id: Number(projectId) });
      setNewSite({ site_code: '', site_name: '', address_text: '', region: '' });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '新增地点失败');
    }
  }

  if (!project) {
    return <div className="card">{error ? <div className="form-error">{error}</div> : '加载中…'}</div>;
  }

  const setSite = (k) => (e) => setNewSite({ ...newSite, [k]: e.target.value });

  return (
    <div>
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="card">
        <h2>{project.project_name} <span className="muted">({project.project_code})</span></h2>
        <p>负责人：{project.owner_name} · 状态：<StatusBadge status={project.status} /></p>
        <div className="row" style={{ gap: 8 }}>
          {nextStatuses(project.status).map((s) => (
            <button key={s} className="secondary" onClick={() => transition(s)}>
              → {STATUS_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>按地点风险</h3>
        <table>
          <thead>
            <tr>
              <th>地点</th><th>区域</th><th>观察项数</th><th>未复核</th>
              <th>已驳回</th><th>最高风险</th><th>最近更新</th><th></th>
            </tr>
          </thead>
          <tbody>
            {risk.map((s) => (
              <tr key={s.site_id}>
                <td>{s.site_name} <span className="muted">({s.site_code})</span></td>
                <td>{s.region || '—'}</td>
                <td>{s.finding_count}</td>
                <td>{s.unreviewed_count}</td>
                <td>{s.rejected_count}</td>
                <td><RiskBadge level={s.highest_risk_level} /></td>
                <td className="muted">{s.last_updated_at || '—'}</td>
                <td><Link to={`/sites/${s.site_id}`}>进入</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!risk.length && <p className="muted">尚无地点。</p>}
      </div>

      <form className="card" onSubmit={addSite}>
        <h3>新增地点</h3>
        <div className="row">
          <div className="col field"><label>site_code</label><input value={newSite.site_code} onChange={setSite('site_code')} /></div>
          <div className="col field"><label>site_name</label><input value={newSite.site_name} onChange={setSite('site_name')} /></div>
          <div className="col field"><label>region</label><input value={newSite.region} onChange={setSite('region')} /></div>
          <div className="col field"><label>address_text</label><input value={newSite.address_text} onChange={setSite('address_text')} /></div>
        </div>
        <button type="submit">新增地点</button>
      </form>
    </div>
  );
}
