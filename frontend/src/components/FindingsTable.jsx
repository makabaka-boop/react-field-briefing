import { riskLabel, statusLabel } from '../stateMachine.js';

function formatTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN');
}

export default function FindingsTable({ findings, selectedId, onSelect }) {
  if (!findings || findings.length === 0) {
    return <div className="empty-state">暂无观察项记录</div>;
  }
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>类别</th>
          <th>描述</th>
          <th>风险等级</th>
          <th>状态</th>
          <th>填报人</th>
          <th>填报时间</th>
        </tr>
      </thead>
      <tbody>
        {findings.map((finding) => (
          <tr
            key={finding.id}
            className={[
              'clickable',
              selectedId === finding.id ? 'selected' : '',
            ].join(' ')}
            onClick={() => onSelect && onSelect(finding)}
          >
            <td>{finding.category}</td>
            <td className="desc-cell" title={finding.description}>
              {finding.description}
            </td>
            <td>
              <span className={`badge badge-risk-${finding.risk_level}`}>
                {riskLabel(finding.risk_level)}
              </span>
            </td>
            <td>
              <span className={`badge badge-status-${finding.finding_status}`}>
                {statusLabel(finding.finding_status)}
              </span>
            </td>
            <td>{finding.reported_by || '-'}</td>
            <td>{formatTime(finding.reported_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
