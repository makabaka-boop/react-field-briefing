import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { RISK_LEVELS, RISK_LABELS } from '../api/state'

export default function FindingForm({ siteId, finding, onSaved, onCancel }) {
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [riskLevel, setRiskLevel] = useState('low')
  const [reportedBy, setReportedBy] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  useEffect(() => {
    if (finding) {
      setCategory(finding.category || '')
      setDescription(finding.description || '')
      setRiskLevel(finding.risk_level || 'low')
      setReportedBy(finding.reported_by || '')
    }
  }, [finding])

  function clearError() {
    setError('')
    setFieldErrors({})
  }

  async function handleSubmit(e, action) {
    e.preventDefault()
    clearError()

    const localErrors = {}
    if (!category.trim()) localErrors.category = '分类不能为空'
    if (!description.trim()) localErrors.description = '描述不能为空'
    if (!riskLevel) localErrors.risk_level = '请选择风险等级'
    if (!reportedBy.trim()) localErrors.reported_by = '报告人不能为空'
    if (riskLevel && !RISK_LEVELS.includes(riskLevel)) localErrors.risk_level = '风险等级不合法'

    if (Object.keys(localErrors).length > 0) {
      setFieldErrors(localErrors)
      setError('请检查必填字段')
      return
    }

    setSubmitting(true)
    try {
      const payload = { category: category.trim(), description: description.trim(), risk_level: riskLevel, reported_by: reportedBy.trim() }
      let saved
      if (finding) {
        saved = await api.updateFinding(finding.id, payload)
      } else {
        payload.site_id = siteId
        saved = await api.createFinding(payload)
      }
      if (action === 'submit') {
        await api.submitFinding(saved.id, reportedBy.trim())
      }
      if (onSaved) onSaved()
    } catch (err) {
      setError(err.message || '提交失败，请重试')
      if (err.details && typeof err.details === 'object') {
        setFieldErrors(err.details)
      }
    } finally {
      setSubmitting(false)
    }
  }

  function fieldErrorClass(field) {
    return fieldErrors[field] ? 'input-error' : ''
  }

  return (
    <form>
      {error && (
        <div className="error-msg">
          <div style={{ fontWeight: 500, marginBottom: fieldErrors && Object.keys(fieldErrors).length > 0 ? 6 : 0 }}>
            {error}
          </div>
          {fieldErrors && Object.keys(fieldErrors).length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
              {Object.entries(fieldErrors).map(([k, v]) => (
                <li key={k}><strong>{k}</strong>: {v}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <div className="form-group">
        <label>分类 <span style={{ color: 'var(--danger)' }}>*</span></label>
        <input
          className={fieldErrorClass('category')}
          value={category}
          onChange={e => { setCategory(e.target.value); clearError() }}
          placeholder="如：安全、环境、质量"
        />
        {fieldErrors.category && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 4 }}>{fieldErrors.category}</div>}
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>风险等级 <span style={{ color: 'var(--danger)' }}>*</span></label>
          <select
            className={fieldErrorClass('risk_level')}
            value={riskLevel}
            onChange={e => { setRiskLevel(e.target.value); clearError() }}
          >
            {RISK_LEVELS.map(l => <option key={l} value={l}>{RISK_LABELS[l]}</option>)}
          </select>
          {fieldErrors.risk_level && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 4 }}>{fieldErrors.risk_level}</div>}
        </div>
        <div className="form-group">
          <label>报告人 <span style={{ color: 'var(--danger)' }}>*</span></label>
          <input
            className={fieldErrorClass('reported_by')}
            value={reportedBy}
            onChange={e => { setReportedBy(e.target.value); clearError() }}
          />
          {fieldErrors.reported_by && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 4 }}>{fieldErrors.reported_by}</div>}
        </div>
      </div>
      <div className="form-group">
        <label>描述 <span style={{ color: 'var(--danger)' }}>*</span></label>
        <textarea
          className={fieldErrorClass('description')}
          value={description}
          onChange={e => { setDescription(e.target.value); clearError() }}
          rows={4}
        />
        {fieldErrors.description && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 4 }}>{fieldErrors.description}</div>}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary" onClick={e => handleSubmit(e, 'save')} disabled={submitting}>
          保存草稿
        </button>
        <button className="btn" onClick={e => handleSubmit(e, 'submit')} disabled={submitting}>
          保存并提交
        </button>
        {onCancel && <button type="button" className="btn" onClick={onCancel} disabled={submitting}>取消</button>}
      </div>
    </form>
  )
}
