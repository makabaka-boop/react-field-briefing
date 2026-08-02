import { RISK_LABELS, RISK_LEVELS, STATUS_LABELS, STATUSES } from '../state/statusMachine.js';

// Reusable filter controls for findings tables and site lists.
export default function RiskFilters({ value, onChange, regions = [] }) {
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value });
  return (
    <div className="filters" data-testid="risk-filters">
      <div className="field">
        <label>观察项状态</label>
        <select value={value.finding_status || ''} onChange={set('finding_status')}>
          <option value="">全部</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{STATUS_LABELS[s]}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>风险等级</label>
        <select value={value.risk_level || ''} onChange={set('risk_level')}>
          <option value="">全部</option>
          {RISK_LEVELS.map((r) => (
            <option key={r} value={r}>{RISK_LABELS[r]}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>区域</label>
        <select value={value.region || ''} onChange={set('region')}>
          <option value="">全部</option>
          {regions.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
