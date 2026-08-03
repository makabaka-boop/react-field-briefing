import { useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { RiskLevel, Site } from '../types'
import { ALL_RISK_LEVELS } from '../types'

export default function FindingForm({
  sites, defaultSiteId, onSaved, onCancel,
}: {
  sites: Site[]
  defaultSiteId?: number
  onSaved: () => void
  onCancel: () => void
}) {
  const [siteId, setSiteId] = useState<number>(defaultSiteId || sites[0]?.id || 0)
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [riskLevel, setRiskLevel] = useState<RiskLevel>('low')
  const [reportedBy, setReportedBy] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!category.trim() || !description.trim() || !reportedBy.trim()) {
      setError('category, description and reported_by are required.')
      return
    }

    setSubmitting(true)
    try {
      await api.createDraft({
        site_id: siteId,
        category: category.trim(),
        description: description.trim(),
        risk_level: riskLevel,
        reported_by: reportedBy.trim(),
      })
      onSaved()
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message)
      } else {
        setError((err as Error).message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (sites.length === 0) {
    return <div className="error">Create a site before adding findings.</div>
  }

  return (
    <div className="panel" style={{ background: '#f9fafb' }}>
      <h3>New Finding Draft</h3>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <form onSubmit={submit} className="row">
        <div className="col form-group">
          <label>Site *</label>
          <select value={siteId} onChange={(e) => setSiteId(Number(e.target.value))} required>
            {sites.map((s) => <option key={s.id} value={s.id}>{s.site_code} — {s.site_name}</option>)}
          </select>
        </div>
        <div className="col form-group">
          <label>Category *</label>
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g. safety, environment"
            required
          />
        </div>
        <div className="col form-group">
          <label>Risk Level *</label>
          <select value={riskLevel} onChange={(e) => setRiskLevel(e.target.value as RiskLevel)} required>
            {ALL_RISK_LEVELS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div className="col form-group">
          <label>Reported By *</label>
          <input
            value={reportedBy}
            onChange={(e) => setReportedBy(e.target.value)}
            required
          />
        </div>
        <div className="form-group" style={{ flexBasis: '100%' }}>
          <label>Description *</label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>
        <div style={{ flexBasis: '100%' }}>
          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : 'Save Draft'}
          </button>
          <button className="btn secondary" type="button" onClick={onCancel} style={{ marginLeft: 8 }} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
