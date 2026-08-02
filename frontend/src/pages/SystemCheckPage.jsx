import { useCallback, useEffect, useState } from 'react';
import { getConsistencyChecks } from '../api/client.js';

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '-';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function IssueTable({ issues }) {
  // 汇总所有 issue 的字段作为列，保证任意问题明细都能渲染
  const columns = [];
  issues.forEach((issue) => {
    Object.keys(issue).forEach((key) => {
      if (!columns.includes(key)) columns.push(key);
    });
  });
  return (
    <table className="data-table" style={{ marginTop: 8 }}>
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column}>{column}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {issues.map((issue, rowIndex) => (
          <tr key={rowIndex}>
            {columns.map((column) => (
              <td key={column}>{formatValue(issue[column])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function SystemCheckPage() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadChecks = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getConsistencyChecks();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChecks();
  }, [loadChecks]);

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}
      <div className="card">
        <div className="card-title-row">
          <h3>系统检查</h3>
          <button className="btn" onClick={loadChecks} disabled={loading}>
            {loading ? '检查中…' : '重新检查'}
          </button>
        </div>
        {loading && !result ? (
          <div className="loading">加载中…</div>
        ) : !result ? null : (
          <>
            <div
              className={
                result.passed ? 'success-banner' : 'error-banner'
              }
              role="status"
            >
              {result.passed
                ? '全部检查通过，未发现数据漂移'
                : `发现 ${result.total_issues} 个问题，请处理后再交付`}
            </div>
            {result.checks?.map((check) => (
              <div className="card" key={check.check_code}>
                <div className="card-title-row">
                  <h3>{check.check_name}</h3>
                  <span
                    className={`badge ${
                      check.passed ? 'badge-status-accepted' : 'badge-status-rejected'
                    }`}
                  >
                    {check.passed ? '通过' : `未通过（${check.issue_count} 个问题）`}
                  </span>
                </div>
                <div className="meta-text">检查项：{check.check_code}</div>
                {check.issues && check.issues.length > 0 && (
                  <IssueTable issues={check.issues} />
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
