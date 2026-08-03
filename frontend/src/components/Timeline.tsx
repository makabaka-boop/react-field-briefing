import type { TimelineEvent } from '../types'

const TYPE_LABELS: Record<string, string> = {
  site_created: 'Site Created',
  finding_reported: 'Finding Reported',
  attachment_registered: 'Attachment Added',
  review_concluded: 'Review Concluded',
}

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) return <p className="muted">No timeline events yet.</p>
  return (
    <div className="timeline">
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
