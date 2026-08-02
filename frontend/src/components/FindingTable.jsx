import { StatusBadge, RiskLabel } from './Badges'
import { getAvailableTransitions, STATUS_LABELS } from '../api/state'

export default function FindingTable({ findings, onEdit, onReview, onTransition, onViewTimeline, showSite = false }) {
  if (findings.length === 0) {
    return <div className="empty-state">暂无观察项</div>
  }

  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          {showSite && <th>地点</th>}
          <th>分类</th>
          <th>描述</th>
          <th>风险</th>
          <th>状态</th>
          <th>报告人</th>
          <th>报告时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        {findings.map(f => (
          <tr key={f.id}>
            <td>#{f.id}</td>
            {showSite && <td>{f.site_name || `Site #${f.site_id}`}</td>}
            <td>{f.category || '-'}</td>
            <td style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {f.description || '-'}
            </td>
            <td><RiskLabel level={f.risk_level} /></td>
            <td><StatusBadge status={f.finding_status} /></td>
            <td>{f.reported_by || '-'}</td>
            <td>{f.reported_at}</td>
            <td>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                <button className="btn btn-sm" onClick={() => onEdit && onEdit(f)}>编辑</button>
                <button className="btn btn-sm" onClick={() => onReview && onReview(f)}>复核</button>
                <button className="btn btn-sm" onClick={() => onViewTimeline && onViewTimeline(f)}>时间线</button>
                {onTransition && getAvailableTransitions(f.finding_status, false).map(t => (
                  <button
                    key={t}
                    className="btn btn-sm"
                    onClick={() => onTransition(f, t)}
                    title={STATUS_LABELS[t]}
                  >
                    → {STATUS_LABELS[t]}
                  </button>
                ))}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
