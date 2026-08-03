import { STATUS_LABELS } from '../state/statusMachine.js';

// Renders a merged, time-ordered timeline of audit events, reviews and
// attachment registrations for one finding.
function describe(e) {
  if (e.kind === 'finding') {
    return {
      title: `观察项创建：${e.category}`,
      body: `${e.reported_by} · 风险 ${e.risk_level} · ${e.description}`,
    };
  }
  if (e.kind === 'audit') {
    const from = e.old_status ? `${STATUS_LABELS[e.old_status] || e.old_status} → ` : '';
    const to = e.new_status ? STATUS_LABELS[e.new_status] || e.new_status : '';
    const who = e.actor_name ? `（${e.actor_name}）` : '';
    return {
      title: `${e.action} ${from}${to}`.trim(),
      body: `${who}${e.note ? ' · ' + e.note : ''}`,
    };
  }
  if (e.kind === 'review') {
    return {
      title: `复核结论：${e.conclusion}`,
      body: `${e.reviewer_name}${e.review_note ? ' · ' + e.review_note : ''}`,
    };
  }
  if (e.kind === 'attachment') {
    return {
      title: `登记附件：${e.file_name}`,
      body: `${e.file_type}${e.storage_note ? ' · ' + e.storage_note : ''}`,
    };
  }
  return { title: e.kind, body: '' };
}

export default function Timeline({ events }) {
  if (!events || !events.length) {
    return <p className="muted">暂无时间线记录。</p>;
  }
  return (
    <div data-testid="timeline">
      {events.map((e, i) => {
        const d = describe(e);
        return (
          <div className="timeline-item" key={i}>
            <div className="ts">{e.created_at}</div>
            <div><strong>{d.title}</strong></div>
            {d.body && <div className="muted">{d.body}</div>}
          </div>
        );
      })}
    </div>
  );
}
