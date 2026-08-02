const BASE_URL = '/api/v1';

async function request(path, options = {}) {
  const { method = 'GET', body, params } = options;
  let url = BASE_URL + path;
  if (params) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        search.append(key, value);
      }
    });
    const qs = search.toString();
    if (qs) url += `?${qs}`;
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    const error = new Error('网络请求失败，请检查后端服务是否可用');
    error.errorCode = 'NETWORK_ERROR';
    throw error;
  }

  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch (err) {
      payload = null;
    }
    const message =
      (payload && payload.message) || `请求失败（HTTP ${response.status}）`;
    const error = new Error(message);
    error.errorCode = (payload && payload.error_code) || 'UNKNOWN_ERROR';
    error.details = payload && payload.details;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

// 项目
export function createProject(data) {
  return request('/projects', { method: 'POST', body: data });
}

export function listProjects(params = {}) {
  return request('/projects', { params });
}

export function getProject(id) {
  return request(`/projects/${id}`);
}

export function createProjectFromTemplate(data) {
  return request('/projects/from_template', { method: 'POST', body: data });
}

// 地点模板
export function createSiteTemplate(data) {
  return request('/site_templates', { method: 'POST', body: data });
}

export function listSiteTemplates() {
  return request('/site_templates');
}

// 地点
export function createSite(data) {
  return request('/sites', { method: 'POST', body: data });
}

export function listSites(params = {}) {
  return request('/sites', { params });
}

export function getSite(id) {
  return request(`/sites/${id}`);
}

export function updateSite(id, data) {
  return request(`/sites/${id}`, { method: 'PATCH', body: data });
}

// 观察项
export function createFinding(data) {
  return request('/findings', { method: 'POST', body: data });
}

export function updateFinding(id, data) {
  return request(`/findings/${id}`, { method: 'PATCH', body: data });
}

export function listFindings(params = {}) {
  return request('/findings', { params });
}

export function submitFinding(id) {
  return request(`/findings/${id}/submit`, { method: 'POST' });
}

export function transitionFinding(id, toStatus, extra = {}) {
  return request(`/findings/${id}/transition`, {
    method: 'POST',
    body: { to_status: toStatus, ...extra },
  });
}

export function reviewFinding(id, data) {
  return request(`/findings/${id}/review`, { method: 'POST', body: data });
}

export function listFindingReviews(id) {
  return request(`/findings/${id}/reviews`);
}

export function getFindingTimeline(id) {
  return request(`/findings/${id}/timeline`);
}

// 附件
export function createAttachment(data) {
  return request('/attachments', { method: 'POST', body: data });
}

export function listAttachments(params = {}) {
  return request('/attachments', { params });
}

// 风险视图
export function getProjectRiskSites(projectId) {
  return request(`/projects/${projectId}/risk_sites`);
}

export function getProjectRiskSummary(projectId) {
  return request(`/projects/${projectId}/risk_summary`);
}

// 一致性自检
export function getConsistencyChecks() {
  return request('/consistency_checks');
}
