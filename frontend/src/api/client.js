const BASE = '/api/v1';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let body = {};
    try { body = await res.json(); } catch (e) {}
    const err = new Error(body.message || `HTTP ${res.status}`);
    err.error_code = body.error_code;
    err.details = body.details;
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  health: () => request('/health'),

  listProjects: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/projects${q ? `?${q}` : ''}`);
  },
  createProject: (data) => request('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id) => request(`/projects/${id}`),
  updateProject: (id, data) => request(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  transitionProject: (id, targetStatus, actor = '') =>
    request(`/projects/${id}/transition`, { method: 'POST', body: JSON.stringify({ target_status: targetStatus, actor }) }),
  createProjectFromTemplate: (data) => request('/projects/from-template', { method: 'POST', body: JSON.stringify(data) }),

  listSites: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/sites${q ? `?${q}` : ''}`);
  },
  createSite: (data) => request('/sites', { method: 'POST', body: JSON.stringify(data) }),
  getSite: (id) => request(`/sites/${id}`),
  updateSite: (id, data) => request(`/sites/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSite: (id) => request(`/sites/${id}`, { method: 'DELETE' }),
  getSiteTimeline: (id) => request(`/sites/${id}/timeline`),

  listFindings: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/findings${q ? `?${q}` : ''}`);
  },
  createFinding: (data) => request('/findings', { method: 'POST', body: JSON.stringify(data) }),
  getFinding: (id) => request(`/findings/${id}`),
  updateFinding: (id, data) => request(`/findings/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  saveDraft: (id, data) => request(`/findings/${id}/save-draft`, { method: 'POST', body: JSON.stringify(data) }),
  submitFinding: (id, actor = '') => request(`/findings/${id}/submit`, { method: 'POST', body: JSON.stringify({ actor }) }),
  transitionFinding: (id, targetStatus, actor = '') =>
    request(`/findings/${id}/transition`, { method: 'POST', body: JSON.stringify({ target_status: targetStatus, actor }) }),
  getFindingTimeline: (id) => request(`/findings/${id}/timeline`),

  listTemplates: () => request('/templates'),
  createTemplate: (data) => request('/templates', { method: 'POST', body: JSON.stringify(data) }),
  getTemplate: (id) => request(`/templates/${id}`),
  deleteTemplate: (id) => request(`/templates/${id}`, { method: 'DELETE' }),

  listAttachments: (findingId) => request(`/attachments?linked_finding_id=${findingId}`),
  createAttachment: (data) => request('/attachments', { method: 'POST', body: JSON.stringify(data) }),
  deleteAttachment: (id) => request(`/attachments/${id}`, { method: 'DELETE' }),

  listReviews: (findingId) => request(`/findings/${findingId}/reviews`),
  createReview: (findingId, data) => request(`/findings/${findingId}/reviews`, { method: 'POST', body: JSON.stringify(data) }),

  listAuditEvents: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/audit-events${q ? `?${q}` : ''}`);
  },

  getRiskOverview: (projectId) => request(`/overview/risk${projectId ? `?project_id=${projectId}` : ''}`),
  getProjectSitesRisk: (projectId) => request(`/projects/${projectId}/sites-risk`),
  runSystemCheck: () => request('/system/check'),
};
