import type {
  Attachment,
  AuditEvent,
  ConsistencyReport,
  Finding,
  Project,
  ProjectDetail,
  ProjectListItem,
  ProjectRiskSummary,
  Review,
  RiskOverview,
  Site,
  SiteRiskItem,
  SiteTemplate,
  Status,
  TimelineEvent,
} from '../types'

const BASE = '/api/v1'

export class ApiClientError extends Error {
  error_code: string
  details: Record<string, unknown>
  status: number

  constructor(status: number, body: { error_code: string; message: string; details: Record<string, unknown> }) {
    super(body.message)
    this.status = status
    this.error_code = body.error_code
    this.details = body.details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (res.status === 204) return undefined as T
  const text = await res.text()
  const body = text ? JSON.parse(text) : null
  if (!res.ok) {
    throw new ApiClientError(res.status, body || { error_code: 'unknown', message: res.statusText, details: {} })
  }
  return body as T
}

export const api = {
  listProjects: (params: { status?: Status; region?: string; highest_risk?: string } = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, String(v)) })
    const s = qs.toString()
    return request<ProjectListItem[]>(`/projects${s ? `?${s}` : ''}`)
  },
  createProject: (data: { project_code: string; project_name: string; owner_name: string }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id: number) => request<ProjectDetail>(`/projects/${id}`),
  projectRiskSummary: (id: number) => request<ProjectRiskSummary>(`/projects/${id}/risk-summary`),
  updateProjectStatus: (id: number, status: Status, actor = 'system') =>
    request<Project>(`/projects/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, actor }),
    }),
  createProjectFromTemplate: (data: {
    project_code: string
    project_name: string
    owner_name: string
    template_id: number
  }) => request<ProjectRiskSummary>('/projects/from-template', { method: 'POST', body: JSON.stringify(data) }),

  listSites: (params: { project_id?: number; region?: string } = {}) => {
    const qs = new URLSearchParams()
    if (params.project_id !== undefined) qs.set('project_id', String(params.project_id))
    if (params.region) qs.set('region', params.region)
    const s = qs.toString()
    return request<Site[]>(`/sites${s ? `?${s}` : ''}`)
  },
  createSite: (data: { project_id: number; site_code: string; site_name: string; address_text?: string; region?: string }) =>
    request<Site>('/sites', { method: 'POST', body: JSON.stringify(data) }),
  updateSite: (id: number, data: Partial<Pick<Site, 'site_name' | 'address_text' | 'region'>>) =>
    request<Site>(`/sites/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSite: (id: number) => request<void>(`/sites/${id}`, { method: 'DELETE' }),
  siteTimeline: (id: number) => request<TimelineEvent[]>(`/sites/${id}/timeline`),

  listTemplates: () => request<SiteTemplate[]>('/templates'),
  createTemplate: (data: { template_name: string; default_region?: string; site_items: unknown[] }) =>
    request<SiteTemplate>('/templates', { method: 'POST', body: JSON.stringify(data) }),

  listFindings: (params: { site_id?: number; status?: Status; risk_level?: string; project_id?: number } = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)) })
    const s = qs.toString()
    return request<Finding[]>(`/findings${s ? `?${s}` : ''}`)
  },
  createDraft: (data: { site_id: number; category: string; description: string; risk_level: string; reported_by: string }) =>
    request<Finding>('/findings/draft', { method: 'POST', body: JSON.stringify(data) }),
  updateDraft: (id: number, data: Partial<{ category: string; description: string; risk_level: string; reported_by: string }>) =>
    request<Finding>(`/findings/${id}/draft`, { method: 'PATCH', body: JSON.stringify(data) }),
  submitFinding: (id: number, actor: string, note?: string) =>
    request<Finding>(`/findings/${id}/submit`, { method: 'POST', body: JSON.stringify({ actor, note: note || '' }) }),
  updateFindingStatus: (id: number, status: Status, actor: string, note?: string) =>
    request<Finding>(`/findings/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status, actor, note: note || '' }) }),

  registerAttachment: (data: { file_name: string; file_type: string; storage_note: string; linked_finding_id: number }) =>
    request<Attachment>('/attachments', { method: 'POST', body: JSON.stringify(data) }),
  listAttachments: (findingId: number) => request<Attachment[]>(`/attachments/by-finding/${findingId}`),

  createReview: (data: { finding_id: number; reviewer_name: string; conclusion: 'accepted' | 'rejected'; comment?: string }) =>
    request<Review>('/reviews', { method: 'POST', body: JSON.stringify(data) }),
  listReviews: (findingId: number) => request<Review[]>(`/reviews/by-finding/${findingId}`),

  listAudit: (params: { entity_type?: string; entity_id?: number; limit?: number } = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)) })
    const s = qs.toString()
    return request<AuditEvent[]>(`/audit${s ? `?${s}` : ''}`)
  },
  overview: () => request<RiskOverview>('/overview'),
  consistency: () => request<ConsistencyReport>('/consistency'),
  siteRisks: (projectId: number) => request<SiteRiskItem[]>(`/projects/${projectId}/site-risks`),
  timeline: (projectId: number) => request<TimelineEvent[]>(`/projects/${projectId}/timeline`),
}
