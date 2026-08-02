import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

const CHECK_LABELS = {
  orphan_sites: '地点关联项目检查',
  orphan_findings: '观察项关联地点检查',
  status_audit_mismatch: '状态与审计一致性',
  orphan_attachments: '附件关联观察项检查',
  duplicate_template_site_codes: '模板地点编码重复检查',
  risk_stats_consistency: '风险统计与明细一致性',
}

const CHECK_DESCRIPTIONS = {
  orphan_sites: '检查是否存在指向不存在项目的地点记录',
  orphan_findings: '检查是否存在缺少有效地点的观察项',
  status_audit_mismatch: '检查观察项当前状态与最后一条审计事件记录是否一致',
  orphan_attachments: '检查是否存在指向不存在观察项的附件',
  duplicate_template_site_codes: '检查模板 site_items 中是否存在重复地点编码',
  risk_stats_consistency: '检查风险概览统计数量与明细汇总是否一致',
}

export default function SystemCheckPage() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState({})

  const runCheck = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.runSystemCheck()
      setResult(data)
      const expand = {}
      data.checks.forEach(c => { if (!c.passed) expand[c.check_code] = true })
      setExpanded(expand)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { runCheck() }, [runCheck])

  function toggleExpand(code) {
    setExpanded(prev => ({ ...prev, [code]: !prev[code] }))
  }

  if (loading) return <div className="empty-state">正在执行系统自检...</div>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>系统自检</h1>
        <button className="btn btn-primary" onClick={runCheck} disabled={loading}>
          {loading ? '检查中...' : '重新检查'}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {result && (
        <>
          <div className="stats-grid">
            <div className="stat-card" style={{ borderLeft: result.all_passed ? '4px solid var(--success)' : '4px solid var(--danger)' }}>
              <div className="label">总体状态</div>
              <div className="value" style={{ fontSize: 22, color: result.all_passed ? 'var(--success)' : 'var(--danger)' }}>
                {result.all_passed ? '✓ 全部通过' : '✗ 发现问题'}
              </div>
            </div>
            <div className="stat-card">
              <div className="label">检查项总数</div>
              <div className="value">{result.total_checks}</div>
            </div>
            <div className="stat-card">
              <div className="label">通过项</div>
              <div className="value" style={{ color: 'var(--success)' }}>{result.passed_checks}</div>
            </div>
            <div className="stat-card">
              <div className="label">问题总数</div>
              <div className="value" style={{ color: result.total_issues > 0 ? 'var(--danger)' : 'inherit' }}>{result.total_issues}</div>
            </div>
          </div>

          <div className="card" style={{ padding: 0 }}>
            {result.checks.map(check => (
              <div key={check.check_code} style={{ borderBottom: '1px solid var(--border)' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 20px',
                    cursor: check.issue_count > 0 ? 'pointer' : 'default',
                    background: check.passed ? 'transparent' : '#fef7e0',
                  }}
                  onClick={() => check.issue_count > 0 && toggleExpand(check.check_code)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 24,
                      height: 24,
                      borderRadius: '50%',
                      background: check.passed ? 'var(--success)' : 'var(--danger)',
                      color: '#fff',
                      fontSize: 14,
                      fontWeight: 700,
                    }}>
                      {check.passed ? '✓' : '!'}
                    </span>
                    <div>
                      <div style={{ fontWeight: 500, fontSize: 14 }}>
                        {CHECK_LABELS[check.check_code] || check.check_code}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        {CHECK_DESCRIPTIONS[check.check_code]}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {check.issue_count > 0 && (
                      <span className="badge badge-rejected">{check.issue_count} 个问题</span>
                    )}
                    {check.issue_count > 0 && (
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        {expanded[check.check_code] ? '收起 ▲' : '展开 ▼'}
                      </span>
                    )}
                  </div>
                </div>
                {expanded[check.check_code] && check.issues.length > 0 && (
                  <div style={{ padding: '0 20px 16px 56px', background: '#fff' }}>
                    <table style={{ fontSize: 13 }}>
                      <thead>
                        <tr>
                          {Object.keys(check.issues[0]).filter(k => k !== 'message').map(key => (
                            <th key={key}>{key}</th>
                          ))}
                          <th>说明</th>
                        </tr>
                      </thead>
                      <tbody>
                        {check.issues.map((issue, idx) => (
                          <tr key={idx}>
                            {Object.entries(issue).filter(([k]) => k !== 'message').map(([k, v]) => (
                              <td key={k}>{String(v)}</td>
                            ))}
                            <td style={{ color: 'var(--danger)' }}>{issue.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
