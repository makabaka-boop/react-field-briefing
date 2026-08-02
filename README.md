# 现场踏勘简报协作系统 (Field Briefing)

面向项目团队的浏览器端简报协作系统，用于沉淀踏勘观察、风险判断、复核结论和模板化地点清单。

## 技术栈

- **前端**: React 18 + Vite + React Router
- **后端**: Python + FastAPI + SQLite
- **测试**: pytest + httpx

## 端口配置

| 服务 | 端口 |
|------|------|
| 前端开发服务 | 18110 |
| 后端 API 服务 | 18111 |

## SQLite 数据库

- 数据库文件位置：`backend/briefing.db`（启动后端时自动创建）
- 可通过环境变量 `BRIEFING_DB_PATH` 自定义路径
- 重置数据：停止后端后执行 `rm backend/briefing.db`，重启自动重建表结构

## 目录结构

```
react-field-briefing/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── database.py          # SQLite 连接与 Schema
│   │   ├── schemas.py           # Pydantic 数据模型
│   │   ├── state_machine.py     # 状态流转定义
│   │   ├── errors.py            # 统一错误处理
│   │   ├── audit.py             # 审计事件记录
│   │   └── routers/             # API 路由
│   │       ├── projects.py
│   │       ├── sites.py
│   │       ├── findings.py
│   │       ├── templates.py
│   │       ├── attachments.py
│   │       ├── reviews.py
│   │       ├── audit.py
│   │       ├── overview.py
│   │       └── system_check.py
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_api.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.js        # API 客户端
│   │   │   └── state.js         # 前端状态常量
│   │   ├── components/
│   │   │   ├── Badges.jsx
│   │   │   ├── FindingTable.jsx
│   │   │   ├── FindingForm.jsx
│   │   │   ├── ReviewSidebar.jsx
│   │   │   ├── Timeline.jsx
│   │   │   └── RiskFilters.jsx
│   │   ├── pages/
│   │   │   ├── ProjectListPage.jsx
│   │   │   ├── ProjectCreatePage.jsx
│   │   │   ├── ProjectDetailPage.jsx
│   │   │   ├── SiteDetailPage.jsx
│   │   │   ├── TemplateManagePage.jsx
│   │   │   ├── RiskOverviewPage.jsx
│   │   │   └── SystemCheckPage.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md
```

## 快速启动

需要**分别启动后端和前端**两个服务（使用两个终端窗口）。

### 1. 启动后端（终端 1，端口 18111）

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 18111 --reload
```

后端启动后自动初始化 SQLite 数据库 (`briefing.db`)。

API 文档访问: http://localhost:18111/docs

### 2. 启动前端（终端 2，端口 18110）

```bash
cd frontend
npm install
npm run dev
```

前端访问: http://localhost:18110

前端通过 Vite 代理将 `/api` 请求转发到后端 18111 端口。

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

## 本地联调步骤

1. **启动后端服务**（终端 1）：
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 18111 --reload
   ```
   - 服务启动后自动创建 `briefing.db`
   - API 文档（Swagger）：http://127.0.0.1:18111/docs
   - 健康检查：`curl http://127.0.0.1:18111/api/v1/health`

2. **启动前端开发服务**（终端 2）：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   - 前端页面：http://127.0.0.1:18110
   - Vite 开发服务器自动将 `/api` 请求代理到 `127.0.0.1:18111`

3. **验证端到端联通**：
   ```bash
   curl http://127.0.0.1:18110/api/v1/health
   ```
   应返回 `{"status":"ok"}`

4. **重置数据库**（开发阶段需要清空数据时）：
   ```bash
   rm backend/briefing.db
   ```
   重启后端服务后自动重建表结构。

5. **运行后端测试**：
   ```bash
   cd backend
   python -m pytest tests/ -v
   ```

6. **前端生产构建检查**：
   ```bash
   cd frontend
   npm run build
   ```

### 观察项校验规则

