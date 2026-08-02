# react-field-briefing

现场踏勘简报协作系统，面向项目团队记录地点、观察项、风险备注、附件元数据、复核结论、模板生成和审计自检，覆盖 React 交互、Python API、SQLite 建模、状态流转和跨模块扩展。

## 技术栈与端口

| 模块 | 技术 | 端口 |
|---|---|---|
| 后端 | Python 3 标准库（http.server + sqlite3），无第三方依赖 | 18111 |
| 前端 | React 18 + Vite 5 | 18110（`/api` 代理到 18111） |
| 数据库 | SQLite（`backend/data/app.db`，启动时自动建表） | — |

## 目录结构

```
backend/
  app/
    main.py           # 服务入口：python3 -m app.main
    router.py         # 路由分发、CORS、统一错误处理
    db.py             # SQLite 连接与 schema 初始化（APP_DB_PATH 可指定库文件）
    errors.py         # ApiError 与统一错误格式
    state_machine.py  # 观察项状态机
    handlers.py       # 全部接口处理函数与审计写入
  tests/test_api.py   # 48 个端到端测试
frontend/
  src/
    api/client.js     # fetch 封装，统一解析 {error_code,message,details}
    stateMachine.js   # 状态/风险常量与中文标签
    pages/            # 项目列表、项目创建、模板管理、项目详情、地点详情、风险概览、系统检查
    components/       # 观察项表格、观察项表单、复核侧栏、时间线、风险筛选
```

## 快速开始

```bash
# 后端
cd backend && python3 -m app.main          # http://127.0.0.1:18111

# 前端
cd frontend && npm install && npm run dev  # http://localhost:18110

# 后端测试
cd backend && python3 -m unittest discover tests -v

# 前端测试（vitest + testing-library）
cd frontend && npm test
```

## 本地联调步骤

1. 启动后端：`cd backend && python3 -m app.main`（默认 127.0.0.1:18111，可用 `APP_PORT` 覆盖，`APP_DB_PATH` 指定数据库文件）。
2. 启动前端：`cd frontend && npm run dev`（端口 18110，Vite 已配置 `/api` 代理到 18111，浏览器只需访问前端端口）。
3. 打开 http://localhost:18110/ ，按以下顺序验证主链路：
   - 「模板管理」创建模板（含 site_items 地点行）；
   - 「新建项目」选择“按模板创建”，生成项目并批量生成地点；
   - 进入项目 → 地点详情 →「新建观察项」保存草稿（空字段/非法风险等级会在表单内直接展示后端错误 message，已输入内容保留）；
   - 点击观察项行打开复核侧栏：提交 → 填写流转说明后「开始复核」→ 填写复核结论（通过/驳回 + 意见）；
   - 侧栏底部「时间线」按时间合并展示观察项本身、附件元数据与审计事件。
4. 命令行冒烟（可选）：

```bash
curl -s -X POST http://localhost:18110/api/v1/findings \
  -H 'Content-Type: application/json' \
  -d '{"site_id":1,"category":"","description":"x","risk_level":"high","reported_by":"李工"}'
# => {"error_code":"VALIDATION_ERROR","message":"field 'category' must be a non-empty string","details":{"field":"category"}}
```

## API 约定

- 路径统一以 `/api/v1` 开头，字段统一 snake_case。
- 错误响应固定为 `{"error_code":"...","message":"...","details":{...}}`。
  - 400：`VALIDATION_ERROR` / `INVALID_JSON`
  - 404：`NOT_FOUND` / `PROJECT_NOT_FOUND` / `SITE_NOT_FOUND` / `FINDING_NOT_FOUND` / `TEMPLATE_NOT_FOUND`
  - 409：`DUPLICATE_CODE` / `INVALID_STATE_TRANSITION`
  - 500：`INTERNAL_ERROR`

## 状态机

观察项 `finding_status` 只允许：`draft → submitted → reviewing → accepted / rejected → archived`。
草稿仅可编辑与提交；复核结论（accepted/rejected）仅在 reviewing 状态可给出；accepted/rejected 可归档。

## 数据模型（SQLite）

数据库文件为 `backend/data/app.db`（首次启动自动建表），共 7 张表：

