import { useCallback, useEffect, useState } from 'react';
import { createSite, getProject, listSites, updateSite } from '../api/client.js';

const EMPTY_SITE_FORM = {
  site_code: '',
  site_name: '',
  address_text: '',
  region: '',
};

export default function ProjectDetailPage({ projectId, onOpenSite }) {
  const [project, setProject] = useState(null);
  const [sites, setSites] = useState([]);
  const [regionFilter, setRegionFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingSite, setEditingSite] = useState(null);
  const [siteForm, setSiteForm] = useState(EMPTY_SITE_FORM);
  const [submitting, setSubmitting] = useState(false);

  const loadProject = useCallback(async () => {
    try {
      const data = await getProject(projectId);
      setProject(data);
    } catch (err) {
      setError(err.message);
    }
  }, [projectId]);

  const loadSites = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listSites({
        project_id: projectId,
        region: regionFilter || undefined,
      });
      setSites(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId, regionFilter]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  useEffect(() => {
    loadSites();
  }, [loadSites]);

  const openCreateForm = () => {
    setEditingSite(null);
    setSiteForm(EMPTY_SITE_FORM);
    setShowForm(true);
  };

  const openEditForm = (site) => {
    setEditingSite(site);
    setSiteForm({
      site_code: site.site_code,
      site_name: site.site_name,
      address_text: site.address_text || '',
      region: site.region || '',
    });
    setShowForm(true);
  };

  const handleChange = (key) => (event) => {
    setSiteForm((prev) => ({ ...prev, [key]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      if (editingSite) {
        await updateSite(editingSite.id, {
          site_name: siteForm.site_name.trim(),
          address_text: siteForm.address_text.trim(),
          region: siteForm.region.trim(),
        });
      } else {
        await createSite({
          site_code: siteForm.site_code.trim(),
          site_name: siteForm.site_name.trim(),
          address_text: siteForm.address_text.trim(),
          region: siteForm.region.trim(),
          project_id: projectId,
        });
      }
      setShowForm(false);
      setEditingSite(null);
      setSiteForm(EMPTY_SITE_FORM);
      await Promise.all([loadSites(), loadProject()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}

      {project && (
        <div className="card">
          <h3>项目信息</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <div className="detail-label">项目编号</div>
              <div className="detail-value">{project.project_code}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">项目名称</div>
              <div className="detail-value">{project.project_name}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">负责人</div>
              <div className="detail-value">{project.owner_name}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">地点数</div>
              <div className="detail-value">{project.sites?.length ?? '-'}</div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title-row">
          <h3>地点列表</h3>
          <button className="btn btn-primary" onClick={openCreateForm}>
            新建地点
          </button>
        </div>
        <div className="filter-bar">
          <div className="form-row">
            <label>按区域过滤</label>
            <input
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              placeholder="输入区域关键字"
            />
          </div>
        </div>
        {loading ? (
          <div className="loading">加载中…</div>
        ) : sites.length === 0 ? (
          <div className="empty-state">暂无地点，可点击"新建地点"添加</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>地点编号</th>
                <th>地点名称</th>
                <th>地址</th>
                <th>区域</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <tr key={site.id}>
                  <td>{site.site_code}</td>
                  <td>{site.site_name}</td>
                  <td>{site.address_text || '-'}</td>
                  <td>{site.region || '-'}</td>
                  <td>
                    <button
                      className="btn btn-sm"
                      onClick={() => onOpenSite(site.id)}
                    >
                      进入地点
                    </button>{' '}
                    <button
                      className="btn btn-sm"
                      onClick={() => openEditForm(site)}
                    >
                      编辑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showForm && (
        <div className="card">
          <h3>{editingSite ? '编辑地点' : '新建地点'}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-row">
                <label>地点编号</label>
                <input
                  value={siteForm.site_code}
                  onChange={handleChange('site_code')}
                  disabled={Boolean(editingSite)}
                  required
                />
              </div>
              <div className="form-row">
                <label>地点名称</label>
                <input
                  value={siteForm.site_name}
                  onChange={handleChange('site_name')}
                  required
                />
              </div>
              <div className="form-row">
                <label>地址</label>
                <input
                  value={siteForm.address_text}
                  onChange={handleChange('address_text')}
                />
              </div>
              <div className="form-row">
                <label>区域</label>
                <input
                  value={siteForm.region}
                  onChange={handleChange('region')}
                />
              </div>
            </div>
            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting}
              >
                {submitting ? '提交中…' : editingSite ? '保存修改' : '创建地点'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setShowForm(false);
                  setEditingSite(null);
                }}
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
