// Thin API client for the field briefing backend.
// Centralizes the /api/v1 base path, JSON handling, and error normalization
// so components can `await api.createProject(...)` and catch a typed error.

const BASE = '/api/v1';

export class ApiError extends Error {
  constructor(errorCode, message, details, status) {
    super(message || errorCode);
    this.errorCode = errorCode;
    this.details = details || {};
    this.status = status;
  }
}

async function request(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = data || {};
    throw new ApiError(
      err.error_code || 'error',
      err.message || 'Request failed',
      err.details,
      res.status,
    );
  }
  return data;
}

function qs(params) {
  const filtered = Object.entries(params || {}).filter(
    ([, v]) => v !== undefined && v !== null && v !== '',
  );
  if (!filtered.length) return '';
  const usp = new URLSearchParams();
  filtered.forEach(([k, v]) => usp.append(k, v));
  return `?${usp.toString()}`;
}

export const api = {
  // projects
  listProjects: (params) => request('GET', `/projects${qs(params)}`),
  getProject: (id) => request('GET', `/projects/${id}`),
  createProject: (body) => request('POST', '/projects', body),
  transitionProject: (id, body) =>
    request('POST', `/projects/${id}/status`, body),
  projectSiteRisk: (id) => request('GET', `/projects/${id}/site_risk`),

  // sites
  listSites: (params) => request('GET', `/sites${qs(params)}`),
  getSite: (id) => request('GET', `/sites/${id}`),
  createSite: (body) => request('POST', '/sites', body),

  // templates
  listTemplates: () => request('GET', '/templates'),
  getTemplate: (id) => request('GET', `/templates/${id}`),
  createTemplate: (body) => request('POST', '/templates', body),
  createProjectFromTemplate: (id, body) =>
    request('POST', `/templates/${id}/create_project`, body),

  // findings
  listFindings: (params) => request('GET', `/findings${qs(params)}`),
  getFinding: (id) => request('GET', `/findings/${id}`),
  saveFindingDraft: (body) => request('POST', '/findings', body),
  updateFindingDraft: (id, body) => request('PUT', `/findings/${id}`, body),
  submitFinding: (id, body) => request('POST', `/findings/${id}/submit`, body),
  transitionFinding: (id, body) =>
    request('POST', `/findings/${id}/status`, body),
  reviewFinding: (id, body) => request('POST', `/findings/${id}/review`, body),
  findingTimeline: (id) => request('GET', `/findings/${id}/timeline`),

  // attachments
  listAttachments: (params) => request('GET', `/attachments${qs(params)}`),
  createAttachment: (body) => request('POST', '/attachments', body),

  // audit + overview
  listAuditEvents: (params) => request('GET', `/audit_events${qs(params)}`),
  riskOverview: (params) => request('GET', `/risk_overview${qs(params)}`),

  // pre-delivery data consistency self-check
  consistencyChecks: () => request('GET', '/consistency_checks'),
};
