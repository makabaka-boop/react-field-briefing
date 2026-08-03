import { useCallback, useEffect, useState } from 'react';
import {
  getProjectRiskSites,
  getProjectRiskSummary,
} from '../api/client.js';
import {
  RISK_LEVELS,
  STATUS_LIST,
  riskLabel,
  statusLabel,
} from '../stateMachine.js';

function formatTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN');
}

export default function RiskOverviewPage({ projectId }) {
  const [summary, setSummary] = useState(null);
  const [riskSites, setRiskSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [summaryData, sitesData] = await Promise.all([
        getProjectRiskSummary(projectId),
        getProjectRiskSites(projectId),
      ]);
      setSummary(summaryData);
      setRiskSites(sitesData || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading">加载中…</div>}

      {summary && (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">地点总数</div>
              <div className="stat-value">{summary.total_sites}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">观察项总数（不含归档）</div>
              <div className="stat-value">{summary.total_findings}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">未复核</div>
              <div className="stat-value">{summary.unreviewed_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">已驳回</div>
              <div className="stat-value">{summary.rejected_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">已归档（不计入统计）</div>
              <div className="stat-value">{summary.archived_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">最近更新时间</div>
              <div className="stat-value" style={{ fontSize: 14 }}>
                {formatTime(summary.last_updated_at)}
              </div>
            </div>
          </div>

          <div className="card">
            <h3>按风险等级统计</h3>
            <div className="stat-grid">
              {RISK_LEVELS.map((level) => (
                <div className="stat-card" key={level}>
                  <div className="stat-label">
                    <span className={`badge badge-risk-${level}`}>
                      {riskLabel(level)}
                    </span>
                  </div>
                  <div className="stat-value">
                    {summary.by_risk_level?.[level] ?? 0}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>按状态统计</h3>
            <div className="stat-grid">
              {STATUS_LIST.map((status) => (
                <div className="stat-card" key={status}>
                  <div className="stat-label">
                    <span className={`badge badge-status-${status}`}>
                      {statusLabel(status)}
                    </span>
                  </div>
                  <div className="stat-value">
                    {summary.by_status?.[status] ?? 0}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <div className="card">
        <h3>各地点风险表（不含已归档观察项）</h3>
        {riskSites.length === 0 ? (
          <div className="empty-state">暂无地点风险数据</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>地点编号</th>
                <th>地点名称</th>
                <th>区域</th>
                <th>观察项数</th>
                <th>未复核</th>
                <th>已驳回</th>
                <th>最高风险</th>
                <th>最近更新</th>
                {RISK_LEVELS.map((level) => (
                  <th key={level}>{riskLabel(level)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {riskSites.map((site) => (
                <tr key={site.site_id}>
                  <td>{site.site_code}</td>
                  <td>{site.site_name}</td>
                  <td>{site.region || '-'}</td>
                  <td>{site.finding_count}</td>
                  <td>{site.unreviewed_count ?? 0}</td>
                  <td>{site.rejected_count ?? 0}</td>
                  <td>
                    {site.max_risk_level ? (
                      <span
                        className={`badge badge-risk-${site.max_risk_level}`}
                      >
                        {riskLabel(site.max_risk_level)}
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td>{formatTime(site.last_updated_at)}</td>
                  {RISK_LEVELS.map((level) => (
                    <td key={level}>{site.risk_counts?.[level] ?? 0}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
