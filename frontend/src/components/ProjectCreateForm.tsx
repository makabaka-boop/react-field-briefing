import { useState } from 'react'
import { api, ApiClientError } from '../api/client'

export default function ProjectCreateForm({
  onCreated, onCancel,
}: { onCreated: () => void; onCancel: () => void }) {
  const [projectCode, setProjectCode] = useState('')
  const [projectName, setProjectName] = useState('')
  const [owner, setOwner] = useState('')
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api.createProject({ project_code: projectCode, project_name: projectName, owner_name: owner })
      onCreated()
    } catch (err) {
      if (err instanceof ApiClientError) setError(`${err.error_code}: ${err.message}`)
      else setError((err as Error).message)
    }
  }

  return (
    <div className="panel">
      <h3>New Blank Project</h3>
      {error && <div className="error">{error}</div>}
      <form onSubmit={submit} className="row">
        <div className="col form-group">
          <label>Project Code</label>
          <input value={projectCode} onChange={(e) => setProjectCode(e.target.value)} required />
        </div>
        <div className="col form-group">
          <label>Project Name</label>
          <input value={projectName} onChange={(e) => setProjectName(e.target.value)} required />
        </div>
        <div className="col form-group">
          <label>Owner</label>
          <input value={owner} onChange={(e) => setOwner(e.target.value)} required />
        </div>
        <div className="col form-group" style={{ alignSelf: 'end' }}>
          <button className="btn" type="submit">Create</button>
          <button className="btn secondary" type="button" onClick={onCancel} style={{ marginLeft: 8 }}>Cancel</button>
        </div>
      </form>
    </div>
  )
}
