import { useState } from 'react';
import { RISK_LEVELS, riskLabel } from '../stateMachine.js';

const EMPTY_FORM = {
  category: '',
  description: '',
  risk_level: 'low',
  reported_by: '',
};

export default function FindingForm({ initialValues, onSubmit, onCancel }) {
  const [form, setForm] = useState(() => ({
    category: initialValues?.category || EMPTY_FORM.category,
    description: initialValues?.description || EMPTY_FORM.description,
    risk_level: initialValues?.risk_level || EMPTY_FORM.risk_level,
    reported_by: initialValues?.reported_by || EMPTY_FORM.reported_by,
  }));
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isEdit = Boolean(initialValues && initialValues.id);

  const handleChange = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const payload = {
      category: form.category.trim(),
      description: form.description.trim(),
      risk_level: form.risk_level,
    };
    if (!isEdit) {
      payload.reported_by = form.reported_by.trim();
    }
    setError('');
    setSubmitting(true);
    try {
      await onSubmit(payload);
    } catch (err) {
      // 提交失败：展示后端统一错误中的 message，已输入内容保留在 form state 中
      setError(err.message || '提交失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      <div className="form-row">
        <label htmlFor="finding-category">类别</label>
        <input
          id="finding-category"
          value={form.category}
          onChange={handleChange('category')}
          placeholder="如：安全 / 质量 / 环境"
          required
        />
      </div>
      <div className="form-row">
        <label htmlFor="finding-description">描述</label>
        <textarea
          id="finding-description"
          value={form.description}
          onChange={handleChange('description')}
          placeholder="现场观察到的问题或情况"
          required
        />
      </div>
      <div className="form-row">
        <label htmlFor="finding-risk-level">风险等级</label>
        <select
          id="finding-risk-level"
          value={form.risk_level}
          onChange={handleChange('risk_level')}
        >
          {RISK_LEVELS.map((level) => (
            <option key={level} value={level}>
              {riskLabel(level)}
            </option>
          ))}
        </select>
      </div>
      {!isEdit && (
        <div className="form-row">
          <label htmlFor="finding-reported-by">填报人</label>
          <input
            id="finding-reported-by"
            value={form.reported_by}
            onChange={handleChange('reported_by')}
            placeholder="填报人姓名"
            required
          />
        </div>
      )}
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? '提交中…' : isEdit ? '保存修改' : '创建草稿'}
        </button>
        {onCancel && (
          <button type="button" className="btn" onClick={onCancel}>
            取消
          </button>
        )}
      </div>
    </form>
  );
}
