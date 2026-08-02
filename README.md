# react-field-briefing · 现场踏勘简报协作系统

面向现场项目团队的浏览器端简报协作系统，用来沉淀踏勘观察、风险判断、复核结论和模板化地点清单。前端使用 React 实现，后端使用 Python 标准库提供 HTTP API，SQLite 负责持久化。

- 后端 API：`http://127.0.0.1:18111`，接口统一前缀 `/api/v1`
- 前端开发服务：`http://127.0.0.1:18110`（通过 Vite 代理将 `/api` 转发到后端）
- 字段统一 `snake_case`；错误响应固定为 `{"error_code":"...","message":"...","details":{...}}`
- SQLite 文件位置：`backend/field_briefing.db`（由 `backend/app/db.py` 首次启动时自动建表；可删除以重置数据）

## 目录结构

```
react-field-briefing/
├── backend/                  # Python 标准库后端（零第三方依赖）
│   ├── app/
│   │   ├── errors.py         # ApiError 及子类，映射到固定错误响应
│   │   ├── state_machine.py  # 状态词表与合法流转规则、风险等级
│   │   ├── db.py             # SQLite 连接管理与建表
│   │   ├── validators.py     # 必填/字符串字段校验
│   │   ├── handlers.py       # 全部业务逻辑（可单测）
│   │   ├── router.py         # (method, path) -> handler 路由表
│   │   └── server.py         # HTTP 层：解析请求/CORS/错误封装/JSON
│   ├── tests/test_handlers.py
│   └── run.py                # 启动入口，监听 18111
└── frontend/                 # React 18 + Vite 5
    ├── src/
    │   ├── api/client.js      # API 客户端，集中处理 /api/v1 与错误
    │   ├── state/statusMachine.js  # 前端镜像的状态机（与后端保持同步）
    │   ├── components/        # Badge / RiskFilters / FindingForm /
    │   │                      # FindingsTable / ReviewSidebar / Timeline
    │   ├── pages/             # ProjectList / ProjectCreate / TemplateManager
    │   │                      # TemplateResult / ProjectDetail / SiteDetail
    │   │                      # RiskOverview / SystemCheck
    │   └── test/              # vitest 用例
    └── vite.config.js         # dev server 18110 + /api 代理
```

## 数据模型（SQLite）

| 表 | 字段 |
| --- | --- |
| `projects` | id, project_code, project_name, owner_name, status, created_at |
| `sites` | id, site_code, site_name, address_text, region, project_id |
| `findings` | id, site_id, category, description, risk_level, finding_status, reported_by, reported_at |
| `attachments` | id, file_name, file_type, storage_note, linked_finding_id, created_at |
| `reviews` | id, finding_id, reviewer_name, conclusion, review_note, resulting_status, created_at |
| `audit_events` | id, entity_type, entity_id, action, actor_name, old_status, new_status, note, created_at |
| `templates` | id, template_name, default_region, site_items(JSON 数组), created_at |

附件仅登记元数据（file_name / file_type / storage_note / linked_finding_id），不处理真实上传。

## 状态机

状态词表在项目与观察项间共享，仅允许：`draft、submitted、reviewing、accepted、rejected、archived`。

合法流转：

```
draft      -> submitted | archived
submitted  -> reviewing | rejected | archived
reviewing  -> accepted | rejected | archived
accepted   -> archived
rejected   -> draft | archived
archived   -> （终态）
```

非法或未知流转返回 `409 invalid_transition`。复核结论 `accept/reject/needs_more_info` 分别映射到 `accepted/rejected/reviewing`。

