import { useEffect, useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { ProjectRiskSummary, SiteTemplate } from '../types'

type Phase = 'select' | 'form' | 'result' | 'error'

export default function TemplateProjectWizard({
  onCreated, onCancel,
}: {
  onCreated: (id: number) => void
  onCancel: () => void
}) {
  const [phase, setPhase] = useState<Phase>('select')
  const [templates, setTemplates] = useState<SiteTemplate[]>([])
  const [templateId, setTemplateId] = useState<number | ''>('')
  const [projectCode, setProjectCode] = useState('')
  const [projectName, setProjectName] = useState('')
  const [owner, setOwner] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<ProjectRiskSummary | null>(null)

  useEffect(() => {
    api.listTemplates().then((data) => {
      setTemplates(data)
      if (data[0]) setTemplateId(data[0].id)
    }).catch((e) => setError((e as ApiClientError).message))
  }, [])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!templateId) {
      setError('Please select a template.')
      return
    }
    try {
      const summary = await api.createProjectFromTemplate({
        project_code: projectCode.trim(),
        project_name: projectName.trim(),
        owner_name: owner.trim(),
        template_id: Number(templateId),
      })
      setResult(summary)
      setPhase('result')
    } catch (err) {
      if (err instanceof ApiClientError) setError(err.message)
      else setError((err as Error).message)
      setPhase('error')
    }
  }

  if (phase === 'result' && result) {
    return (
      <div className="panel" style={{ background: '#f0fdf4', borderColor: '#86efac' }}>
        <h3 style={{ color: '#166534' }}>Project created successfully</h3>
        <p>
          <strong>{result.project_name}</strong> ({result.project_code}) was created in a single transaction
          with <strong>{result.total_sites}</strong> sites.
        </p>
        <table style={{ marginTop: 12 }}>
          <thead>
            <tr><th>Site Code</th><th>Name</th><th>Region</th></tr>
          </thead>
          <tbody>
            {result.sites.map((s) => (
              <tr key={s.site_id}>
                <td>{s.site_code}</td>
                <td>{s.site_name}</td>
                <td>{s.region || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <button className="btn" onClick={() => onCreated(result.project_id)}>Open project</button>
          <button className="btn secondary" onClick={onCancel}>Back to list</button>
        </div>
      </div>
    )
  }

  return (
    <div className="panel">
      <h3>Create Project from Template</h3>
      <p className="muted">
        The project and all template sites are created in one transaction. If any site code is invalid or duplicated,
        the whole batch is rolled back and no partial data is saved.
      </p>

      {error && <div className="error" role="alert">{error}</div>}

      <form onSubmit={create}>
        {phase === 'select' && (
          <>
            <div className="form-group">
              <label>Select Template *</label>
              {templates.length === 0 ? (
                <div className="muted">No templates available. Create one in the Templates page first.</div>
              ) : (
                <select value={templateId} onChange={(e) => setTemplateId(Number(e.target.value))}>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.template_name} — {t.site_items.length} sites (default region: {t.default_region || '—'})
                    </option>
                  ))}
                </select>
              )}
            </div>
            <button className="btn" type="button" disabled={!templateId} onClick={() => setPhase('form')}>
              Next
            </button>
            <button className="btn secondary" type="button" onClick={onCancel} style={{ marginLeft: 8 }}>Cancel</button>
          </>
        )}

        {phase === 'form' && (
          <>
            <div className="row">
              <div className="col form-group">
                <label>Project Code *</label>
                <input value={projectCode} onChange={(e) => setProjectCode(e.target.value)} required />
              </div>
              <div className="col form-group">
                <label>Project Name *</label>
                <input value={projectName} onChange={(e) => setProjectName(e.target.value)} required />
              </div>
              <div className="col form-group">
                <label>Owner *</label>
                <input value={owner} onChange={(e) => setOwner(e.target.value)} required />
              </div>
            </div>
            <div>
              <button className="btn" type="submit">Create project & sites</button>
              <button className="btn secondary" type="button" onClick={() => setPhase('select')} style={{ marginLeft: 8 }}>
                Back
              </button>
            </div>
          </>
        )}

        {phase === 'error' && (
          <div>
            <button className="btn secondary" type="button" onClick={() => { setError(''); setPhase('form') }}>
              Back to form
            </button>
          </div>
        )}
      </form>
    </div>
  )
}
