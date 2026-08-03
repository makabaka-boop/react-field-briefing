import { useEffect, useState } from 'react';
import {
  createProject,
  createProjectFromTemplate,
  listSiteTemplates,
} from '../api/client.js';

const EMPTY_FORM = {
  project_code: '',
  project_name: '',
  owner_name: '',
};

export default function ProjectCreatePage({ onCreated, onCancel }) {
  const [mode, setMode] = useState('normal');
  const [form, setForm] = useState(EMPTY_FORM);
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [createdProject, setCreatedProject] = useState(null);

  useEffect(() => {
    listSiteTemplates()
      .then((data) => setTemplates(data || []))
      .catch((err) => setError(err.message));
  }, []);

  const selectedTemplate = templates.find(
    (tpl) => String(tpl.id) === String(templateId)
  );

  const handleChange = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const base = {
        project_code: form.project_code.trim(),
        project_name: form.project_name.trim(),
        owner_name: form.owner_name.trim(),
      };
      const project =
        mode === 'template'
          ? await createProjectFromTemplate({
              ...base,
              template_id: Number(templateId),
            })
          : await createProject(base);
      setCreatedProject(project);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setCreatedProject(null);
    setForm(EMPTY_FORM);
    setTemplateId('');
    setError('');
  };

  // 创建结果页：展示项目信息与批量生成的地点，失败时停留在表单并展示错误
  if (createdProject) {
    const sites = createdProject.sites || [];
    return (
      <div className="card">
        <div className="card-title-row">
          <h3>创建成功</h3>
        </div>
        <div className="detail-grid">
          <div className="detail-item">
            <div className="detail-label">项目编号</div>
            <div className="detail-value">{createdProject.project_code}</div>
          </div>
          <div className="detail-item">
            <div className="detail-label">项目名称</div>
            <div className="detail-value">{createdProject.project_name}</div>
          </div>
          <div className="detail-item">
            <div className="detail-label">负责人</div>
            <div className="detail-value">{createdProject.owner_name}</div>
          </div>
          <div className="detail-item">
            <div className="detail-label">生成地点数</div>
            <div className="detail-value">{sites.length}</div>
          </div>
        </div>
        {sites.length > 0 && (
          <table className="data-table" style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>地点编号</th>
                <th>地点名称</th>
                <th>地址</th>
                <th>区域</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <tr key={site.id}>
                  <td>{site.site_code}</td>
                  <td>{site.site_name}</td>
                  <td>{site.address_text || '-'}</td>
                  <td>{site.region || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="form-actions" style={{ marginTop: 16 }}>
          <button
            className="btn btn-primary"
            onClick={() => onCreated(createdProject)}
          >
            进入项目
          </button>
          <button className="btn" onClick={handleReset}>
            继续创建
          </button>
          <button className="btn" onClick={onCancel}>
            返回列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title-row">
        <h3>新建项目</h3>
        <button className="btn" onClick={onCancel}>
          返回列表
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}

      <div className="filter-bar">
        <div className="form-row">
          <label>创建方式</label>
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="normal">普通创建</option>
            <option value="template">按模板创建</option>
          </select>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-row">
            <label>项目编号</label>
            <input
              value={form.project_code}
              onChange={handleChange('project_code')}
              required
            />
          </div>
          <div className="form-row">
            <label>项目名称</label>
            <input
              value={form.project_name}
              onChange={handleChange('project_name')}
              required
            />
          </div>
          <div className="form-row">
            <label>负责人</label>
            <input
              value={form.owner_name}
              onChange={handleChange('owner_name')}
              required
            />
          </div>
          {mode === 'template' && (
            <div className="form-row">
              <label>选择模板</label>
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                required
              >
                <option value="">请选择模板</option>
                {templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.template_name}（默认区域：{tpl.default_region || '-'}）
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {mode === 'template' && selectedTemplate && (
          <div className="card">
            <h3>模板地点预览（{selectedTemplate.site_items?.length || 0} 个地点）</h3>
            {selectedTemplate.site_items && selectedTemplate.site_items.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>地点编号</th>
                    <th>地点名称</th>
                    <th>地址</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedTemplate.site_items.map((item, index) => (
                    <tr key={index}>
                      <td>{item.site_code}</td>
                      <td>{item.site_name}</td>
                      <td>{item.address_text || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">该模板未配置地点</div>
            )}
          </div>
        )}
        {mode === 'template' && templates.length === 0 && (
          <div className="empty-state">
            暂无可用模板，请先在"模板管理"中创建模板
          </div>
        )}

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting || (mode === 'template' && !templateId)}
          >
            {submitting ? '创建中…' : '创建项目'}
          </button>
          <button type="button" className="btn" onClick={onCancel}>
            取消
          </button>
        </div>
      </form>
    </div>
  );
}
