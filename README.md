# Field Briefing Collaboration System

现场项目团队的浏览器简报协作系统，用于沉淀踏勘观察、风险判断、复核结论和模板化地点清单。

- **前端**：React 18 + TypeScript + Vite，开发服务器监听 **18110**
- **后端**：Python + FastAPI + SQLAlchemy，HTTP API 监听 **18111**
- **数据库**：SQLite（文件位于 `backend/field_briefing.db`）
- 所有接口路径以 `/api/v1` 开头，字段统一 `snake_case`
- 错误响应固定为 `{"error_code":"...","message":"...","details":{...}}`

## 目录结构

```
react-field-briefing/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # 应用入口、路由注册、启动初始化
│   │   ├── core/
│   │   │   ├── config.py        # 配置（端口、状态、风险等级）
│   │   │   ├── database.py      # SQLAlchemy engine / Session / init_db
│   │   │   ├── errors.py        # 统一错误类与异常处理器
│   │   │   └── state_machine.py # 项目/观察项状态机
│   │   ├── models/
│   │   │   └── all_models.py    # ORM 模型
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── services/
│   │   │   ├── audit_service.py       # 审计事件写入
│   │   │   ├── risk_service.py        # 风险汇总（排除 archived）
│   │   │   └── consistency_service.py # 一致性自检
│   │   └── api/v1/              # 路由：projects / sites / templates /
│   │                              #       findings / attachments / reviews / meta
│   ├── tests/                   # pytest 测试（39 个用例）
│   ├── requirements.txt
│   └── run.py                   # uvicorn 启动脚本
└── frontend/                    # React 前端
    ├── src/
    │   ├── api/client.ts        # 类型安全的 API 客户端
    │   ├── types/index.ts       # 领域类型 + 状态机常量
    │   ├── App.tsx              # 顶层视图路由
    │   ├── styles.css
    │   └── components/          # 项目列表/创建、模板管理、地点详情、
    │                            # 观察项表格/表单、复核侧栏、时间线、风险概览
    ├── vite.config.ts           # 端口 18110 + 代理 /api → 18111
    └── package.json
```

## 数据模型

| 表 | 关键字段 |
|---|---|
| `projects` | `project_code`（唯一）、`project_name`、`owner_name`、`status`、`created_at` |
| `sites` | `site_code`、`site_name`、`address_text`、`region`、`project_id` |
| `findings`（观察项） | `site_id`、`category`、`description`、`risk_level`、`finding_status`、`reported_by`、`reported_at` |
| `attachments` | `file_name`、`file_type`、`storage_note`、`linked_finding_id`（仅登记元数据，不处理真实上传） |
| `reviews` | `finding_id`、`reviewer_name`、`conclusion`、`comment`、`reviewed_at` |
| `audit_events` | `entity_type`、`entity_id`、`action`、`actor`、`from_status`、`to_status`、`event_metadata`、`created_at` |
| `site_templates` | `template_name`、`default_region`、`site_items`（JSON 数组） |

状态取值：`draft`、`submitted`、`reviewing`、`accepted`、`rejected`、`archived`。
风险等级：`low`、`medium`、`high`、`critical`。

**观察项校验**：`category`、`description`、`risk_level`、`reported_by` 保存草稿时即不能为空；`risk_level` 只能取 `low`/`medium`/`high`/`critical`；提交（submit）和状态流转接口要求非空 `actor`。任何字段校验失败都会返回统一的 422 错误结构，前端直接展示 `message` 即可。

**审计事件**：观察项 `submitted → reviewing → accepted/rejected` 的每次状态变化都会写入 `audit_events`，包含操作者（`actor`）、动作（`action`）、旧状态（`from_status`）、新状态（`to_status`）以及 `event_metadata.note` 说明；复核结论也会同步写入对应状态变更事件。

### 状态流转

```
draft ──► submitted ──► reviewing ──► accepted ──► archived
  │           │             │
  │           ▼             ▼
  │        rejected ◄──────┘
  │           │
  └───────────┘（可回退到 draft 修订）
```