- `category`、`description`、`reported_by` 不能为空或纯空白
- `risk_level` 必须是 `low`、`medium`、`high`、`critical` 之一
- 创建和更新时均执行校验，提交（submit）时再次校验
- 校验失败返回 HTTP 422，`details` 中包含各字段的错误说明
- 前端表单提交失败时展示后端返回的 `message`，并保留用户已输入内容

### 审计事件说明

观察项的每次状态流转（提交、reviewing、通过、驳回）均写入 `audit_events`，详情包含：
- `from_status` / `to_status`：旧状态和新状态
- `actor`：操作者
- `note`：中文说明

## 数据模型

### projects (项目)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_code | TEXT | 项目编号（唯一） |
| project_name | TEXT | 项目名称 |
| owner_name | TEXT | 负责人 |
| status | TEXT | 状态 |
| created_at | TEXT | 创建时间 |

### sites (地点)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| site_code | TEXT | 地点编号（唯一） |
| site_name | TEXT | 地点名称 |
| address_text | TEXT | 地址 |
| region | TEXT | 区域 |
| project_id | INTEGER | 所属项目 |

### findings (观察项)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| site_id | INTEGER | 所属地点 |
| category | TEXT | 分类 |
| description | TEXT | 描述 |
| risk_level | TEXT | 风险等级 (low/medium/high/critical) |
| finding_status | TEXT | 状态 |
| reported_by | TEXT | 报告人 |
| reported_at | TEXT | 报告时间 |

### attachments (附件元数据)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| file_name | TEXT | 文件名 |
| file_type | TEXT | 文件类型 |
| storage_note | TEXT | 存储位置备注 |
| linked_finding_id | INTEGER | 关联观察项 |
| created_at | TEXT | 登记时间 |

### templates (地点模板)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| template_name | TEXT | 模板名称（唯一） |
| default_region | TEXT | 默认区域 |
| site_items | TEXT(JSON) | 地点项数组 |

### reviews (复核记录)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| finding_id | INTEGER | 关联观察项 |
| reviewer_name | TEXT | 复核人 |
| conclusion | TEXT | 结论 (approved/rejected/needs_changes) |
| comment | TEXT | 备注 |
| reviewed_at | TEXT | 复核时间 |

### audit_events (审计事件)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| entity_type | TEXT | 实体类型 |
| entity_id | INTEGER | 实体 ID |
| action | TEXT | 操作类型 |
| actor | TEXT | 操作人 |
| details | TEXT(JSON) | 详情 |
| created_at | TEXT | 时间 |

## 状态机

状态值: `draft`(草稿) → `submitted`(已提交) → `reviewing`(审核中) → `accepted`(已通过) / `rejected`(已驳回) → `archived`(已归档)

允许的状态流转:
- draft → submitted, archived
- submitted → reviewing, draft, archived
- reviewing → accepted, rejected, archived
- accepted → archived
- rejected → draft, archived
- archived → draft

## API 概览

所有接口路径以 `/api/v1` 开头，字段使用 `snake_case`。

### 错误响应格式
```json
{
  "error_code": "not_found",
  "message": "project not found",
  "details": {"entity": "project", "id": 123}
}
```

### 项目
- `POST /projects` - 创建项目
- `GET /projects` - 项目列表（支持 status、region、max_risk_level 筛选，返回 risk_summary 风险摘要）
- `GET /projects/{id}` - 项目详情
- `PATCH /projects/{id}` - 更新项目
- `POST /projects/{id}/transition` - 项目状态流转
- `POST /projects/from-template` - 按模板创建项目并批量生成地点（单事务，失败整批回滚）

### 地点
- `POST /sites` - 创建地点
- `GET /sites` - 地点列表（支持 project_id、region 筛选）
- `GET /sites/{id}` - 地点详情
- `PATCH /sites/{id}` - 更新地点
- `DELETE /sites/{id}` - 删除地点
- `GET /sites/{id}/timeline` - 地点合并时间线（观察项、附件、审计事件按时间排序）

