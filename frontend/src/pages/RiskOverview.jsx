import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { RISK_COLORS, RISK_LABELS, RISK_LEVELS, STATUS_LABELS } from '../state/statusMachine.js';

// Aggregate risk snapshot for review meetings. Optionally scoped to a
// project; archived findings are excluded server-side.
export default function RiskOverview() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState('');
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    api.listProjects().then((r) => setProjects(r.items)).catch(() => {});
  }, []);

  useEffect(() => {
    api.riskOverview(projectId ? { project_id: projectId } : {})
      .then(setOverview)
      .catch(() => setOverview(null));
  }, [projectId]);

  return (
    <div>
      <div className="card">
        <h2>风险概览</h2>
        <div className="field" style={{ maxWidth: 320 }}>
          <label>项目范围</label>
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">全部项目</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.project_name}</option>
            ))}
          </select>
        </div>
      </div>

      {overview && (
        <>
          <div className="card">
            <h3>未归档观察项总数：{overview.open_findings_total}</h3>
            <div className="overview-grid">
              {RISK_LEVELS.map((r) => (
                <div className="stat" key={r} style={{ borderTopColor: RISK_COLORS[r] }}>
                  <div className="num" style={{ color: RISK_COLORS[r] }}>
                    {overview.by_risk_level[r] || 0}
                  </div>
                  <div className="lbl">{RISK_LABELS[r]}风险</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>按状态分布</h3>
            <div className="overview-grid">
              {Object.keys(STATUS_LABELS).map((s) => (
                <div className="stat" key={s}>
                  <div className="num">{overview.by_status[s] || 0}</div>
                  <div className="lbl">{STATUS_LABELS[s]}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
