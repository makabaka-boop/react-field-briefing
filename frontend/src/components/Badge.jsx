import { RISK_COLORS, RISK_LABELS, STATUS_LABELS } from '../state/statusMachine.js';

export function RiskBadge({ level }) {
  if (!level) return <span className="muted">—</span>;
  return (
    <span className="badge" style={{ background: RISK_COLORS[level] || '#999' }}>
      {RISK_LABELS[level] || level}
    </span>
  );
}

const STATUS_COLORS = {
  draft: '#607d8b',
  submitted: '#1565c0',
  reviewing: '#6a1b9a',
  accepted: '#2e7d32',
  rejected: '#c62828',
  archived: '#455a64',
};

export function StatusBadge({ status }) {
  return (
    <span className="badge" style={{ background: STATUS_COLORS[status] || '#999' }}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}
