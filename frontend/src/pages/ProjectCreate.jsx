import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client.js';

const EMPTY = { project_code: '', project_name: '', owner_name: '' };

export default function ProjectCreate() {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError('');
    try {
      const p = await api.createProject(form);
      navigate(`/projects/${p.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
        setErrors(err.details?.fields || {});
      } else {
        setFormError('创建失败');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={submit} data-testid="project-create">
      <h2>新建项目</h2>
      <p className="muted">
        需要按标准清单批量生成地点？{' '}
        <Link to="/templates">前往模板管理，按模板创建项目 →</Link>
      </p>
      {formError && <div className="form-error" role="alert">{formError}</div>}
      <div className="field">
        <label>项目编号 project_code</label>
        <input value={form.project_code} onChange={set('project_code')} />
        {errors.project_code && <div className="field-error">{errors.project_code}</div>}
      </div>
      <div className="field">
        <label>项目名称 project_name</label>
        <input value={form.project_name} onChange={set('project_name')} />
        {errors.project_name && <div className="field-error">{errors.project_name}</div>}
      </div>
      <div className="field">
        <label>负责人 owner_name</label>
        <input value={form.owner_name} onChange={set('owner_name')} />
        {errors.owner_name && <div className="field-error">{errors.owner_name}</div>}
      </div>
      <button type="submit" disabled={busy}>{busy ? '创建中…' : '创建项目'}</button>
    </form>
  );
}