## API 一览（前缀 `/api/v1`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/projects` | 创建项目 |
| GET | `/projects` | 项目列表（`status`、`region`、`min_risk_level` 过滤，每行含 `risk_summary` 风险摘要） |
| GET | `/projects/{id}` | 项目详情 |
| POST | `/projects/{id}/status` | 项目状态流转 |
| GET | `/projects/{id}/site_risk` | 按地点风险分布（每地点含观察项数/未复核/已驳回/最高风险/最近更新） |
| POST | `/sites` | 新增/维护地点 |
| GET | `/sites` | 地点列表（`project_id`、`region` 过滤） |
| GET | `/sites/{id}` | 地点详情 |
| POST | `/templates` | 创建模板 |
| GET | `/templates` | 模板列表 |
| GET | `/templates/{id}` | 模板详情 |
| POST | `/templates/{id}/create_project` | 按模板创建项目并批量生成地点（事务） |
| POST | `/findings` | 观察项草稿保存 |
| GET | `/findings` | 观察项列表（`finding_status`、`risk_level`、`site_id`、`project_id` 过滤） |
| GET | `/findings/{id}` | 观察项详情 |
| PUT | `/findings/{id}` | 编辑草稿（仅 draft 可改） |
| POST | `/findings/{id}/submit` | 提交观察项 |
| POST | `/findings/{id}/status` | 观察项状态流转 |
| POST | `/findings/{id}/review` | 复核结论 |
| GET | `/findings/{id}/timeline` | 观察项时间线（审计/复核/附件合并按时间排序） |
| POST | `/attachments` | 附件元数据登记 |
| GET | `/attachments` | 附件列表 |
| GET | `/audit_events` | 审计事件查询（`entity_type`、`entity_id` 过滤） |
| GET | `/risk_overview` | 风险概览（可按 `project_id` 限定，排除 archived） |
| GET | `/consistency_checks` | 交付前一致性自检（6 项检查，返回逐项通过状态/问题数/问题明细） |

## 本地运行（前后端分别启动）

后端与前端是两个独立进程，需各开一个终端窗口分别启动。

**第一步 · 启动后端**（Python 3.8+，无需安装任何依赖，仅用标准库）：

```bash
cd backend
python3 run.py          # 监听 http://127.0.0.1:18111，首次运行自动创建 field_briefing.db
```

**第二步 · 启动前端**（Node 18+，另开一个终端）：

```bash
cd frontend
npm install             # 首次运行安装依赖
npm run dev             # 监听 http://127.0.0.1:18110
```

打开浏览器访问 `http://127.0.0.1:18110`。前端会把 `/api` 请求代理到后端 18111 端口，无需额外配置 CORS。两个服务需同时运行。

## 联调步骤（推荐验证顺序）

1. 「模板管理」新建模板并填写地点清单 → 保存。
2. 在模板卡片中填写项目编号/名称/负责人 → 「按模板创建项目」，系统在一个事务内批量生成地点。
3. 进入项目详情查看「按地点风险」，点击地点进入地点详情。
4. 在地点详情用观察项表单保存草稿：`category、description、risk_level、reported_by` 均为必填，`risk_level` 只能是 `low/medium/high/critical`。
   - 校验失败时后端返回固定错误结构，`details.fields` 给出逐字段提示；前端在表单顶部展示统一 `message`，逐字段展示提示，并**保留用户已输入内容**（成功后才清空）。
5. 从观察项表格选择一条，在复核侧栏「提交」进入 `submitted`；再「采纳/驳回」。
   - 采纳/驳回一个 `submitted` 观察项会经 `submitted → reviewing → accepted/rejected` 两跳，**每一跳各写入一条审计事件**（含操作者、动作、旧状态、新状态、说明）。
   - 「补充信息」将 `submitted → reviewing`，随后可从 `reviewing` 单跳采纳/驳回。
6. 登记附件元数据，在地点详情复核侧栏查看时间线：**观察项本身、审计事件、复核记录、附件元数据按时间合并排列**（观察项为首条；同一秒内的多条事件按写入顺序稳定排序）。
7. 「风险概览」按项目查看未归档观察项的风险与状态分布，支撑评审会议。
8. 交付前打开「系统检查」视图（或调用 `GET /api/v1/consistency_checks`），确认 6 项一致性检查全部通过；若有问题，视图会列出每项检查的问题数量与明细。

### 快速命令行联调（可选）

