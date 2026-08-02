export const STATUSES = ['draft', 'submitted', 'reviewing', 'accepted', 'rejected', 'archived'];

export const STATUS_LABELS = {
  draft: '草稿',
  submitted: '已提交',
  reviewing: '审核中',
  accepted: '已通过',
  rejected: '已驳回',
  archived: '已归档',
};

export const RISK_LEVELS = ['low', 'medium', 'high', 'critical'];

export const RISK_LABELS = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};

export const PROJECT_TRANSITIONS = {
  draft: ['submitted', 'archived'],
  submitted: ['reviewing', 'draft', 'archived'],
  reviewing: ['accepted', 'rejected', 'archived'],
  accepted: ['archived'],
  rejected: ['draft', 'archived'],
  archived: ['draft'],
};

export const FINDING_TRANSITIONS = { ...PROJECT_TRANSITIONS };

export function getAvailableTransitions(current, isProject = true) {
  const map = isProject ? PROJECT_TRANSITIONS : FINDING_TRANSITIONS;
  return map[current] || [];
}
