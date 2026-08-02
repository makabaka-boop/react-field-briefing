import { useCallback, useEffect, useState } from 'react';
import { createSiteTemplate, listSiteTemplates } from '../api/client.js';

const EMPTY_ITEM = { site_code: '', site_name: '', address_text: '' };

export default function TemplateManagePage() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [defaultRegion, setDefaultRegion] = useState('');
  const [siteItems, setSiteItems] = useState([{ ...EMPTY_ITEM }]);
  const [submitting, setSubmitting] = useState(false);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listSiteTemplates();
      setTemplates(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleItemChange = (index, key) => (event) => {
    setSiteItems((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, [key]: event.target.value } : item
      )
    );
  };

  const addItem = () => {
    setSiteItems((prev) => [...prev, { ...EMPTY_ITEM }]);
  };

  const removeItem = (index) => {
    setSiteItems((prev) => prev.filter((_, i) => i !== index));
  };

  const resetForm = () => {
    setTemplateName('');
    setDefaultRegion('');
    setSiteItems([{ ...EMPTY_ITEM }]);
    setShowForm(false);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const items = siteItems
        .map((item) => ({
          site_code: item.site_code.trim(),
          site_name: item.site_name.trim(),
          address_text: item.address_text.trim(),
        }))
        .filter((item) => item.site_code && item.site_name);
      await createSiteTemplate({
        template_name: templateName.trim(),
        default_region: defaultRegion.trim(),
        site_items: items,
      });
      resetForm();
      await loadTemplates();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="card-title-row">
          <h3>模板列表</h3>
          <button
            className="btn btn-primary"
            onClick={() => setShowForm((prev) => !prev)}
          >
            {showForm ? '收起表单' : '创建模板'}
          </button>
        </div>
        {loading ? (
          <div className="loading">加载中…</div>
        ) : templates.length === 0 ? (
          <div className="empty-state">暂无模板，请先创建</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>模板名称</th>
                <th>默认区域</th>
                <th>地点数</th>
                <th>地点明细</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((tpl) => (
                <tr key={tpl.id}>
                  <td>{tpl.template_name}</td>
                  <td>{tpl.default_region || '-'}</td>
                  <td>{tpl.site_items?.length || 0}</td>
                  <td>
                    {(tpl.site_items || [])
                      .map((item) => `${item.site_code} ${item.site_name}`)
                      .join('；') || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showForm && (
        <div className="card">
          <h3>创建模板</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-row">
                <label>模板名称</label>
                <input
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  required
                />
              </div>
              <div className="form-row">
                <label>默认区域</label>
                <input
                  value={defaultRegion}
                  onChange={(e) => setDefaultRegion(e.target.value)}
                  placeholder="如：华东 / 北区"
                />
              </div>
            </div>

            <div className="form-row">
              <label>地点明细（site_items）</label>
              {siteItems.map((item, index) => (
                <div className="site-item-row" key={index}>
                  <input
                    value={item.site_code}
                    onChange={handleItemChange(index, 'site_code')}
                    placeholder="地点编号"
                    required
                  />
                  <input
                    value={item.site_name}
                    onChange={handleItemChange(index, 'site_name')}
                    placeholder="地点名称"
                    required
                  />
                  <input
                    value={item.address_text}
                    onChange={handleItemChange(index, 'address_text')}
                    placeholder="地址"
                  />
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => removeItem(index)}
                    disabled={siteItems.length === 1}
                  >
                    删除
                  </button>
                </div>
              ))}
              <button type="button" className="btn btn-sm" onClick={addItem}>
                + 添加地点行
              </button>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting}
              >
                {submitting ? '提交中…' : '保存模板'}
              </button>
              <button type="button" className="btn" onClick={resetForm}>
                取消
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
