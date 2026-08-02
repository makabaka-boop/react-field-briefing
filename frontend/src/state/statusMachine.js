// Mirror of the backend status vocabulary and transition rules so the UI can
// show only legal next-steps without a round trip. Keep in sync with
// backend/app/state_machine.py.

export const STATUSES = [
  'draft',
  'submitted',
  'reviewing',
  'accepted',
  'rejected',
  'archived',
];

export const RISK_LEVELS = ['low', 'medium', 'high', 'critical'];

const TRANSITIONS = {
  draft: ['submitted', 'archived'],
  submitted: ['reviewing', 'rejected', 'archived'],
  reviewing: ['accepted', 'rejected', 'archived'],
  accepted: ['archived'],
  rejected: ['draft', 'archived'],
  archived: [],
};

export function nextStatuses(current) {
  return TRANSITIONS[current] || [];
}

export function canTransition(current, target) {
  return nextStatuses(current).includes(target);
}

export const RISK_COLORS = {
  low: '#2e7d32',
  medium: '#f9a825',
  high: '#ef6c00',
  critical: '#c62828',
};

export const STATUS_LABELS = {
  draft: '草稿',
  submitted: '已提交',
  reviewing: '复核中',
  accepted: '已采纳',
  rejected: '已驳回',
  archived: '已归档',
};

export const RISK_LABELS = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};
