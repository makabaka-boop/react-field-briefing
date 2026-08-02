import { STATUS_LABELS, RISK_LABELS } from '../api/state'

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status] || status}</span>
}

export function RiskLabel({ level }) {
  return (
    <span>
      <span className={`risk-dot risk-${level}`}></span>
      {RISK_LABELS[level] || level}
    </span>
  )
}
