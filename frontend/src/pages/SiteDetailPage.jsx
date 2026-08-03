import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import FindingTable from '../components/FindingTable'
import FindingForm from '../components/FindingForm'
import ReviewSidebar from '../components/ReviewSidebar'
import Timeline from '../components/Timeline'
import RiskFilters from '../components/RiskFilters'

export default function SiteDetailPage() {
  const { id } = useParams()
  const [site, setSite] = useState(null)
  const [project, setProject] = useState(null)
  const [findings, setFindings] = useState([])
  const [filters, setFilters] = useState({})
  const [tab, setTab] = useState('findings')
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ site_name: '', address_text: '', region: '' })
  const [showFindingForm, setShowFindingForm] = useState(false)
  const [editingFinding, setEditingFinding] = useState(null)
  const [reviewFindingId, setReviewFindingId] = useState(null)
  const [timelineFindingId, setTimelineFindingId] = useState(null)
  const [showAttachForm, setShowAttachForm] = useState(false)
  const [attachForm, setAttachForm] = useState({ file_name: '', file_type: '', storage_note: '', linked_finding_id: '' })
  const [error, setError] = useState('')

  useEffect(() => { loadAll() }, [id])
  useEffect(() => { loadFindings() }, [id, filters])

  async function loadAll() {
    try {
      const s = await api.getSite(id)
      setSite(s)
      setEditForm({ site_name: s.site_name, address_text: s.address_text, region: s.region })
      const p = await api.getProject(s.project_id)
      setProject(p)
      loadFindings()
    } catch (e) {
      setError(e.message)
    }
  }

  async function loadFindings() {
    try {
      const params = { site_id: id }
      if (filters.finding_status) params.finding_status = filters.finding_status
      if (filters.risk_level) params.risk_level = filters.risk_level
      const data = await api.listFindings(params)
      setFindings(data)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleSaveSite() {
    try {
      const updated = await api.updateSite(id, editForm)
      setSite(updated)
      setEditing(false)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleFindingTransition(f, target) {
    try {
      await api.transitionFinding(f.id, target)
      await loadFindings()
    } catch (e) {
      setError(e.message)
    }
  }

  function handleNewFinding() {
    setEditingFinding(null)
    setShowFindingForm(true)
  }

  function handleEditFinding(f) {
    setEditingFinding(f)
    setShowFindingForm(true)
  }

  async function handleAddAttachment(e) {
    e.preventDefault()
    setError('')
    try {
      await api.createAttachment({
        ...attachForm,
        linked_finding_id: attachForm.linked_finding_id ? parseInt(attachForm.linked_finding_id) : null,
      })
      setAttachForm({ file_name: '', file_type: '', storage_note: '', linked_finding_id: '' })
      setShowAttachForm(false)
    } catch (e) {
      setError(e.message)
    }
  }

  if (!site) return <div>加载中...</div>

  return (
    <div>
      <Link to={`/projects/${site.project_id}`} className="back-link">← 返回项目</Link>

      {error && <div className="error-msg">{error}</div>}

      <div className="card">
        <div className="site-detail-header">
          {editing ? (
            <div style={{ flex: 1, maxWidth: 500 }}>
              <div className="form-group">
                <label>地点名称</label>
                <input value={editForm.site_name} onChange={e => setEditForm({ ...editForm, site_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>地址</label>
                <input value={editForm.address_text} onChange={e => setEditForm({ ...editForm, address_text: e.target.value })} />
              </div>
              <div className="form-group">
                <label>区域</label>
                <input value={editForm.region} onChange={e => setEditForm({ ...editForm, region: e.target.value })} />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary" onClick={handleSaveSite}>保存</button>
                <button className="btn" onClick={() => setEditing(false)}>取消</button>
              </div>
            </div>
          ) : (
            <div>
              <h1 style={{ fontSize: 22 }}>{site.site_name}</h1>
              <div className="site-meta" style={{ marginTop: 12 }}>
                <div className="site-meta-item">
                  <label>地点编号</label>
                  <span>{site.site_code}</span>
                </div>
                <div className="site-meta-item">
                  <label>所属项目</label>
                  <span>{project?.project_name || site.project_id}</span>
                </div>
                <div className="site-meta-item">
                  <label>区域</label>
                  <span>{site.region || '-'}</span>
                </div>
                <div className="site-meta-item">
                  <label>地址</label>
                  <span>{site.address_text || '-'}</span>
                </div>
              </div>
            </div>
          )}
          {!editing && (
            <button className="btn" onClick={() => setEditing(true)}>编辑地点</button>
          )}
        </div>
      </div>

      <div className="tabs">
        <div className={`tab ${tab === 'findings' ? 'active' : ''}`} onClick={() => setTab('findings')}>观察项 ({findings.length})</div>
        <div className={`tab ${tab === 'timeline' ? 'active' : ''}`} onClick={() => setTab('timeline')}>地点时间线</div>
      </div>

      {tab === 'findings' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn" onClick={() => setShowAttachForm(!showAttachForm)}>登记附件</button>
            </div>
            <button className="btn btn-primary" onClick={handleNewFinding}>+ 新建观察项</button>
          </div>

          {showAttachForm && (
            <div className="card" style={{ marginBottom: 16 }}>
              <h3 style={{ marginBottom: 12, fontSize: 15 }}>登记附件元数据</h3>
              <form onSubmit={handleAddAttachment}>
                <div className="form-row">
                  <div className="form-group">
                    <label>文件名 *</label>
                    <input value={attachForm.file_name} onChange={e => setAttachForm({ ...attachForm, file_name: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label>文件类型</label>
                    <input value={attachForm.file_type} onChange={e => setAttachForm({ ...attachForm, file_type: e.target.value })} placeholder="如 image/jpeg" />
                  </div>
                </div>
                <div className="form-group">
                  <label>存储位置备注</label>
                  <input value={attachForm.storage_note} onChange={e => setAttachForm({ ...attachForm, storage_note: e.target.value })} placeholder="如 s3://bucket/photo.jpg" />
                </div>
                <div className="form-group">
                  <label>关联观察项ID</label>
                  <select value={attachForm.linked_finding_id} onChange={e => setAttachForm({ ...attachForm, linked_finding_id: e.target.value })}>
                    <option value="">不关联</option>
                    {findings.map(f => <option key={f.id} value={f.id}>#{f.id} - {f.description.slice(0, 30)}</option>)}
                  </select>
                </div>
                <button type="submit" className="btn btn-primary">保存附件记录</button>
              </form>
            </div>
          )}

          <RiskFilters filters={filters} onChange={setFilters} />

          <div className="card" style={{ padding: 0 }}>
            <FindingTable
              findings={findings}
              onEdit={handleEditFinding}
              onReview={f => setReviewFindingId(f.id)}
              onTransition={handleFindingTransition}
              onViewTimeline={f => setTimelineFindingId(f.id)}
            />
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>地点活动时间线</h3>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
            合并展示该地点下所有观察项的创建、状态流转、复核结论和附件登记记录，按时间排序。
          </p>
          <Timeline siteId={parseInt(id)} />
        </div>
      )}

      {showFindingForm && (
        <div className="sidebar-overlay" onClick={() => setShowFindingForm(false)}>
          <div className="sidebar-panel" onClick={e => e.stopPropagation()}>
            <div className="sidebar-header">
              <h2>{editingFinding ? '编辑观察项' : '新建观察项'}</h2>
              <button className="btn btn-sm" onClick={() => setShowFindingForm(false)}>关闭</button>
            </div>
            <FindingForm
              siteId={parseInt(id)}
              finding={editingFinding}
              onSaved={() => { setShowFindingForm(false); loadFindings() }}
              onCancel={() => setShowFindingForm(false)}
            />
          </div>
        </div>
      )}

      {reviewFindingId && (
        <ReviewSidebar
          findingId={reviewFindingId}
          onClose={() => setReviewFindingId(null)}
          onReviewed={() => loadFindings()}
        />
      )}

      {timelineFindingId && (
        <div className="sidebar-overlay" onClick={() => setTimelineFindingId(null)}>
          <div className="sidebar-panel" onClick={e => e.stopPropagation()}>
            <div className="sidebar-header">
              <h2>观察项时间线</h2>
              <button className="btn btn-sm" onClick={() => setTimelineFindingId(null)}>关闭</button>
            </div>
            <Timeline findingId={timelineFindingId} />
          </div>
        </div>
      )}
    </div>
  )
}
