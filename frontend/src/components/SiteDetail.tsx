import { useState } from 'react'
import { api, ApiClientError } from '../api/client'

export default function SiteDetail({ siteId, onChanged }: { siteId: number; onChanged: () => void }) {
  const [editing, setEditing] = useState(false)
  const [siteName, setSiteName] = useState('')
  const [address, setAddress] = useState('')
  const [region, setRegion] = useState('')
  const [error, setError] = useState('')

  async function save() {
    setError('')
    try {
      await api.updateSite(siteId, { site_name: siteName, address_text: address, region })
      setEditing(false)
      onChanged()
    } catch (err) {
      if (err instanceof ApiClientError) setError(err.message)
    }
  }

  async function remove() {
    if (!confirm('Delete this site and its findings?')) return
    try {
      await api.deleteSite(siteId)
      onChanged()
    } catch (err) {
      if (err instanceof ApiClientError) setError(err.message)
    }
  }

  if (!editing) {
    return (
      <>
        <button className="btn small" style={{ marginLeft: 6 }} onClick={() => { setEditing(true) }}>Edit</button>
        <button className="btn small danger" style={{ marginLeft: 6 }} onClick={remove}>Delete</button>
      </>
    )
  }

  return (
    <div className="panel" style={{ padding: 12, marginTop: 8 }}>
      {error && <div className="error">{error}</div>}
      <div className="form-group"><label>Name</label><input value={siteName} onChange={(e) => setSiteName(e.target.value)} /></div>
      <div className="form-group"><label>Address</label><input value={address} onChange={(e) => setAddress(e.target.value)} /></div>
      <div className="form-group"><label>Region</label><input value={region} onChange={(e) => setRegion(e.target.value)} /></div>
      <button className="btn small" onClick={save}>Save</button>
      <button className="btn small secondary" style={{ marginLeft: 6 }} onClick={() => setEditing(false)}>Cancel</button>
    </div>
  )
}
