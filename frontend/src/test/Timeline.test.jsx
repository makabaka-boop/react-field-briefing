import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import Timeline from '../components/Timeline.jsx';

afterEach(cleanup);

// Events as returned by GET /findings/{id}/timeline, already time-sorted
// by the backend. The component renders them in received order.
const EVENTS = [
  {
    kind: 'finding',
    created_at: '2026-08-02T09:00:00Z',
    category: '结构',
    description: '发现裂缝',
    risk_level: 'high',
    reported_by: '王工',
  },
  {
    kind: 'audit',
    created_at: '2026-08-02T09:01:00Z',
    action: 'submit',
    actor_name: '王工',
    old_status: 'draft',
    new_status: 'submitted',
  },
  {
    kind: 'attachment',
    created_at: '2026-08-02T09:02:00Z',
    file_name: 'crack.jpg',
    file_type: 'image/jpeg',
  },
  {
    kind: 'review',
    created_at: '2026-08-02T09:03:00Z',
    reviewer_name: '张工',
    conclusion: 'accept',
  },
];

describe('Timeline', () => {
  it('renders merged entries in order with the finding first', () => {
    render(<Timeline events={EVENTS} />);
    const items = screen.getByTestId('timeline').querySelectorAll('.timeline-item');
    expect(items.length).toBe(4);
    // finding entry leads the timeline
    expect(items[0].textContent).toContain('观察项创建');
    expect(items[1].textContent).toContain('submit');
    expect(items[2].textContent).toContain('crack.jpg');
    expect(items[3].textContent).toContain('复核结论');
  });

  it('shows an empty hint when there are no events', () => {
    render(<Timeline events={[]} />);
    expect(screen.getByText('暂无时间线记录。')).toBeInTheDocument();
  });
});
