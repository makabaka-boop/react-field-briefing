import { useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { Review } from '../types'

export default function ReviewSidebar({
  findingId, reviews, onReviewed,
}: {
  findingId: number | null
  reviews: Review[]
  onReviewed: () => void
}) {
  const [reviewer, setReviewer] = useState('')
  const [conclusion, setConclusion] = useState<'accepted' | 'rejected'>('accepted')
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (findingId === null) return
    setError('')
    try {
      await api.createReview({ finding_id: findingId, reviewer_name: reviewer, conclusion, comment })
      setReviewer(''); setComment('')
      onReviewed()
    } catch (err) {
      if (err instanceof ApiClientError) setError(`${err.error_code}: ${err.message}`)
      else setError((err as Error).message)
    }
  }

  return (
    <aside className="sidebar">
      <h3>Review Panel</h3>
      {findingId === null ? (
        <p className="muted">Select a finding to record a review conclusion.</p>
      ) : (
        <>
          <p className="muted">Finding #{findingId}</p>
          {error && <div className="error">{error}</div>}
          <form onSubmit={submit}>
            <div className="form-group">
              <label>Reviewer</label>
              <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Conclusion</label>
              <select value={conclusion} onChange={(e) => setConclusion(e.target.value as 'accepted' | 'rejected')}>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
            <div className="form-group">
              <label>Comment</label>
              <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
            </div>
            <button className="btn" type="submit">Submit Review</button>
          </form>

          <h3 style={{ marginTop: 20 }}>History ({reviews.length})</h3>
          {reviews.length === 0 && <p className="muted">No reviews yet.</p>}
          {reviews.map((r) => (
            <div key={r.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{r.reviewer_name}</strong>
                <span className={`badge ${r.conclusion === 'accepted' ? 'accepted' : 'rejected'}`}>{r.conclusion}</span>
              </div>
              <div className="muted" style={{ fontSize: 12 }}>{new Date(r.reviewed_at).toLocaleString()}</div>
              {r.comment && <div style={{ marginTop: 4 }}>{r.comment}</div>}
            </div>
          ))}
        </>
      )}
    </aside>
  )
}
