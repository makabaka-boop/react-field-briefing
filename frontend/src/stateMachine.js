export const STATUS_LIST = [
  'draft',
  'submitted',
  'reviewing',
  'accepted',
  'rejected',
  'archived',
];

export const TRANSITIONS = {
  draft: ['submitted'],
  submitted: ['reviewing'],
  reviewing: ['accepted', 'rejected'],
  accepted: ['archived'],
  rejected: ['archived'],
};

export const RISK_LEVELS = ['low', 'medium', 'high', 'critical'];

export const STATUS_LABELS = {
  draft: '草稿',
  submitted: '已提交',
  reviewing: '复核中',
  accepted: '已通过',
  rejected: '已驳回',
  archived: '已归档',
};

export const RISK_LABELS = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};

export const TIMELINE_ACTION_LABELS = {
  finding_created: '创建草稿',
  finding_submitted: '提交',
  status_transition: '状态流转',
  finding_reviewed: '复核',
  attachment_registered: '附件登记',
};

export function statusLabel(status) {
  return STATUS_LABELS[status] || status;
}

export function riskLabel(level) {
  return RISK_LABELS[level] || level;
}

export function timelineActionLabel(action) {
  return TIMELINE_ACTION_LABELS[action] || action;
}

export function availableTransitions(status) {
  return TRANSITIONS[status] || [];
}
