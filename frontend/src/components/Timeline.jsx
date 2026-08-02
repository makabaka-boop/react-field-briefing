import { riskLabel, statusLabel, timelineActionLabel } from '../stateMachine.js';

function formatTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN');
}

function formatDetail(detail) {
  if (detail === null || detail === undefined || detail === '') return '';
  if (typeof detail === 'string') return detail;
  try {
    return JSON.stringify(detail);
  } catch (err) {
    return String(detail);
  }
}

// 审计事件条目：优先展示 旧状态 → 新状态 与说明，其余 detail 原样展示
function AuditEventDetail({ detail }) {
  if (!detail || typeof detail !== 'object') {
    const text = formatDetail(detail);
    return text ? <div className="timeline-detail">{text}</div> : null;
  }
  const lines = [];
  if (detail.from_status || detail.to_status) {
    lines.push(
      `状态：${statusLabel(detail.from_status)} → ${statusLabel(detail.to_status)}`
    );
  }
  if (detail.note) {
    lines.push(`说明：${detail.note}`);
  }
  if (lines.length === 0) {
    const rest = { ...detail };
    const text = formatDetail(rest);
    if (text && text !== '{}') lines.push(text);
  }
  if (lines.length === 0) return null;
  return (
    <div className="timeline-detail">
      {lines.map((line, index) => (
        <div key={index}>{line}</div>
      ))}
    </div>
  );
}

function TimelineItem({ item }) {
  if (item.item_type === 'finding') {
    const finding = item.finding || {};
    return (
      <li>
        <div className="timeline-head">
          <span>
            <span className="timeline-action">观察项</span>
            {finding.category && (
              <span className="timeline-actor">{finding.category}</span>
            )}
            {finding.risk_level && (
              <span className={`badge badge-risk-${finding.risk_level}`}>
                {riskLabel(finding.risk_level)}
              </span>
            )}
          </span>
          <span className="timeline-time">{formatTime(item.created_at)}</span>
        </div>
        {finding.description && (
          <div className="timeline-detail">{finding.description}</div>
        )}
      </li>
    );
  }

  if (item.item_type === 'attachment') {
    const attachment = item.attachment || {};
    return (
      <li>
        <div className="timeline-head">
          <span>
            <span className="timeline-action">附件元数据</span>
            <span className="timeline-actor">{attachment.file_name}</span>
          </span>
          <span className="timeline-time">{formatTime(item.created_at)}</span>
        </div>
        <div className="timeline-detail">
          <div>类型：{attachment.file_type || '-'}</div>
          {attachment.storage_note && <div>存储说明：{attachment.storage_note}</div>}
        </div>
      </li>
    );
  }

  // 默认按审计事件渲染（item_type === 'audit_event' 或旧格式）
  return (
    <li>
      <div className="timeline-head">
        <span>
          <span className="timeline-action">
            {timelineActionLabel(item.action)}
          </span>
          {item.actor && <span className="timeline-actor">{item.actor}</span>}
        </span>
        <span className="timeline-time">{formatTime(item.created_at)}</span>
      </div>
      <AuditEventDetail detail={item.detail} />
    </li>
  );
}

export default function Timeline({ items }) {
  if (!items || items.length === 0) {
    return <div className="empty-state">暂无时间线记录</div>;
  }
  return (
    <ul className="timeline">
      {items.map((item, index) => (
        <TimelineItem key={index} item={item} />
      ))}
    </ul>
  );
}
