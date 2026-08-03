export type Status = 'draft' | 'submitted' | 'reviewing' | 'accepted' | 'rejected' | 'archived'
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export const ALL_STATUSES: Status[] = ['draft', 'submitted', 'reviewing', 'accepted', 'rejected', 'archived']
export const ALL_RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high', 'critical']

export const PROJECT_TRANSITIONS: Record<Status, Status[]> = {
  draft: ['submitted', 'archived'],
  submitted: ['reviewing', 'rejected', 'archived'],
  reviewing: ['accepted', 'rejected', 'archived'],
  accepted: ['archived'],
  rejected: ['draft', 'archived'],
  archived: [],
}

export const FINDING_TRANSITIONS: Record<Status, Status[]> = {
  draft: ['submitted', 'archived'],
  submitted: ['reviewing', 'rejected', 'archived'],
  reviewing: ['accepted', 'rejected', 'archived'],
  accepted: ['archived'],
  rejected: ['draft', 'archived'],
  archived: [],
}

export interface Project {
  id: number
  project_code: string
  project_name: string
  owner_name: string
  status: Status
  created_at: string
}

export interface SiteRiskSummary {
  site_id: number
  site_code: string
  site_name: string
  region: string
  total_findings: number
  unreviewed_count: number
  rejected_count: number
  highest_risk: RiskLevel | 'none'
  last_updated_at: string | null
}

export interface ProjectRiskSummary {
  project_id: number
  project_code: string
  project_name: string
  total_sites: number
  total_findings: number
  unreviewed_count: number
  rejected_count: number
  highest_risk: RiskLevel | 'none'
  last_updated_at: string | null
  sites: SiteRiskSummary[]
}

export interface ProjectListItem extends Project {
  site_count: number
  highest_risk: RiskLevel | 'none'
  total_findings: number
  unreviewed_count: number
  rejected_count: number
  last_updated_at: string | null
}

export interface ProjectDetail extends Project {
  site_count: number
}

export interface Site {
  id: number
  site_code: string
  site_name: string
  address_text: string
  region: string
  project_id: number
}

export interface Finding {
  id: number
  site_id: number
  category: string
  description: string
  risk_level: RiskLevel
  finding_status: Status
  reported_by: string
  reported_at: string
}

export interface Attachment {
  id: number
  file_name: string
  file_type: string
  storage_note: string
  linked_finding_id: number
}

export interface Review {
  id: number
  finding_id: number
  reviewer_name: string
  conclusion: 'accepted' | 'rejected'
  comment: string
  reviewed_at: string
}

export interface SiteTemplate {
  id: number
  template_name: string
  default_region: string
  site_items: TemplateSiteItem[]
  created_at: string
}

export interface TemplateSiteItem {
  site_code?: string
  site_name?: string
  address_text?: string
  region?: string
}

export interface AuditEvent {
  id: number
  entity_type: string
  entity_id: number
  action: string
  actor: string
  from_status: string
  to_status: string
  event_metadata: Record<string, unknown>
  created_at: string
}

export interface RiskOverview {
  total_projects: number
  total_sites: number
  total_findings: number
  by_risk: Record<RiskLevel, number>
  by_status: Record<Status, number>
  by_region: Record<string, number>
}

export interface SiteRiskItem {
  site_id: number
  site_code: string
  site_name: string
  region: string
  total_findings: number
  by_risk: Record<RiskLevel, number>
  highest_risk: RiskLevel
}

export interface TimelineEvent {
  event_type: string
  event_id: number
  entity_type: string
  entity_id: number
  occurred_at: string
  actor: string
  summary: string
  details: Record<string, unknown>
}

export interface ConsistencyCheck {
  check_name: string
  description: string
  passed: boolean
  issue_count: number
  issues: Record<string, unknown>[]
}

export interface ConsistencyReport {
  passed: boolean
  total_checks: number
  failed_checks: number
  total_issues: number
  checks: ConsistencyCheck[]
}

export interface ApiError {
  error_code: string
  message: string
  details: Record<string, unknown>
}
