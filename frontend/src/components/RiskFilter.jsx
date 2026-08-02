import { RISK_LEVELS, STATUS_LIST, riskLabel, statusLabel } from '../stateMachine.js';

export default function RiskFilter({ filters, onChange }) {
  const handleChange = (key) => (event) => {
    onChange({ ...filters, [key]: event.target.value });
  };

  return (
    <div className="filter-bar">
      <div className="form-row">
        <label>风险等级</label>
        <select
          value={filters.risk_level || ''}
          onChange={handleChange('risk_level')}
        >
          <option value="">全部</option>
          {RISK_LEVELS.map((level) => (
            <option key={level} value={level}>
              {riskLabel(level)}
            </option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label>状态</label>
        <select
          value={filters.finding_status || ''}
          onChange={handleChange('finding_status')}
        >
          <option value="">全部</option>
          {STATUS_LIST.map((status) => (
            <option key={status} value={status}>
              {statusLabel(status)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
