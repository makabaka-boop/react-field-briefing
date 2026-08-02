import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function TemplateManagePage() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [defaultRegion, setDefaultRegion] = useState('')
  const [siteItems, setSiteItems] = useState([
    { site_code: '', site_name: '', address_text: '', region: '' },
  ])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => { loadTemplates() }, [])

  async function loadTemplates() {
    try {
      const data = await api.listTemplates()
      setTemplates(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function addSiteItem() {
    setSiteItems([...siteItems, { site_code: '', site_name: '', address_text: '', region: '' }])
  }

  function updateSiteItem(idx, field, value) {
    const updated = [...siteItems]
    updated[idx][field] = value
    setSiteItems(updated)
  }

  function removeSiteItem(idx) {
    setSiteItems(siteItems.filter((_, i) => i !== idx))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      const validItems = siteItems.filter(s => s.site_code && s.site_name)
      await api.createTemplate({
        template_name: templateName,
        default_region: defaultRegion,
        site_items: validItems,
      })
      setTemplateName('')
      setDefaultRegion('')
      setSiteItems([{ site_code: '', site_name: '', address_text: '', region: '' }])
      setShowForm(false)
      setSuccess('模板创建成功')
      await loadTemplates()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDelete(id) {
    if (!confirm('确定删除此模板？')) return
    try {
      await api.deleteTemplate(id)
      await loadTemplates()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>模板管理</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? '取消' : '+ 新建模板'}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">{success}</div>}

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ marginBottom: 16 }}>新建模板</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>模板名称 *</label>
                <input value={templateName} onChange={e => setTemplateName(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>默认区域</label>
                <input value={defaultRegion} onChange={e => setDefaultRegion(e.target.value)} />
              </div>
            </div>

            <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>地点清单</label>
            {siteItems.map((item, idx) => (
              <div key={idx} className="site-items-editor">
                <div className="site-item-row">
                  <input placeholder="地点编号 *" value={item.site_code} onChange={e => updateSiteItem(idx, 'site_code', e.target.value)} />
                  <input placeholder="地点名称 *" value={item.site_name} onChange={e => updateSiteItem(idx, 'site_name', e.target.value)} />
                  <input placeholder="地址" value={item.address_text} onChange={e => updateSiteItem(idx, 'address_text', e.target.value)} />
                  <button type="button" className="btn btn-sm btn-danger" onClick={() => removeSiteItem(idx)}>删除</button>
                </div>
                <div className="site-item-row">
                  <input placeholder="区域（留空使用默认）" value={item.region} onChange={e => updateSiteItem(idx, 'region', e.target.value)} />
                </div>
              </div>
            ))}
            <button type="button" className="btn btn-sm" onClick={addSiteItem} style={{ marginBottom: 16 }}>+ 添加地点</button>

            <div>
              <button type="submit" className="btn btn-primary">保存模板</button>
            </div>
          </form>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center' }}>加载中...</div>
        ) : templates.length === 0 ? (
          <div className="empty-state">暂无模板，点击上方按钮创建</div>
        ) : (
          <div style={{ padding: 16 }}>
            {templates.map(t => (
              <div key={t.id} className="template-item">
                <div>
                  <div style={{ fontWeight: 500 }}>{t.template_name}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    默认区域：{t.default_region || '无'} · {t.site_items.length} 个地点
                  </div>
                  {t.site_items.length > 0 && (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                      {t.site_items.slice(0, 5).map(s => s.site_name).join('、')}
                      {t.site_items.length > 5 && ' ...'}
                    </div>
                  )}
                </div>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(t.id)}>删除</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
