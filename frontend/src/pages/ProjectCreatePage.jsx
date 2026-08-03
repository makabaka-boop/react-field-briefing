import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'

export default function ProjectCreatePage() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState([])
  const [loadingTemplates, setLoadingTemplates] = useState(true)
  const [mode, setMode] = useState('manual')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [projectCode, setProjectCode] = useState('')
  const [projectName, setProjectName] = useState('')
  const [ownerName, setOwnerName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    api.listTemplates().then(data => {
      setTemplates(data)
      setLoadingTemplates(false)
    }).catch(() => setLoadingTemplates(false))
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      let res
      if (mode === 'template' && selectedTemplate) {
        res = await api.createProjectFromTemplate({
          project_code: projectCode,
          project_name: projectName,
          owner_name: ownerName,
          template_id: parseInt(selectedTemplate),
        })
      } else {
        res = await api.createProject({
          project_code: projectCode,
          project_name: projectName,
          owner_name: ownerName,
        })
      }
      setResult(res)
    } catch (err) {
      setError(err.message || '创建失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    const tpl = templates.find(t => t.id === (selectedTemplate ? parseInt(selectedTemplate) : null))
    return (
      <div>
        <h1 className="page-title">创建结果</h1>
        <div className="card" style={{ maxWidth: 600 }}>
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
            <h2 style={{ fontSize: 20, marginBottom: 8 }}>项目创建成功</h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              {result.project_name}（{result.project_code}）
            </p>
          </div>
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16, marginTop: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>项目编号</label>
                <div>{result.project_code}</div>
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>负责人</label>
                <div>{result.owner_name}</div>
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>初始状态</label>
                <div>{result.status}</div>
              </div>
              {result.sites_created !== undefined && (
                <div>
                  <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>批量生成地点</label>
                  <div><strong>{result.sites_created}</strong> 个</div>
                </div>
              )}
            </div>
            {result.site_codes && result.site_codes.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>地点清单</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                  {result.site_codes.map(code => (
                    <span key={code} className="badge badge-submitted">{code}</span>
                  ))}
                </div>
              </div>
            )}
            {result.template_name && (
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>使用模板</label>
                <div>{result.template_name}</div>
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
            <Link to={`/projects/${result.id}`} className="btn btn-primary">进入项目详情</Link>
            <button className="btn" onClick={() => navigate('/projects')}>返回项目列表</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">新建项目</h1>
      <div className="card" style={{ maxWidth: 600 }}>
        {error && <div className="error-msg">{error}</div>}

        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          <button
            className={`btn ${mode === 'manual' ? 'btn-primary' : ''}`}
            onClick={() => setMode('manual')}
            style={{ flex: 1 }}
          >
            手动创建
          </button>
          <button
            className={`btn ${mode === 'template' ? 'btn-primary' : ''}`}
            onClick={() => setMode('template')}
            style={{ flex: 1 }}
          >
            从模板创建
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>项目编号 *</label>
            <input value={projectCode} onChange={e => setProjectCode(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>项目名称 *</label>
            <input value={projectName} onChange={e => setProjectName(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>负责人 *</label>
            <input value={ownerName} onChange={e => setOwnerName(e.target.value)} required />
          </div>

          {mode === 'template' && (
            <div className="form-group">
              <label>选择模板 *</label>
              {loadingTemplates ? (
                <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>加载模板中...</div>
              ) : templates.length === 0 ? (
                <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                  暂无模板，请先到<Link to="/templates">模板管理</Link>创建
                </div>
              ) : (
                <select value={selectedTemplate} onChange={e => setSelectedTemplate(e.target.value)} required>
                  <option value="">请选择模板</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>
                      {t.template_name}（{t.site_items.length} 个地点{t.default_region ? ` · 默认区域：${t.default_region}` : ''}）
                    </option>
                  ))}
                </select>
              )}
              {selectedTemplate && (
                <div style={{ marginTop: 8, padding: 12, background: 'var(--bg)', borderRadius: 6, fontSize: 13 }}>
                  {(() => {
                    const tpl = templates.find(t => t.id === parseInt(selectedTemplate))
                    if (!tpl) return null
                    return (
                      <div>
                        <div style={{ marginBottom: 4 }}><strong>{tpl.site_items.length}</strong> 个地点将被自动创建：</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {tpl.site_items.map(item => (
                            <span key={item.site_code} className="badge badge-draft" style={{ fontSize: 11 }}>
                              {item.site_code}
                            </span>
                          ))}
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
          )}

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || (mode === 'template' && !selectedTemplate)}
            >
              {submitting ? '创建中...' : (mode === 'template' ? '创建项目并生成地点' : '创建项目')}
            </button>
            <button type="button" className="btn" onClick={() => navigate('/projects')}>取消</button>
          </div>
        </form>
      </div>
    </div>
  )
}
