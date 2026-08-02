import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SystemCheck from '../pages/SystemCheck.jsx';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function checksResponse(report) {
  return {
    ok: true,
    status: 200,
    text: async () => JSON.stringify(report),
  };
}

const PASS_REPORT = {
  passed: true,
  total_issues: 0,
  checked_at: '2026-08-02T10:00:00Z',
  checks: [
    { check_name: 'orphan_sites', description: 'x', passed: true, issue_count: 0, issues: [] },
    { check_name: 'duplicate_site_codes', description: 'y', passed: true, issue_count: 0, issues: [] },
  ],
};

const FAIL_REPORT = {
  passed: false,
  total_issues: 1,
  checked_at: '2026-08-02T10:05:00Z',
  checks: [
    { check_name: 'orphan_sites', description: 'x', passed: true, issue_count: 0, issues: [] },
    {
      check_name: 'attachments_missing_finding',
      description: 'Attachments must reference an existing finding.',
      passed: false,
      issue_count: 1,
      issues: [{ attachment_id: 7, linked_finding_id: 9999 }],
    },
  ],
};

describe('SystemCheck', () => {
  it('renders an all-pass report', async () => {
    global.fetch = vi.fn().mockResolvedValue(checksResponse(PASS_REPORT));
    render(
      <MemoryRouter>
        <SystemCheck />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('check-summary')).toHaveTextContent('全部通过'),
    );
    // both check cards render as 通过
    expect(screen.getByTestId('check-orphan_sites')).toHaveTextContent('通过');
  });

  it('renders issue count and issue detail rows on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue(checksResponse(FAIL_REPORT));
    render(
      <MemoryRouter>
        <SystemCheck />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('check-summary')).toHaveTextContent('发现 1 个问题'),
    );
    const failCard = screen.getByTestId('check-attachments_missing_finding');
    expect(failCard).toHaveTextContent('1 个问题');
    // issue detail rendered (snake_case fields + values)
    expect(failCard).toHaveTextContent('attachment_id');
    expect(failCard).toHaveTextContent('9999');
  });
});
