import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import FindingForm from '../components/FindingForm.jsx';

afterEach(cleanup);

describe('FindingForm', () => {
  it('shows backend error and preserves input on validation failure', async () => {
    // Mock fetch to return a 422 validation error like the backend does.
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: async () =>
        JSON.stringify({
          error_code: 'validation_error',
          message: 'One or more required fields are missing.',
          details: { fields: { reported_by: 'This field is required.' } },
        }),
    });

    render(<FindingForm siteId={1} onSaved={() => {}} />);

    const categoryInput = screen.getByLabelText(/category/i);
    fireEvent.change(categoryInput, { target: { value: 'structural' } });
    fireEvent.click(screen.getByText('保存草稿'));

    // error message appears
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('required fields are missing'),
    );
    // per-field error shown
    expect(screen.getByText('This field is required.')).toBeInTheDocument();
    // input preserved (not reset)
    expect(categoryInput.value).toBe('structural');
  });

  it('resets input on successful save', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      text: async () => JSON.stringify({ id: 5, category: 'structural' }),
    });
    const onSaved = vi.fn();
    render(<FindingForm siteId={1} onSaved={onSaved} />);

    const categoryInput = screen.getByLabelText(/category/i);
    const desc = screen.getByLabelText(/description/i);
    const reporter = screen.getByLabelText(/reported_by/i);
    fireEvent.change(categoryInput, { target: { value: 'structural' } });
    fireEvent.change(desc, { target: { value: 'crack' } });
    fireEvent.change(reporter, { target: { value: 'Grace' } });
    fireEvent.click(screen.getByText('保存草稿'));

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(categoryInput.value).toBe('');
  });
});
