import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client.js';
import FindingForm from '../components/FindingForm.jsx';
import FindingsTable from '../components/FindingsTable.jsx';
import ReviewSidebar from '../components/ReviewSidebar.jsx';
import RiskFilters from '../components/RiskFilters.jsx';

// Site detail brings together the findings table, the draft form, filter
// controls and the review sidebar for the selected finding.
export default function SiteDetail() {
  const { siteId } = useParams();
  const [site, setSite] = useState(null);
  const [findings, setFindings] = useState([]);
  const [filters, setFilters] = useState({ finding_status: '', risk_level: '' });
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');

  const loadFindings = useCallback(async () => {
    setError('');
    try {
      const res = await api.listFindings({
        site_id: siteId,
        finding_status: filters.finding_status,
        risk_level: filters.risk_level,
      });
      setFindings(res.items);
      // keep the selected finding fresh after a status change
      if (selected) {
        const updated = res.items.find((f) => f.id === selected.id);
        setSelected(updated || null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '加载失败');
    }
  }, [siteId, filters.finding_status, filters.risk_level, selected]);

  useEffect(() => {
    api.getSite(siteId).then(setSite).catch(() => {});
  }, [siteId]);

  useEffect(() => {
    loadFindings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId, filters.finding_status, filters.risk_level]);

  return (
    <div>
      <div className="card">
        <h2>
          {site ? `${site.site_name} (${site.site_code})` : '地点详情'}
        </h2>
        {site && <p className="muted">区域：{site.region || '—'} · 地址：{site.address_text || '—'}</p>}
      </div>
      {error && <div className="form-error" role="alert">{error}</div>}

      <div className="detail-layout">
        <div className="detail-main">
          <div className="card">
            <h3>观察项</h3>
            <RiskFilters
              value={filters}
              onChange={setFilters}
              regions={site && site.region ? [site.region] : []}
            />
            <FindingsTable
              findings={findings}
              onSelect={setSelected}
              selectedId={selected && selected.id}
            />
          </div>
          <FindingForm siteId={Number(siteId)} onSaved={loadFindings} />
        </div>
        <ReviewSidebar finding={selected} onChanged={loadFindings} />
      </div>
    </div>
  );
}
