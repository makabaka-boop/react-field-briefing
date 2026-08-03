import { useEffect, useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { RiskOverview as Overview } from '../types'
import { ALL_RISK_LEVELS, ALL_STATUSES } from '../types'

export default function OverviewView() {
  const [data, setData] = useState<Overview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.overview().then(setData).catch((e) => setError((e as ApiClientError).message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="panel">Loading…</div>

  const totalByRisk = ALL_RISK_LEVELS.reduce((s, k) => s + (data.by_risk[k] || 0), 0)

  return (
    <div>
      <div className="panel"><h2>Risk Overview</h2></div>
      <div className="cards">
        <div className="card"><div className="label">Projects</div><div className="num">{data.total_projects}</div></div>
        <div className="card"><div className="label">Sites</div><div className="num">{data.total_sites}</div></div>
        <div className="card"><div className="label">Findings</div><div className="num">{data.total_findings}</div></div>
        <div className="card"><div className="label">Regions</div><div className="num">{Object.keys(data.by_region).length}</div></div>
      </div>

      <div className="row" style={{ marginTop: 20 }}>
        <div className="panel col">
          <h3>Findings by Risk</h3>
          {ALL_RISK_LEVELS.map((r) => {
            const count = data.by_risk[r] || 0
            const pct = totalByRisk ? (count / totalByRisk) * 100 : 0
            return (
              <div key={r} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span><span className={`badge ${r}`}>{r}</span></span>
                  <span>{count}</span>
                </div>
                <div style={{ background: '#e5e7eb', borderRadius: 4, height: 8, marginTop: 4 }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: `var(--${r})`, borderRadius: 4 }} />
                </div>
              </div>
            )
          })}
        </div>
        <div className="panel col">
          <h3>Findings by Status</h3>
          {ALL_STATUSES.map((s) => (
            <div key={s} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
              <span><span className={`badge ${s}`}>{s}</span></span>
              <span>{data.by_status[s] || 0}</span>
            </div>
          ))}
        </div>
        <div className="panel col">
          <h3>Sites by Region</h3>
          {Object.entries(data.by_region).length === 0 && <div className="muted">No data</div>}
          {Object.entries(data.by_region).map(([region, count]) => (
            <div key={region} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
              <span>{region}</span><span>{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
