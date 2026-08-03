import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProjectList from '../pages/ProjectList.jsx';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function projectsResponse(items) {
  return {
    ok: true,
    status: 200,
    text: async () => JSON.stringify({ items, count: items.length }),
  };
}

const HIGH_PROJECT = {
  id: 1,
  project_code: 'PJ-1',
  project_name: '跨江大桥',
  owner_name: '李工',
  status: 'draft',
  site_count: 2,
  highest_risk_level: 'high',
  risk_summary: {
    open_finding_count: 3,
    unreviewed_count: 2,
    rejected_count: 1,
    highest_risk_level: 'high',
    last_updated_at: '2026-08-02T09:00:00Z',
  },
};

describe('ProjectList filters', () => {
  it('renders risk summary columns from backend data', async () => {
    global.fetch = vi.fn().mockResolvedValue(projectsResponse([HIGH_PROJECT]));
    render(
      <MemoryRouter>
        <ProjectList />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText('跨江大桥')).toBeInTheDocument());
    // risk summary cells rendered from backend data (check the data row)
    const row = screen.getByText('跨江大桥').closest('tr');
    const cells = row.querySelectorAll('td');
    // columns: code, name, owner, status, site_count, open, unreviewed,
    // rejected, highest_risk, last_updated, link
    expect(cells[5].textContent).toBe('3'); // open_finding_count
    expect(cells[6].textContent).toBe('2'); // unreviewed_count
    expect(cells[7].textContent).toBe('1'); // rejected_count
    expect(cells[9].textContent).toBe('2026-08-02T09:00:00Z');
  });

  it('passes region and min_risk_level filters to the API request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(projectsResponse([HIGH_PROJECT]));
    global.fetch = fetchMock;
    render(
      <MemoryRouter>
        <ProjectList />
      </MemoryRouter>,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    // change region filter
    fireEvent.change(screen.getByPlaceholderText('按地点区域筛选'), {
      target: { value: 'north' },
    });
    await waitFor(() => {
      const urls = fetchMock.mock.calls.map((c) => c[0]);
      expect(urls.some((u) => u.includes('region=north'))).toBe(true);
    });

    // change min risk level (the second combobox)
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[selects.length - 1], { target: { value: 'high' } });
    await waitFor(() => {
      const urls = fetchMock.mock.calls.map((c) => c[0]);
      expect(urls.some((u) => u.includes('min_risk_level=high'))).toBe(true);
    });
  });
});
