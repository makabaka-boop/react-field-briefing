import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client.js';

const EMPTY_TEMPLATE = {
  template_name: '',
  default_region: '',
  site_items: [{ site_code: '', site_name: '', region: '' }],
};

export default function TemplateManager() {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState(EMPTY_TEMPLATE);
  const [error, setError] = useState('');
  const [useForProject, setUseForProject] = useState({});
  const navigate = useNavigate();

  async function load() {
    const res = await api.listTemplates();
    setTemplates(res.items);
  }
  useEffect(() => { load(); }, []);

  const setField = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  function setItem(idx, key, val) {
    const items = form.site_items.map((it, i) =>
      i === idx ? { ...it, [key]: val } : it,
    );
    setForm({ ...form, site_items: items });
  }
  const addItem = () =>
    setForm({ ...form, site_items: [...form.site_items, { site_code: '', site_name: '', region: '' }] });
  const removeItem = (idx) =>
    setForm({ ...form, site_items: form.site_items.filter((_, i) => i !== idx) });

  async function createTemplate(e) {
    e.preventDefault();
    setError('');
    try {
      // strip blank region so backend default applies
      const site_items = form.site_items.map((it) => {
        const clean = { site_code: it.site_code, site_name: it.site_name };
        if (it.region) clean.region = it.region;
        return clean;
      });
      await api.createTemplate({ ...form, site_items });
      setForm(EMPTY_TEMPLATE);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '创建失败');
    }
  }

  async function instantiate(tpl) {
    setError('');
    const payload = useForProject[tpl.id];
    if (!payload || !payload.project_code) {
      setError('请填写项目编号后再按模板创建。');
      return;
    }
    try {
      const project = await api.createProjectFromTemplate(tpl.id, payload);
      // Land on a dedicated result page that re-reads the committed project
      // and its generated sites from the backend.
      navigate(
        `/templates/result/${project.id}?template=${encodeURIComponent(tpl.template_name)}`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '创建失败');
    }
  }

  return (
    <div>
      {error && <div className="form-error" role="alert">{error}</div>}
      <form className="card" onSubmit={createTemplate} data-testid="template-form">
        <h2>新建模板</h2>
        <div className="row">
          <div className="col field">
            <label>模板名称 template_name</label>
            <input value={form.template_name} onChange={setField('template_name')} />
          </div>
          <div className="col field">
            <label>默认区域 default_region</label>
            <input value={form.default_region} onChange={setField('default_region')} />
          </div>
        </div>
        <h4>地点清单 site_items</h4>
        {form.site_items.map((it, idx) => (
          <div className="row" key={idx} style={{ alignItems: 'flex-end' }}>
            <div className="col field">
              <label>site_code</label>
              <input value={it.site_code} onChange={(e) => setItem(idx, 'site_code', e.target.value)} />
            </div>
            <div className="col field">
              <label>site_name</label>
              <input value={it.site_name} onChange={(e) => setItem(idx, 'site_name', e.target.value)} />
            </div>
            <div className="col field">
              <label>region（可选）</label>
              <input value={it.region} onChange={(e) => setItem(idx, 'region', e.target.value)} />
            </div>
            <button type="button" className="secondary" onClick={() => removeItem(idx)}>删除</button>
          </div>
        ))}
        <button type="button" className="secondary" onClick={addItem}>+ 添加地点</button>{' '}
        <button type="submit">保存模板</button>
      </form>

      <div className="card">
        <h2>模板列表</h2>
        {!templates.length && <p className="muted">暂无模板。</p>}
        {templates.map((tpl) => (
          <div key={tpl.id} className="card">
            <h3>{tpl.template_name} <span className="muted">（默认区域：{tpl.default_region || '—'}）</span></h3>
            <p className="muted">包含 {tpl.site_items.length} 个地点：{tpl.site_items.map((s) => s.site_code).join(', ')}</p>
            <div className="row" style={{ alignItems: 'flex-end' }}>
              <div className="col field">
                <label>project_code</label>
                <input
                  onChange={(e) => setUseForProject({ ...useForProject, [tpl.id]: { ...useForProject[tpl.id], project_code: e.target.value } })}
                />
              </div>
              <div className="col field">
                <label>project_name</label>
                <input
                  onChange={(e) => setUseForProject({ ...useForProject, [tpl.id]: { ...useForProject[tpl.id], project_name: e.target.value } })}
                />
              </div>
              <div className="col field">
                <label>owner_name</label>
                <input
                  onChange={(e) => setUseForProject({ ...useForProject, [tpl.id]: { ...useForProject[tpl.id], owner_name: e.target.value } })}
                />
              </div>
              <button onClick={() => instantiate(tpl)}>按模板创建项目</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
