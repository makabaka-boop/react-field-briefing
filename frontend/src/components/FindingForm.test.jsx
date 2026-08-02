import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import FindingForm from './FindingForm.jsx';

afterEach(cleanup);

// 模拟后端统一错误结构 {error_code, message, details} 经 client.js 转换后的 Error
function backendError(message, errorCode = 'VALIDATION_ERROR') {
  const error = new Error(message);
  error.errorCode = errorCode;
  error.details = { missing_fields: ['description'] };
  return error;
}

function fillForm(values) {
  fireEvent.change(screen.getByLabelText('类别'), {
    target: { value: values.category },
  });
  fireEvent.change(screen.getByLabelText('描述'), {
    target: { value: values.description },
  });
  fireEvent.change(screen.getByLabelText('填报人'), {
    target: { value: values.reported_by },
  });
}

describe('FindingForm 提交失败', () => {
  it('展示后端统一错误中的 message', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(backendError("missing required field(s): description"));

    render(<FindingForm onSubmit={onSubmit} />);
    fillForm({ category: '安全', description: '护栏缺失', reported_by: '王五' });
    fireEvent.click(screen.getByRole('button', { name: '创建草稿' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'missing required field(s): description'
      );
    });
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('提交失败后保留用户已输入的内容', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(backendError('risk_level must be one of: low, medium, high, critical'));

    render(<FindingForm onSubmit={onSubmit} />);
    fillForm({ category: '质量', description: '混凝土蜂窝麻面', reported_by: '李工' });
    fireEvent.change(screen.getByLabelText('风险等级'), {
      target: { value: 'high' },
    });
    fireEvent.click(screen.getByRole('button', { name: '创建草稿' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.getByLabelText('类别')).toHaveValue('质量');
    expect(screen.getByLabelText('描述')).toHaveValue('混凝土蜂窝麻面');
    expect(screen.getByLabelText('风险等级')).toHaveValue('high');
    expect(screen.getByLabelText('填报人')).toHaveValue('李工');
  });

  it('再次提交前会清除上一条错误提示', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValueOnce(backendError('first error'))
      .mockResolvedValueOnce({ id: 1 });

    render(<FindingForm onSubmit={onSubmit} />);
    fillForm({ category: '安全', description: '护栏缺失', reported_by: '王五' });

    fireEvent.click(screen.getByRole('button', { name: '创建草稿' }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('first error');
    });

    fireEvent.click(screen.getByRole('button', { name: '创建草稿' }));
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
    expect(onSubmit).toHaveBeenCalledTimes(2);
  });
});

describe('FindingForm 提交成功', () => {
  it('调用 onSubmit 并携带 trim 后的字段', async () => {
    const onSubmit = vi.fn().mockResolvedValue({ id: 1 });

    render(<FindingForm onSubmit={onSubmit} />);
    fillForm({ category: '  安全  ', description: '  护栏缺失  ', reported_by: ' 王五 ' });
    fireEvent.click(screen.getByRole('button', { name: '创建草稿' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        category: '安全',
        description: '护栏缺失',
        risk_level: 'low',
        reported_by: '王五',
      });
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