| 表 | 字段 |
|---|---|
| projects | id、project_code（唯一）、project_name、owner_name、status、created_at |
| sites | id、site_code、site_name、address_text、region、project_id，（project_id, site_code）唯一 |
| findings | id、site_id、category、description、risk_level、finding_status、reported_by、reported_at、created_at、updated_at |
| attachments | id、file_name、file_type、storage_note、linked_finding_id、created_at（仅元数据，不真实上传） |
| reviews | id、finding_id、reviewer_name、conclusion、comment、created_at |
| audit_events | id、entity_type、entity_id、action、actor、detail（JSON）、project_id、created_at |
| site_templates | id、template_name（唯一）、default_region、site_items（JSON 数组）、created_at |

## 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /projects | 创建项目 |
| GET | /projects | 项目列表（?status= ?region= ?max_risk_level=，每项附 risk_summary 与 regions） |
| GET | /projects/{id} | 项目详情（含 sites） |
| POST | /projects/from_template | 按模板创建项目并批量生成地点（单事务，任一地点编码重复或 site_items 结构非法则整批回滚） |
| POST / GET | /site_templates | 模板创建 / 列表 |
| POST | /sites | 创建地点 |
| GET | /sites | 地点列表（?project_id= ?region=） |
| GET / PATCH | /sites/{id} | 地点详情（含 findings）/ 更新 |
| POST | /findings | 观察项草稿保存 |
| PATCH | /findings/{id} | 编辑草稿（仅 draft） |
| POST | /findings/{id}/submit | 提交 |
| POST | /findings/{id}/transition | 状态流转（可带 actor、note 说明，写入审计事件） |
| POST | /findings/{id}/review | 复核结论（comment 作为审计说明） |
| GET | /findings/{id}/reviews | 复核记录 |
| GET | /findings | 列表（?site_id= ?project_id= ?finding_status= ?risk_level= ?category=） |
| POST / GET | /attachments | 附件元数据登记 / 查询（?linked_finding_id=） |
| GET | /findings/{id}/timeline | 合并时间线（观察项本身 + 附件元数据 + 审计事件，按时间升序） |
| GET | /audit_events | 审计事件查询（?entity_type= ?entity_id= ?project_id=） |
| GET | /projects/{id}/risk_sites | 各地点风险：观察项数、未复核数、已驳回数、最高风险等级、最近更新时间 |
| GET | /projects/{id}/risk_summary | 项目风险概览（含 unreviewed_count / rejected_count / archived_count / last_updated_at） |
| GET | /consistency_checks | 一致性自检（六项检查，含通过状态、问题数量与问题明细） |

## 一致性自检

`GET /api/v1/consistency_checks` 用于交付前确认数据没有漂移，返回 `{passed, total_issues, checks[]}`，每项检查包含 `check_code`、`check_name`、`passed`、`issue_count`、`issues[]`（明细字段均为 snake_case）。六项检查：

1. `orphan_sites`：地点指向不存在的项目；
2. `findings_without_site`：观察项缺少地点；
3. `status_audit_mismatch`：观察项状态与最后一条审计事件隐含状态不一致；
4. `orphan_attachments`：附件指向不存在的观察项；
5. `duplicate_site_codes`：项目内地点编码重复（模板批量生成场景）；
6. `risk_summary_mismatch`：风险概览统计与明细数量不一致（如发现非法 risk_level 漂移数据）。

前端「系统检查」视图（顶部导航）展示每项检查的通过状态、问题数量和问题明细表格。

## 风险统计口径

- 所有风险统计（risk_sites、risk_summary、项目列表 risk_summary）均**排除 archived 观察项**；归档数量以 `archived_count` 单独返回，地点详情接口仍可查看归档历史。
- `unreviewed_count`：finding_status 为 draft / submitted / reviewing 的观察项数（尚未得出复核结论）。
- `max_risk_level`：按 low < medium < high < critical 取最高，无（非归档）观察项时为 null。
- `last_updated_at`：非归档观察项中最大的 updated_at。
- 项目列表的 `region` 过滤按项目下地点的 region 匹配，`max_risk_level` 按项目级最高风险等级精确匹配；统计在后端基于数据库聚合，前端不做本地计算。

风险等级：`low / medium / high / critical`。附件仅保存元数据（file_name、file_type、storage_note、linked_finding_id），不处理真实上传。