项目与观察项使用同一套状态机（分别在 `PROJECT_TRANSITIONS` / `FINDING_TRANSITIONS` 中定义，后端见 [state_machine.py](file:///Users/zhangxinyu/sunxidan/9999-gsb/0731-new/react-field-briefing/backend/app/core/state_machine.py)，前端见 [types/index.ts](file:///Users/zhangxinyu/sunxidan/9999-gsb/0731-new/react-field-briefing/frontend/src/types/index.ts)）。复核通过/驳回会自动把观察项推进到 `accepted` / `rejected`。

## 一致性自检

`GET /api/v1/consistency` 返回系统一致性报告，所有字段保持 snake_case：

```json
{
  "passed": true,
  "total_checks": 6,
  "failed_checks": 0,
  "total_issues": 0,
  "checks": [
    {"check_name": "orphan_sites", "description": "...", "passed": true, "issue_count": 0, "issues": []}
  ]
}
```

包含六项检查：

| check_name | 检查内容 |
|---|---|
| `orphan_sites` | 地点是否指向不存在的项目 |
| `orphan_findings` | 观察项是否缺少地点 |
| `orphan_attachments` | 附件是否指向不存在的观察项 |
| `status_audit_drift` | 项目/观察项当前状态是否与最后一条带 `to_status` 的审计事件一致 |
| `template_duplicate_site_codes` | 各模板 `site_items` 内是否存在重复 `site_code` |
| `overview_consistency` | 风险概览按非归档观察项聚合的总数/未复核/驳回数，是否等于各项目明细之和 |

统计口径统一排除 `finding_status = archived` 的观察项；归档历史仍可在站点时间线中查看。前端顶部导航的 **System Check** 视图会展示每项检查的通过状态、问题数量和 JSON 问题明细，并支持重新执行。

## API 一览（前缀 `/api/v1`）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/projects` | 创建项目 |
| GET | `/projects` | 项目列表，带风险摘要列；支持 `status`、`region`、`highest_risk` 过滤 |
| GET | `/projects/{id}` | 项目详情（含站点数） |
| GET | `/projects/{id}/risk-summary` | 项目风险汇总：各地点观察项数/未复核数/驳回数/最高风险/最近更新（排除 archived） |
| PATCH | `/projects/{id}/status` | 项目状态流转 |
| POST | `/projects/from-template` | 单事务创建项目并批量生成地点，任一地点编码重复或 `site_items` 非法则整批回滚；返回风险汇总 |
| POST | `/sites` | 创建地点 |
| GET | `/sites` | 地点列表，支持 `project_id`、`region` 筛选 |
| GET / PATCH / DELETE | `/sites/{id}` | 地点详情 / 更新 / 删除 |
| GET | `/sites/{id}/timeline` | 站点观察项时间线（合并观察项、附件元数据、审计事件，按时间倒序；归档历史仍可见） |
| POST | `/templates` | 创建模板 |
| GET | `/templates` | 模板列表 |
| POST | `/findings/draft` | 保存观察项草稿（category/description/risk_level/reported_by 必填） |
| PATCH | `/findings/{id}/draft` | 更新草稿 |
| POST | `/findings/{id}/submit` | 提交观察项（必填 actor） |
| PATCH | `/findings/{id}/status` | 观察项状态流转（必填 actor，可带 note） |
| GET | `/findings` | 观察项列表，支持 `site_id`、`status`、`risk_level`、`project_id` |
| POST | `/attachments` | 登记附件元数据 |
| GET | `/attachments/by-finding/{finding_id}` | 观察项的附件列表 |
| POST | `/reviews` | 提交复核结论（自动流转状态，写带 note 的审计事件） |
| GET | `/reviews/by-finding/{finding_id}` | 观察项的复核历史 |
| GET | `/audit` | 审计事件查询，支持 `entity_type`、`entity_id`、`limit` |
| GET | `/overview` | 风险概览（总数、按风险/状态/区域聚合） |
| GET | `/projects/{id}/site-risks` | 按项目查看各地点风险 |
| GET | `/projects/{id}/timeline` | 项目级时间线（站点/观察项/附件/复核） |
| GET | `/consistency` | 系统一致性自检（孤儿记录、状态/审计漂移、模板重复编码、概览口径一致性） |

## 快速开始

### 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
# API 运行在 http://localhost:18111
```

数据库表会在启动时自动创建。使用 `DATABASE_URL` 环境变量可覆盖数据库位置。

### 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:18110
```

Vite 已配置把 `/api` 请求代理到 `http://localhost:18111`，无需处理跨域。

### 本地联调步骤

推荐在两个终端中分别启动后端和前端：

```bash
# 终端 1：后端（监听 18111）
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py

# 终端 2：前端（监听 18110）
cd frontend
npm install
npm run dev
```

打开浏览器访问 http://localhost:18110 ，前端会把所有 `/api/v1/*` 请求代理到 `http://localhost:18111`。

联调建议：

1. **先建模板，再建项目**：在 Templates 页用 JSON 数组定义 `site_items`，再在 Projects 页选择 “From template”，即可一次性生成项目和批量地点。
2. **验证必填校验**：在观察项表单中留空 category/description/reported_by 或选择非法风险等级提交，应看到后端返回的 `message`（如 “Request validation failed…”），且表单已输入内容不会丢失。
3. **走通复核链路**：新建草稿 → Submit → 在观察项行把状态改为 `reviewing` → 在右侧复核侧栏选择 Accepted/Rejected 提交结论。
4. **查看审计与时间线**：
   - 项目详情页的 Timeline 标签展示项目级时间线；
   - 地点表每行点 “Timeline” 展示该站点的观察项、附件元数据和审计事件合并时间线；
   - 直接请求 `GET /api/v1/audit?entity_type=finding&entity_id=<id>` 可核对每次状态流转是否写入了操作者、动作、旧/新状态和 note。
5. **端口被占用时**：若 18110/18111 被其他进程占用，可用 `lsof -iTCP:18111 -sTCP:LISTEN` 查找并结束旧进程后再启动。

### 运行后端测试

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

测试覆盖（共 39 个用例）：项目创建与重复编码冲突、状态机非法流转、模板批量建点与单事务回滚、地点 CRUD 与区域筛选、观察项草稿→提交→复核全流程、状态/风险筛选、附件元数据登记、风险概览/站点风险/时间线/审计查询、空字段/非法风险/非法状态跳转/审计字段完整性、一致性自检（通过、孤儿记录、模板重复编码、snake_case 字段），以及统一错误结构（含 FastAPI 请求体校验错误）。

## 前端视图

- **Projects**：项目列表，带 Findings / Unreviewed / Rejected / Highest Risk / Last Updated 风险摘要列；支持按状态、区域、最高风险阈值筛选；新建空项目或通过模板向导批量建点
- **Templates**：以 JSON 数组编辑 `site_items` 创建地点模板
- **Risk Overview**：项目/站点/观察项总数，按风险等级、状态、区域聚合
- **System Check**：一致性自检结果，展示每项检查通过状态、问题数量与问题明细，可重新执行
- **Project Detail**：
  - 地点表（区域筛选、内联编辑/删除、查看该地点观察项）
  - 观察项表格（按状态/风险筛选、提交草稿、状态流转、打开复核）
  - 观察项表单（新建草稿）
  - 右侧复核侧栏（提交 `accepted`/`rejected` 结论与历史）
  - Site Risk 标签：各地点各级风险数量与最高风险
  - Timeline 标签：站点创建、观察项上报、附件登记、复核结论时间线

## 设计说明

- **分层清晰**：路由层只做参数校验与编排，数据库访问通过 SQLAlchemy session，审计由独立 service 统一写入。
- **统一错误处理**：所有业务异常继承 `AppError`，由全局 exception handler 输出固定结构，避免把堆栈泄露给前端。
- **状态机集中管理**：前后端各有一份一致的转移表，非法流转返回 `invalid_status_transition`。
- **附件不处理真实上传**：仅保存 `file_name`、`file_type`、`storage_note`，`storage_note` 可记录对象存储 key 或外部链接。
- **审计事件**：创建、状态变更、复核、附件登记等关键动作均写入 `audit_events`，可按实体类型与 ID 追溯。
