import { useCallback, useEffect, useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { ConsistencyReport } from '../types'

const CHECK_LABELS: Record<string, string> = {
  orphan_sites: 'Orphan Sites',
  orphan_findings: 'Orphan Findings',
  orphan_attachments: 'Orphan Attachments',
  status_audit_drift: 'Status / Audit Drift',
  template_duplicate_site_codes: 'Template Duplicate Site Codes',
  overview_consistency: 'Risk Overview Consistency',
}

export default function SystemCheckView() {
  const [report, setReport] = useState<ConsistencyReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.consistency()
      setReport(data)
    } catch (e) {
      setError((e as ApiClientError).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { run() }, [run])

  return (
    <div>
      <div className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: 0 }}>System Consistency Check</h2>
            <p className="muted" style={{ margin: '4px 0 0' }}>
              Validates referential integrity, status/audit alignment, template data and risk overview totals.
            </p>
          </div>
          <button className="btn" onClick={run} disabled={loading}>
            {loading ? 'Running…' : 'Re-run checks'}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {report && (
        <>
          <div className="cards" style={{ marginBottom: 20 }}>
            <div className="card">
              <div className="label">Overall</div>
              <div className="num" style={{ color: report.passed ? 'var(--ok)' : 'var(--danger)' }}>
                {report.passed ? 'PASS' : 'FAIL'}
              </div>
            </div>
            <div className="card">
              <div className="label">Checks Run</div>
              <div className="num">{report.total_checks}</div>
            </div>
            <div className="card">
              <div className="label">Failed Checks</div>
              <div className="num" style={{ color: report.failed_checks ? 'var(--danger)' : undefined }}>
                {report.failed_checks}
              </div>
            </div>
            <div className="card">
              <div className="label">Total Issues</div>
              <div className="num" style={{ color: report.total_issues ? 'var(--warn)' : undefined }}>
                {report.total_issues}
              </div>
            </div>
          </div>

          <div className="panel">
            <h3>Check Results</h3>
            <table>
              <thead>
                <tr><th>Check</th><th>Description</th><th>Status</th><th>Issues</th><th>Details</th></tr>
              </thead>
              <tbody>
                {report.checks.map((c) => (
                  <tr key={c.check_name}>
                    <td>{CHECK_LABELS[c.check_name] || c.check_name}<div className="muted" style={{ fontSize: 11 }}>{c.check_name}</div></td>
                    <td>{c.description}</td>
                    <td>
                      <span className={`badge ${c.passed ? 'accepted' : 'rejected'}`}>
                        {c.passed ? 'passed' : 'failed'}
                      </span>
                    </td>
                    <td>{c.issue_count}</td>
                    <td>
                      {c.issues.length === 0 ? (
                        <span className="muted">—</span>
                      ) : (
                        <pre style={{
                          margin: 0, fontSize: 11, background: '#f9fafb',
                          border: '1px solid var(--border)', borderRadius: 4,
                          padding: 8, maxWidth: 480, overflowX: 'auto', whiteSpace: 'pre-wrap',
                        }}>
                          {JSON.stringify(c.issues, null, 2)}
                        </pre>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
