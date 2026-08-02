import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { RiskLabel } from './Badges'

const TYPE_LABELS = {
  finding_created: '创建观察项',
  audit: '操作记录',
  review: '复核',
  attachment: '附件登记',
  site_audit: '地点操作',
}

const ACTION_LABELS = {
  create_draft: '创建草稿',
  update: '更新',
  submit: '提交',
  status_change: '状态流转',
  review: '复核',
  attachment_registered: '登记附件',
  create: '创建',
  delete: '删除',
}

function renderDetails(item) {
  const d = item.details || {}
  if (item.type === 'attachment') {
    return (
      <span>
        文件：<strong>{d.file_name}</strong>
        {d.file_type && ` (${d.file_type})`}
        {d.storage_note && ` · ${d.storage_note}`}
      </span>
    )
  }
  if (item.type === 'review') {
    const conclusionMap = { approved: '通过', rejected: '驳回', needs_changes: '需修改' }
    return (
      <span>
        结论：<strong>{conclusionMap[d.conclusion] || d.conclusion}</strong>
        {d.comment && ` — ${d.comment}`}
      </span>
    )
  }
  if (d.from_status && d.to_status) {
    return <span>{d.from_status} → {d.to_status}{d.note ? `（${d.note}）` : ''}</span>
  }
  if (d.note) return <span>{d.note}</span>
  if (d.category && item.type === 'finding_created') {
    return (
      <span>
        分类：{d.category} · 风险：<RiskLabel level={d.risk_level} />
        {d.description && ` · ${d.description.slice(0, 60)}`}
      </span>
    )
  }
  if (d.changed_fields) return <span>变更字段：{d.changed_fields.join(', ')}</span>
  if (d.conclusion) return <span>结论：{d.conclusion}</span>
  return <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(d, null, 2)}</pre>
}

function typeDotClass(type) {
  switch (type) {
    case 'review': return 'review'
    case 'attachment': return 'attachment'
    case 'finding_created': return 'created'
    default: return ''
  }
}

export default function Timeline({ findingId, siteId }) {
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (findingId || siteId) loadTimeline()
  }, [findingId, siteId])

  async function loadTimeline() {
    setLoading(true)
    try {
      let data
      if (siteId) {
        data = await api.getSiteTimeline(siteId)
      } else {
        data = await api.getFindingTimeline(findingId)
      }
      setTimeline(data.timeline || [])
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div>加载中...</div>
  if (timeline.length === 0) return <div className="empty-state">暂无时间线事件</div>

  return (
    <div className="timeline">
      {timeline.map((item, idx) => (
        <div key={idx} className={`timeline-item ${typeDotClass(item.type)}`}>
          <div className="timeline-time">{item.timestamp}</div>
          <div className="timeline-title">
            {ACTION_LABELS[item.action] || TYPE_LABELS[item.type] || item.action}
            {item.actor && ` · ${item.actor}`}
            {item.finding_id && ` · 观察项 #${item.finding_id}`}
          </div>
          <div className="timeline-desc">{renderDetails(item)}</div>
        </div>
      ))}
    </div>
  )
}