```bash
# 启动后端后，走通一次草稿→提交→复核链路并观察审计与时间线
B=http://127.0.0.1:18111/api/v1
curl -s -X POST $B/projects -d '{"project_code":"PJ-1","project_name":"踏勘","owner_name":"李工"}'
curl -s -X POST $B/sites -d '{"site_code":"S1","site_name":"1号点","project_id":1,"region":"华东"}'
curl -s -X POST $B/findings -d '{"site_id":1,"category":"结构","description":"裂缝","risk_level":"high","reported_by":"王工"}'
curl -s -X POST $B/findings/1/submit -d '{"actor_name":"王工"}'
curl -s -X POST $B/findings/1/review -d '{"reviewer_name":"张工","conclusion":"accept","review_note":"确认"}'
curl -s $B/findings/1/timeline      # 观察项/审计/复核合并时间线
curl -s "$B/audit_events?entity_type=finding&entity_id=1"   # 两跳审计事件
```

## 测试

后端（unittest，内存 SQLite，54 个用例）覆盖：空字段、非法风险等级、草稿保存、提交成功、非法状态跳转、复核两跳审计写入、时间线排序（含观察项首条与同秒稳定排序）、风险统计口径（未复核/已驳回/最高风险/最近更新）、归档排除但历史可查、模板事务回滚（编码重复/结构非法）、成功批量生成地点、一致性自检（全部通过与逐项异常检出、响应字段保持 snake_case）：

```bash
cd backend
python3 -m unittest discover -s tests -v
```

前端（vitest + Testing Library，12 个用例）覆盖：提交失败展示后端 `message` 并保留输入、成功清空、时间线合并渲染与顺序、项目列表风险摘要列渲染与 `region`/`min_risk_level` 筛选交互、系统检查视图的通过与异常渲染：

```bash
cd frontend
npm test
```

## 设计要点

- **分层清晰**：`server.py` 只做 HTTP/CORS/JSON/错误封装；`router.py` 只做路由；`handlers.py` 承载全部业务逻辑，可脱离 HTTP 单测。
- **零后端依赖**：仅用 `http.server` + `sqlite3`，便于现场部署。
- **模板生成不留半成品**：按模板建项目在单个事务内创建项目与全部地点；模板 `site_items` 结构非法、批内 `site_code` 重复、或与已有地点冲突（`UNIQUE(project_id, site_code)` 触发 `IntegrityError`）都会整批回滚——包括项目行本身，绝不产生半成品数据。
- **风险统计排除 archived，但历史可查**：项目列表 `risk_summary` 与按地点风险均只统计未归档观察项（在办工作量），归档观察项仍可在地点详情通过 `finding_status=archived` 过滤查看。统计一律实时读取 projects/sites/findings/audit 数据，不在前端本地数组计算。
- **风险摘要口径**：`unreviewed_count` = `draft/submitted/reviewing` 之和；`rejected_count` = `rejected`；`highest_risk_level` 取在办观察项最高等级；`last_updated_at` 取观察项 `reported_at` 与其审计事件时间的最大值（含归档历史，反映真实活动）。
- **状态机双端一致**：前端 `statusMachine.js` 镜像后端规则，仅展示合法的下一步操作，非法流转仍由后端兜底拒绝。
- **复核链路逐跳审计**：`submitted → reviewing → accepted/rejected` 每一跳单独写入审计事件，评审可追溯谁在何时因何结论推进状态。
- **时间线稳定排序**：合并观察项/审计/复核/附件后按 `created_at` 升序，同一事务内同秒事件用数据源自增 id 做二级排序键，保证顺序确定。

## 交付前一致性自检

`GET /api/v1/consistency_checks` 跨 projects/sites/findings/attachments/audit/templates 读取数据，返回 `{passed, total_issues, checked_at, checks[]}`；每项 `checks` 含 `check_name`、`description`、`passed`、`issue_count`、`issues[]`（问题明细，字段保持 snake_case）。前端「系统检查」视图逐项展示通过状态、问题数量与明细表，并支持「重新检查」。共 6 项检查：

1. `orphan_sites` — 地点指向不存在的项目。
2. `findings_missing_site` — 观察项缺少所属地点。
3. `status_audit_mismatch` — `finding_status` 与最后一条状态审计事件的 `new_status` 不一致。
4. `attachments_missing_finding` — 附件指向不存在的观察项。
5. `duplicate_site_codes` — 同一项目内 `site_code` 重复（模板生成后校验）。
6. `risk_overview_consistency` — 风险概览聚合数量与明细逐项数量不一致。
