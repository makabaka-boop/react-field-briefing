import { RiskBadge, StatusBadge } from './Badge.jsx';

// Read-only table of observation findings with a select action.
export default function FindingsTable({ findings, onSelect, selectedId }) {
  if (!findings.length) {
    return <p className="muted">暂无观察项。</p>;
  }
  return (
    <table data-testid="findings-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>类别</th>
          <th>描述</th>
          <th>风险</th>
          <th>状态</th>
          <th>报告人</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {findings.map((f) => (
          <tr
            key={f.id}
            style={f.id === selectedId ? { background: '#eef4fc' } : undefined}
          >
            <td>{f.id}</td>
            <td>{f.category}</td>
            <td>{f.description}</td>
            <td><RiskBadge level={f.risk_level} /></td>
            <td><StatusBadge status={f.finding_status} /></td>
            <td>{f.reported_by}</td>
            <td>
              <button className="link-btn" onClick={() => onSelect(f)}>
                复核
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