### 观察项
- `POST /findings` - 创建观察项草稿
- `GET /findings` - 观察项列表（支持 site_id、project_id、finding_status、risk_level 筛选）
- `GET /findings/{id}` - 观察项详情
- `PATCH /findings/{id}` - 更新观察项
- `POST /findings/{id}/save-draft` - 保存草稿
- `POST /findings/{id}/submit` - 提交观察项
- `POST /findings/{id}/transition` - 状态流转
- `GET /findings/{id}/timeline` - 观察项时间线（含创建、状态流转、复核、附件）

### 模板
- `POST /templates` - 创建模板
- `GET /templates` - 模板列表
- `GET /templates/{id}` - 模板详情
- `DELETE /templates/{id}` - 删除模板

### 附件
- `POST /attachments` - 登记附件元数据
- `GET /attachments` - 附件列表（支持 linked_finding_id 筛选）
- `GET /attachments/{id}` - 附件详情
- `DELETE /attachments/{id}` - 删除附件记录

### 复核
- `POST /findings/{id}/reviews` - 提交复核结论
- `GET /findings/{id}/reviews` - 复核历史

### 审计
- `GET /audit-events` - 审计事件查询（支持 entity_type、entity_id、action 筛选）

### 风险概览
- `GET /overview/risk` - 风险概览（支持 project_id 筛选，排除 archived 观察项）
- `GET /projects/{id}/sites-risk` - 按项目查看各地点风险（含未复核数、已驳回数、最高风险等级、最近更新时间）

### 系统自检
- `GET /system/check` - 数据一致性自检（返回 6 项检查的通过状态、问题数量和问题明细）

自检项：
1. **orphan_sites** — 检查是否存在指向不存在项目的地点
2. **orphan_findings** — 检查是否存在缺少有效地点的观察项
3. **status_audit_mismatch** — 检查观察项当前状态与最后一条审计事件的 to_status 是否一致
4. **orphan_attachments** — 检查是否存在指向不存在观察项的附件
5. **duplicate_template_site_codes** — 检查模板 site_items 中是否存在重复地点编码
6. **risk_stats_consistency** — 检查风险概览统计总数与各风险等级明细之和是否一致

## 前端功能

- **项目列表**: 查看所有项目，展示风险摘要列（观察项数、未复核、已驳回、最高风险、最近更新），支持按状态、区域、最高风险等级筛选
- **项目创建**: 手动创建或从模板创建（含模板预览、创建结果页展示生成的地点清单）
- **模板管理**: 创建和管理地点模板，定义批量地点清单
- **项目详情**: 地点列表、观察项表格、风险分布三个标签页（风险分布含未复核/已驳回统计）
- **地点详情**: 编辑地点信息、管理观察项、登记附件元数据、查看地点合并时间线
- **观察项表格**: 按状态/风险/区域筛选，支持编辑、复核、状态流转
- **观察项表单**: 草稿保存和提交，提交失败时展示后端错误并保留已输入内容
- **复核侧栏**: 查看复核历史、提交复核结论
- **时间线**: 展示观察项或地点的完整操作历史（含创建、状态流转、复核、附件）
- **风险概览**: 全局或项目维度的风险统计可视化，排除归档观察项
- **系统检查**: 数据一致性自检视图，展示每项检查的通过状态、问题数量和问题明细表格

## 统计口径

- 风险概览和项目列表风险摘要**排除 archived 状态的观察项**
- 地点详情页仍可查看归档观察项的完整历史
- 未复核数 = 状态为 draft、submitted、reviewing 的观察项数量
- 已驳回数 = 状态为 rejected 的观察项数量
- 最高风险等级 = 非归档观察项中风险等级最高的值（critical > high > medium > low）
- 最近更新时间 = 非归档观察项中最新的 reported_at

## 事务保证

按模板创建项目时，项目和所有地点在**单个数据库事务**中创建：
- 模板 site_items 结构非法（缺 site_code/site_name、编码重复）→ 整批回滚
- 任一地点编码与现有数据冲突 → 整批回滚
- 项目编号重复 → 整批回滚
- 不会产生半成品项目或地点数据
