import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { STATUS_LABELS } from '../api/state'

export default function ReviewSidebar({ findingId, onClose, onReviewed }) {
  const [reviews, setReviews] = useState([])
  const [reviewerName, setReviewerName] = useState('')
  const [conclusion, setConclusion] = useState('approved')
  const [comment, setComment] = useState('')
  const [newStatus, setNewStatus] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (findingId) loadReviews()
  }, [findingId])

  async function loadReviews() {
    try {
      const data = await api.listReviews(findingId)
      setReviews(data)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        reviewer_name: reviewerName,
        conclusion,
        comment,
      }
      if (newStatus) payload.new_status = newStatus
      await api.createReview(findingId, payload)
      setReviewerName('')
      setComment('')
      setNewStatus('')
      await loadReviews()
      if (onReviewed) onReviewed()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="sidebar-overlay" onClick={onClose}>
      <div className="sidebar-panel" onClick={e => e.stopPropagation()}>
        <div className="sidebar-header">
          <h2>复核记录</h2>
          <button className="btn btn-sm" onClick={onClose}>关闭</button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>历史复核</h3>
          {reviews.length === 0 && <div className="empty-state" style={{ padding: 20 }}>暂无复核记录</div>}
          {reviews.map(r => (
            <div key={r.id} className="review-item">
              <div className="review-meta">
                <span>{r.reviewer_name}</span>
                <span>{r.reviewed_at}</span>
              </div>
              <div className="review-conclusion">
                结论：{r.conclusion === 'approved' ? '通过' : r.conclusion === 'rejected' ? '驳回' : '需修改'}
                {r.new_status_note && ` (${STATUS_LABELS[r.new_status_note] || r.new_status_note})`}
              </div>
              {r.comment && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{r.comment}</div>}
            </div>
          ))}
        </div>

        <h3 style={{ fontSize: 15, marginBottom: 12 }}>新增复核</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>复核人</label>
            <input value={reviewerName} onChange={e => setReviewerName(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>结论</label>
            <select value={conclusion} onChange={e => setConclusion(e.target.value)}>
              <option value="approved">通过</option>
              <option value="rejected">驳回</option>
              <option value="needs_changes">需修改</option>
            </select>
          </div>
          <div className="form-group">
            <label>备注</label>
            <textarea value={comment} onChange={e => setComment(e.target.value)} />
          </div>
          <div className="form-group">
            <label>手动指定状态（可选）</label>
            <select value={newStatus} onChange={e => setNewStatus(e.target.value)}>
              <option value="">不修改状态（按结论自动流转）</option>
              <option value="reviewing">审核中</option>
              <option value="accepted">已通过</option>
              <option value="rejected">已驳回</option>
              <option value="draft">退回草稿</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? '提交中...' : '提交复核'}
          </button>
        </form>
      </div>
    </div>
  )
}
