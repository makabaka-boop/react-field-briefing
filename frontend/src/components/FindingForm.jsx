import { useState } from 'react';
import { api, ApiError } from '../api/client.js';
import { RISK_LABELS, RISK_LEVELS } from '../state/statusMachine.js';

const EMPTY = {
  category: '',
  description: '',
  risk_level: 'low',
  reported_by: '',
};

// Draft observation form. On backend validation failure it surfaces the
// error message and per-field errors while preserving the user's input.
export default function FindingForm({ siteId, onSaved }) {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError('');
    try {
      const saved = await api.saveFindingDraft({ site_id: siteId, ...form });
      setForm(EMPTY); // reset only on success
      onSaved && onSaved(saved);
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
        // details.fields carries per-field messages from the backend
        setErrors(err.details?.fields || {});
      } else {
        setFormError('保存失败，请重试。');
      }
      // NOTE: form state is intentionally NOT reset so input is preserved
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={submit} data-testid="finding-form">
      <h3>新增观察项（草稿）</h3>
      {formError && <div className="form-error" role="alert">{formError}</div>}
      <div className="field">
        <label htmlFor="ff-category">类别 category</label>
        <input id="ff-category" value={form.category} onChange={set('category')} />
        {errors.category && <div className="field-error">{errors.category}</div>}
      </div>
      <div className="field">
        <label htmlFor="ff-description">描述 description</label>
        <textarea id="ff-description" rows={3} value={form.description} onChange={set('description')} />
        {errors.description && (
          <div className="field-error">{errors.description}</div>
        )}
      </div>
      <div className="field">
        <label htmlFor="ff-risk">风险等级 risk_level</label>
        <select id="ff-risk" value={form.risk_level} onChange={set('risk_level')}>
          {RISK_LEVELS.map((r) => (
            <option key={r} value={r}>{RISK_LABELS[r]}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="ff-reporter">报告人 reported_by</label>
        <input id="ff-reporter" value={form.reported_by} onChange={set('reported_by')} />
        {errors.reported_by && (
          <div className="field-error">{errors.reported_by}</div>
        )}
      </div>
      <button type="submit" disabled={busy}>
        {busy ? '保存中…' : '保存草稿'}
      </button>
    </form>
  );
}
