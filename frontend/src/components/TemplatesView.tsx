import { useEffect, useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { SiteTemplate } from '../types'

export default function TemplatesView() {
  const [templates, setTemplates] = useState<SiteTemplate[]>([])
  const [name, setName] = useState('')
  const [region, setRegion] = useState('')
  const [itemsJson, setItemsJson] = useState('[\n  {"site_code":"S-001","site_name":"Site 1","address_text":"","region":""}\n]')
  const [error, setError] = useState('')

  async function load() {
    const data = await api.listTemplates()
    setTemplates(data)
  }
  useEffect(() => { load() }, [])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const site_items = JSON.parse(itemsJson)
      if (!Array.isArray(site_items)) throw new Error('site_items must be a JSON array')
      await api.createTemplate({ template_name: name, default_region: region, site_items })
      setName(''); setRegion('')
      load()
    } catch (err) {
      if (err instanceof ApiClientError) setError(`${err.error_code}: ${err.message}`)
      else setError((err as Error).message)
    }
  }

  return (
    <div>
      <div className="panel">
        <h2>Site Templates</h2>
        <p className="muted">Define reusable location lists. When a project is created from a template, sites are batch-generated.</p>
      </div>

      <div className="panel">
        <h3>New Template</h3>
        {error && <div className="error">{error}</div>}
        <form onSubmit={create}>
          <div className="row">
            <div className="col form-group">
              <label>Template Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="col form-group">
              <label>Default Region</label>
              <input value={region} onChange={(e) => setRegion(e.target.value)} />
            </div>
          </div>
          <div className="form-group site-items-editor">
            <label>Site Items (JSON array)</label>
            <textarea rows={8} value={itemsJson} onChange={(e) => setItemsJson(e.target.value)} />
          </div>
          <button className="btn" type="submit">Create Template</button>
        </form>
      </div>

      <div className="panel">
        <h3>Existing Templates</h3>
        <table>
          <thead>
            <tr><th>ID</th><th>Name</th><th>Default Region</th><th>Site Count</th><th>Created</th></tr>
          </thead>
          <tbody>
            {templates.map((t) => (
              <tr key={t.id}>
                <td>{t.id}</td>
                <td>{t.template_name}</td>
                <td>{t.default_region || '—'}</td>
                <td>{t.site_items.length}</td>
                <td className="muted">{new Date(t.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {templates.length === 0 && <tr><td colSpan={5} className="muted" style={{ textAlign: 'center' }}>No templates yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
