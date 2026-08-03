import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { listProjects } from '../api/client.js';
import ProjectListPage from './ProjectListPage.jsx';

vi.mock('../api/client.js', () => ({
  listProjects: vi.fn(),
}));

const PROJECTS = [
  {
    id: 1,
    project_code: 'P-100',
    project_name: '一号项目',
    owner_name: '张三',
    status: 'draft',
    created_at: '2026-08-01T08:00:00.000Z',
    regions: ['华东', '华北'],
    risk_summary: {
      total_findings: 3,
      unreviewed_count: 2,
      rejected_count: 1,
      max_risk_level: 'critical',
      last_updated_at: '2026-08-01T09:00:00.000Z',
    },
  },
  {
    id: 2,
    project_code: 'P-200',
    project_name: '二号项目',
    owner_name: '李四',
    status: 'submitted',
    created_at: '2026-08-01T10:00:00.000Z',
    regions: ['华南'],
    risk_summary: {
      total_findings: 0,
      unreviewed_count: 0,
      rejected_count: 0,
      max_risk_level: null,
      last_updated_at: null,
    },
  },
];

afterEach(cleanup);

beforeEach(() => {
  listProjects.mockReset();
  listProjects.mockResolvedValue(PROJECTS);
});

describe('ProjectListPage 筛选交互', () => {
  it('加载时请求项目列表并渲染风险摘要列', async () => {
    render(<ProjectListPage onOpenProject={() => {}} onCreateProject={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('P-100')).toBeInTheDocument();
    });
    expect(listProjects).toHaveBeenCalledWith({
      status: undefined,
      region: undefined,
      max_risk_level: undefined,
    });
    // 风险摘要列：观察项/未复核/已驳回
    expect(screen.getByText('3 / 2 / 1')).toBeInTheDocument();
    // 最高风险徽章（critical -> 严重；下拉选项中也有同文案，故断言徽章元素存在）
    const criticalBadges = screen
      .getAllByText('严重')
      .filter((el) => el.classList.contains('badge-risk-critical'));
    expect(criticalBadges.length).toBe(1);
    // 无观察项的项目显示占位
    expect(screen.getByText('0 / 0 / 0')).toBeInTheDocument();
  });

  it('修改区域与最高风险等级筛选会携带参数重新请求', async () => {
    render(<ProjectListPage onOpenProject={() => {}} onCreateProject={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText('P-100')).toBeInTheDocument();
    });

    listProjects.mockResolvedValue([PROJECTS[0]]);
    fireEvent.change(screen.getByLabelText('区域'), {
      target: { value: '华东' },
    });
    await waitFor(() => {
      expect(listProjects).toHaveBeenLastCalledWith({
        status: undefined,
        region: '华东',
        max_risk_level: undefined,
      });
    });

    fireEvent.change(screen.getByLabelText('最高风险等级'), {
      target: { value: 'critical' },
    });
    await waitFor(() => {
      expect(listProjects).toHaveBeenLastCalledWith({
        status: undefined,
        region: '华东',
        max_risk_level: 'critical',
      });
    });

    fireEvent.change(screen.getByLabelText('项目状态'), {
      target: { value: 'draft' },
    });
    await waitFor(() => {
      expect(listProjects).toHaveBeenLastCalledWith({
        status: 'draft',
        region: '华东',
        max_risk_level: 'critical',
      });
    });
  });

  it('筛选结果为空时展示空态文案', async () => {
    render(<ProjectListPage onOpenProject={() => {}} onCreateProject={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText('P-100')).toBeInTheDocument();
    });

    listProjects.mockResolvedValue([]);
    fireEvent.change(screen.getByLabelText('区域'), {
      target: { value: '不存在区域' },
    });
    await waitFor(() => {
      expect(screen.getByText(/暂无项目/)).toBeInTheDocument();
    });
  });

  it('请求失败时展示后端错误 message', async () => {
    const error = new Error('max_risk_level must be one of: low, medium, high, critical');
    error.errorCode = 'VALIDATION_ERROR';
    listProjects.mockRejectedValue(error);

    render(<ProjectListPage onOpenProject={() => {}} onCreateProject={() => {}} />);
    await waitFor(() => {
      expect(
        screen.getByText('max_risk_level must be one of: low, medium, high, critical')
      ).toBeInTheDocument();
    });
  });
});
