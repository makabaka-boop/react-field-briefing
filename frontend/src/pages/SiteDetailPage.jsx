import { useCallback, useEffect, useState } from 'react';
import {
  createFinding,
  getSite,
  listFindings,
  updateFinding,
} from '../api/client.js';
import FindingsTable from '../components/FindingsTable.jsx';
import FindingForm from '../components/FindingForm.jsx';
import ReviewSidebar from '../components/ReviewSidebar.jsx';
import RiskFilter from '../components/RiskFilter.jsx';

export default function SiteDetailPage({ siteId, onBack }) {
  const [site, setSite] = useState(null);
  const [findings, setFindings] = useState([]);
  const [filters, setFilters] = useState({ finding_status: '', risk_level: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formMode, setFormMode] = useState(null); // null | 'create' | 'edit'
  const [editingFinding, setEditingFinding] = useState(null);
  const [selectedFinding, setSelectedFinding] = useState(null);

  const loadSite = useCallback(async () => {
    try {
      const data = await getSite(siteId);
      setSite(data);
    } catch (err) {
      setError(err.message);
    }
  }, [siteId]);

  const loadFindings = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listFindings({
        site_id: siteId,
        finding_status: filters.finding_status || undefined,
        risk_level: filters.risk_level || undefined,
      });
      setFindings(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [siteId, filters]);

  useEffect(() => {
    loadSite();
  }, [loadSite]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  const refreshSelectedFinding = async () => {
    await loadFindings();
    if (selectedFinding) {
      try {
        const data = await listFindings({ site_id: siteId });
        const fresh = (data || []).find((f) => f.id === selectedFinding.id);
        if (fresh) setSelectedFinding(fresh);
      } catch (err) {
        // 列表已刷新，选中项刷新失败时保留旧数据
      }
    }
  };

  const handleSelectFinding = (finding) => {
    setSelectedFinding(finding);
    if (finding.finding_status === 'draft') {
      setEditingFinding(finding);
      setFormMode('edit');
    } else {
      setFormMode(null);
      setEditingFinding(null);
    }
  };

  const handleFormSubmit = async (payload) => {
    if (formMode === 'edit' && editingFinding) {
      await updateFinding(editingFinding.id, payload);
    } else {
      await createFinding({ ...payload, site_id: siteId });
    }
    setFormMode(null);
    setEditingFinding(null);
    await loadFindings();
  };

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="card-title-row">
          <h3>地点详情</h3>
          <button className="btn" onClick={onBack}>
            返回项目
          </button>
        </div>
        {site ? (
          <div className="detail-grid">
            <div className="detail-item">
              <div className="detail-label">地点编号</div>
              <div className="detail-value">{site.site_code}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">地点名称</div>
              <div className="detail-value">{site.site_name}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">地址</div>
              <div className="detail-value">{site.address_text || '-'}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">区域</div>
              <div className="detail-value">{site.region || '-'}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">观察项数</div>
              <div className="detail-value">
                {site.findings?.length ?? '-'}
              </div>
            </div>
          </div>
        ) : (
          <div className="loading">加载中…</div>
        )}
      </div>

      <div className="split-layout">
        <div className="split-main">
          <div className="card">
            <div className="card-title-row">
              <h3>观察项</h3>
              <button
                className="btn btn-primary"
                onClick={() => {
                  setFormMode('create');
                  setEditingFinding(null);
                }}
              >
                新建观察项
              </button>
            </div>
            <RiskFilter filters={filters} onChange={setFilters} />
            {loading ? (
              <div className="loading">加载中…</div>
            ) : (
              <FindingsTable
                findings={findings}
                selectedId={selectedFinding?.id}
                onSelect={handleSelectFinding}
              />
            )}
          </div>

          {formMode && (
            <div className="card">
              <h3>
                {formMode === 'edit' ? '编辑观察项草稿' : '新建观察项草稿'}
              </h3>
              <FindingForm
                key={editingFinding?.id ?? 'create'}
                initialValues={editingFinding}
                onSubmit={handleFormSubmit}
                onCancel={() => {
                  setFormMode(null);
                  setEditingFinding(null);
                }}
              />
            </div>
          )}
        </div>

        {selectedFinding && (
          <ReviewSidebar
            key={selectedFinding.id}
            finding={selectedFinding}
            onClose={() => setSelectedFinding(null)}
            onChanged={refreshSelectedFinding}
          />
        )}
      </div>
    </div>
  );
}
