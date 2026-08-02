import { cleanup, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getConsistencyChecks } from '../api/client.js';
import SystemCheckPage from './SystemCheckPage.jsx';

vi.mock('../api/client.js', () => ({
  getConsistencyChecks: vi.fn(),
}));

const PASS_RESULT = {
  passed: true,
  total_issues: 0,
  checks: [
    {
      check_code: 'orphan_sites',
      check_name: '地点指向不存在的项目',
      passed: true,
      issue_count: 0,
      issues: [],
    },
    {
      check_code: 'duplicate_site_codes',
      check_name: '项目内地点编码重复',
      passed: true,
      issue_count: 0,
      issues: [],
    },
  ],
};

const FAIL_RESULT = {
  passed: false,
  total_issues: 2,
  checks: [
    {
      check_code: 'orphan_sites',
      check_name: '地点指向不存在的项目',
      passed: false,
      issue_count: 1,
      issues: [{ site_id: 9, site_code: 'ORPHAN-S', project_id: 99999 }],
    },
    {
      check_code: 'status_audit_mismatch',
      check_name: '状态与最后一条审计事件不一致',
      passed: false,
      issue_count: 1,
      issues: [
        {
          finding_id: 3,
          finding_status: 'submitted',
          last_action: 'finding_created',
          expected_status: 'draft',
          audit_event_id: 12,
        },
      ],
    },
    {
      check_code: 'duplicate_site_codes',
      check_name: '项目内地点编码重复',
      passed: true,
      issue_count: 0,
      issues: [],
    },
  ],
};

afterEach(cleanup);

beforeEach(() => {
  getConsistencyChecks.mockReset();
});

describe('SystemCheckPage 检查结果渲染', () => {
  it('全部通过时展示通过横幅与每项通过状态', async () => {
    getConsistencyChecks.mockResolvedValue(PASS_RESULT);
    render(<SystemCheckPage />);

    await waitFor(() => {
      expect(screen.getByText('全部检查通过，未发现数据漂移')).toBeInTheDocument();
    });
    expect(screen.getByText('地点指向不存在的项目')).toBeInTheDocument();
    expect(screen.getByText('项目内地点编码重复')).toBeInTheDocument();
    expect(screen.getAllByText('通过')).toHaveLength(2);
  });

  it('存在问题时展示问题数量与问题明细', async () => {
    getConsistencyChecks.mockResolvedValue(FAIL_RESULT);
    render(<SystemCheckPage />);

    await waitFor(() => {
      expect(
        screen.getByText('发现 2 个问题，请处理后再交付')
      ).toBeInTheDocument();
    });
    // 未通过徽标（含问题数量），两个失败检查各一个
    expect(screen.getAllByText('未通过（1 个问题）')).toHaveLength(2);
    // 问题明细字段值渲染
    expect(screen.getByText('ORPHAN-S')).toBeInTheDocument();
    expect(screen.getByText('99999')).toBeInTheDocument();
    expect(screen.getByText('finding_created')).toBeInTheDocument();
    // 明细表头使用 snake_case 字段名
    expect(screen.getByText('expected_status')).toBeInTheDocument();
    // 通过项仍展示通过徽标
    expect(screen.getByText('通过')).toBeInTheDocument();
  });

  it('接口失败时展示后端错误 message', async () => {
    const error = new Error('网络请求失败，请检查后端服务是否可用');
    error.errorCode = 'NETWORK_ERROR';
    getConsistencyChecks.mockRejectedValue(error);
    render(<SystemCheckPage />);

    await waitFor(() => {
      expect(
        screen.getByText('网络请求失败，请检查后端服务是否可用')
      ).toBeInTheDocument();
    });
  });
});
