import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client.js';

// "系统检查" view: runs the backend consistency self-check and shows each
// check's pass status, issue count and issue detail. Used before delivery
// to confirm no field/status/template/history drift.
const CHECK_LABELS = {
  orphan_sites: '地点指向不存在的项目',
  findings_missing_site: '观察项缺少所属地点',
  status_audit_mismatch: '状态与最后一条审计事件不一致',
  attachments_missing_finding: '附件指向不存在的观察项',
  duplicate_site_codes: '同项目内地点编码重复',
  risk_overview_consistency: '风险概览统计与明细数量不一致',
};

export default function SystemCheck() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const run = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      setReport(await api.consistencyChecks());
    } catch (err) {
      setError(err.message);
      setReport(null);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    run();
  }, [run]);

  return (
    <div>
      <div className="card">
        <h2>系统检查</h2>
        <p className="muted">
          交付前一致性自检：核对地点/观察项/附件引用、状态与审计一致性、模板地点编码与风险统计口径。
        </p>
        <button onClick={run} disabled={busy}>
          {busy ? '检查中…' : '重新检查'}
        </button>
        {error && <div className="form-error" role="alert" style={{ marginTop: 12 }}>{error}</div>}
        {report && (
          <p style={{ marginTop: 12 }} data-testid="check-summary">
            {report.passed ? (
              <span className="badge" style={{ background: '#2e7d32' }}>全部通过</span>
            ) : (
              <span className="badge" style={{ background: '#c62828' }}>
                发现 {report.total_issues} 个问题
              </span>
            )}
            <span className="muted" style={{ marginLeft: 8 }}>
              检查时间：{report.checked_at}
            </span>
          </p>
        )}
      </div>

      {report && report.checks.map((c) => (
        <div className="card" key={c.check_name} data-testid={`check-${c.check_name}`}>
          <h3>
            {c.passed ? (
              <span className="badge" style={{ background: '#2e7d32' }}>通过</span>
            ) : (
              <span className="badge" style={{ background: '#c62828' }}>
                {c.issue_count} 个问题
              </span>
            )}{' '}
            {CHECK_LABELS[c.check_name] || c.check_name}
          </h3>
          <p className="muted">{c.description}</p>
          {c.issue_count > 0 && (
            <table>
              <thead>
                <tr>
                  {Object.keys(c.issues[0]).map((k) => (
                    <th key={k}>{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {c.issues.map((issue, i) => (
                  <tr key={i}>
                    {Object.keys(c.issues[0]).map((k) => (
                      <td key={k}>{String(issue[k])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
    </div>
  );
}
