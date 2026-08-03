import { useEffect, useState } from 'react'
import { api, ApiClientError } from '../api/client'
import type { TimelineEvent } from '../types'

const TYPE_LABELS: Record<string, string> = {
  site_created: 'Site Created',
  finding_reported: 'Finding Reported',
  attachment_registered: 'Attachment Added',
  review_concluded: 'Review Concluded',
  audit_event: 'Audit Event',
}

export default function SiteTimeline({ siteId }: { siteId: number }) {
  const [events, setEvents] = useState<TimelineEvent[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api.siteTimeline(siteId)
      .then((data) => { if (active) setEvents(data) })
      .catch((e) => { if (active) setError((e as ApiClientError).message) })
    return () => { active = false }
  }, [siteId])

  if (error) return <div className="error">{error}</div>
  if (!events) return <div className="muted">Loading timeline…</div>
  if (events.length === 0) return <div className="muted">No timeline events yet for this site.</div>

  return (
    <div className="timeline" style={{ marginTop: 12 }}>
      {events.map((e) => (
        <div key={`${e.event_type}-${e.event_id}`} className="tl-item">
          <div className="tl-time">
            {e.occurred_at ? new Date(e.occurred_at).toLocaleString() : '—'}
          </div>
          <div className="tl-summary">
            <span className="pill">{TYPE_LABELS[e.event_type] || e.event_type}</span>
            {e.summary}
          </div>
          <div className="tl-actor">by {e.actor || 'system'}</div>
        </div>
      ))}
    </div>
  )
}
