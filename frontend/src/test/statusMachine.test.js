import { describe, expect, it } from 'vitest';
import { canTransition, nextStatuses } from '../state/statusMachine.js';

describe('statusMachine', () => {
  it('allows draft -> submitted', () => {
    expect(canTransition('draft', 'submitted')).toBe(true);
  });
  it('forbids draft -> accepted', () => {
    expect(canTransition('draft', 'accepted')).toBe(false);
  });
  it('archived is terminal', () => {
    expect(nextStatuses('archived')).toEqual([]);
  });
  it('rejected can reopen to draft', () => {
    expect(canTransition('rejected', 'draft')).toBe(true);
  });
});
