import { STATUSES, STATUS_LABELS, RISK_LEVELS, RISK_LABELS } from '../api/state'

export default function RiskFilters({ filters, onChange }) {
  return (
    <div className="filters">
      <div className="form-group">
        <label>状态筛选</label>
        <select value={filters.finding_status || ''} onChange={e => onChange({ ...filters, finding_status: e.target.value })}>
          <option value="">全部状态</option>
          {STATUSES.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
        </select>
      </div>
      <div className="form-group">
        <label>风险等级</label>
        <select value={filters.risk_level || ''} onChange={e => onChange({ ...filters, risk_level: e.target.value })}>
          <option value="">全部等级</option>
          {RISK_LEVELS.map(r => <option key={r} value={r}>{RISK_LABELS[r]}</option>)}
        </select>
      </div>
      <div className="form-group">
        <label>区域筛选</label>
        <input
          value={filters.region || ''}
          onChange={e => onChange({ ...filters, region: e.target.value })}
          placeholder="输入区域"
        />
      </div>
    </div>
  )
}
