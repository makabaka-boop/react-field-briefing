import { useCallback, useEffect, useState } from 'react';
import { listProjects } from '../api/client.js';
import { RISK_LEVELS, STATUS_LIST, riskLabel, statusLabel } from '../stateMachine.js';

function formatTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN');
}

export default function ProjectListPage({ onOpenProject, onCreateProject }) {
  const [projects, setProjects] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [maxRiskFilter, setMaxRiskFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listProjects({
        status: statusFilter || undefined,
        region: regionFilter.trim() || undefined,
        max_risk_level: maxRiskFilter || undefined,
      });
      setProjects(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, regionFilter, maxRiskFilter]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}
      <div className="card">
        <div className="card-title-row">
          <h3>项目列表</h3>
          <button className="btn btn-primary" onClick={onCreateProject}>
            新建项目
          </button>
        </div>
        <div className="filter-bar">
          <div className="form-row">
            <label htmlFor="project-status-filter">项目状态</label>
            <select
              id="project-status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">全部</option>
              {STATUS_LIST.map((status) => (
                <option key={status} value={status}>
                  {statusLabel(status)}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="project-region-filter">区域</label>
            <input
              id="project-region-filter"
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              placeholder="如：华东"
            />
          </div>
          <div className="form-row">
            <label htmlFor="project-max-risk-filter">最高风险等级</label>
            <select
              id="project-max-risk-filter"
              value={maxRiskFilter}
              onChange={(e) => setMaxRiskFilter(e.target.value)}
            >
              <option value="">全部</option>
              {RISK_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {riskLabel(level)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {loading ? (
          <div className="loading">加载中…</div>
        ) : projects.length === 0 ? (
          <div className="empty-state">暂无项目，点击右上角"新建项目"开始</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>项目编号</th>
                <th>项目名称</th>
                <th>负责人</th>
                <th>状态</th>
                <th>风险摘要（观察项/未复核/已驳回）</th>
                <th>最高风险</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => {
                const summary = project.risk_summary || {};
                return (
                  <tr key={project.id}>
                    <td>{project.project_code}</td>
                    <td>{project.project_name}</td>
                    <td>{project.owner_name}</td>
                    <td>
                      <span className={`badge badge-status-${project.status}`}>
                        {statusLabel(project.status)}
                      </span>
                    </td>
                    <td>
                      {summary.total_findings ?? 0} / {summary.unreviewed_count ?? 0} /{' '}
                      {summary.rejected_count ?? 0}
                    </td>
                    <td>
                      {summary.max_risk_level ? (
                        <span
                          className={`badge badge-risk-${summary.max_risk_level}`}
                        >
                          {riskLabel(summary.max_risk_level)}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>{formatTime(project.created_at)}</td>
                    <td>
                      <button
                        className="btn btn-sm"
                        onClick={() => onOpenProject(project.id)}
                      >
                        进入项目
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
