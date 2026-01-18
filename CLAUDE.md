# CLAUDE.md

此文件为 Claude Code 提供项目上下文，帮助理解代码库结构和开发规范。

## 沟通规范

- **请使用中文与用户沟通**

## 项目概述

周报管理系统 - 企业周报在线填写、智能汇总与 Word 文档自动生成。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / SQLAlchemy (async) / SQLite
- **前端**: Vue 3 (Composition API) / Element Plus / Pinia / ECharts
- **AI**: Qwen / DeepSeek / OpenAI 兼容接口

## 项目结构

```
weekly-report/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 应用入口
│   │   ├── config.py       # 配置管理 (Pydantic Settings)
│   │   ├── database.py     # 异步数据库连接
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── routers/        # API 路由
│   │   ├── schemas/        # Pydantic 验证
│   │   ├── services/       # 业务逻辑
│   │   ├── tasks/          # 定时任务 (APScheduler)
│   │   └── utils/          # 工具函数
│   ├── data/               # 数据库和生成文档
│   └── .env                # 环境配置
│
├── frontend/                # Vue 3 前端
│   └── src/
│       ├── views/          # 页面组件
│       ├── api/            # Axios API 客户端
│       ├── stores/         # Pinia 状态
│       └── router/         # Vue Router
│
└── data/                    # 共享数据目录
```

## 常用命令

### 后端
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000   # 开发模式
pip install -r requirements.txt              # 安装依赖
```

### 前端
```bash
cd frontend
npm run dev      # 开发模式 (localhost:3000)
npm run build    # 生产构建
```

### 数据库
```bash
# SQLite 数据库位于 backend/data/weekly_report.db
sqlite3 data/weekly_report.db ".tables"      # 查看表
sqlite3 data/weekly_report.db ".schema users" # 查看结构
```

## 关键模块说明

### 后端路由 (backend/app/routers/)
| 文件 | 前缀 | 功能 |
|------|------|------|
| auth.py | /api/auth | 登录认证 |
| reports.py | /api/reports | 周报 CRUD |
| summary.py | /api/summary | 汇总和文档 |
| admin.py | /api/admin/users | 用户管理 |

### 后端服务 (backend/app/services/)
| 文件 | 功能 |
|------|------|
| auth_service.py | 用户认证、JWT |
| report_service.py | 周报增删改查 |
| summary_service.py | 数据汇总、LLM 分析 |
| llm_service.py | LLM API 调用 |
| word_generator.py | Word 文档生成 |

### 数据模型 (backend/app/models/)
| 模型 | 表名 | 说明 |
|------|------|------|
| User | users | 用户信息 |
| Report | reports | 周报内容 |
| WeeklySummary | weekly_summary | 汇总缓存 |

### 前端页面 (frontend/src/views/)
| 文件 | 路由 | 功能 |
|------|------|------|
| Login.vue | /login | 登录 |
| Report.vue | /report | 周报编辑 |
| Chart.vue | /chart | 可视化汇总 |
| Admin/Users.vue | /admin/users | 用户管理 |

## 代码规范

### 后端
- 使用 async/await 异步编程
- Pydantic 做请求/响应验证
- 依赖注入获取数据库会话: `db: AsyncSession = Depends(get_db)`
- 权限检查: `current_user: User = Depends(get_current_user)`

### 前端
- Vue 3 Composition API + `<script setup>` 语法
- Pinia 管理全局状态
- Element Plus 组件库
- API 调用统一放在 `src/api/` 目录

## LLM 智能解析机制

**触发时机**: 用户保存/提交周报时

**流程**:
1. 用户填写周报 → 前端调用 `/parse-preview` 预览解析结果
2. 用户确认或修正后保存 → 结构化数据存入 `report_items` 表
3. 汇总统计直接使用 `report_items` 数据，不再重复调用 LLM

**关键代码**:
- 解析服务: `backend/app/services/report_parser_service.py`
- 汇总统计: `backend/app/services/summary_service.py:get_weekly_report_dashboard()`

**模型选择（重要）**:
- ✅ 推荐: `qwen-plus`、`deepseek-chat` — 解析准确率高
- ⚠️ 不建议: `qwen-flash` — 准确率一般，仅在成本敏感场景考虑
- ❌ 禁止: `qwen-turbo` — 项目匹配准确率低，会导致分类错误

## 项目活跃度排序

项目选择下拉列表根据活跃度自动排序，活跃项目优先显示，便于快速选择。

**活跃度判断依据**（最近 30 天内有使用记录）:
- **日报**: 基于 `DailyReport.date` 字段，统计该日期在 30 天内的日报条目
- **周报**: 基于 `Report.year` + `Report.week_num` 字段，统计最近 5 周的周报条目

**前端展示**:
- 使用 Element Plus `el-option-group` 分组显示
- "常用项目": 最近 30 天有使用记录的项目
- "其他项目": 无近期使用记录的项目

**关键代码**:
- 后端 API: `backend/app/routers/reports.py` → `GET /api/reports/projects`
- 前端组件: `frontend/src/views/DailyReport.vue` → `activeProjects` / `inactiveProjects` 计算属性

**注意**: 日报将作为主要数据来源，周报后续将自动生成。

## 环境变量 (.env)

```env
DATABASE_URL=sqlite+aiosqlite:///./data/weekly_report.db
SECRET_KEY=xxx
LLM_PROVIDER=qwen          # qwen/deepseek/openai
OPENAI_API_KEY=xxx
OPENAI_BASE_URL=https://...
DEEPSEEK_API_KEY=xxx
DASHSCOPE_API_KEY=xxx
```

## 部署

详细文档: `docs/deployment.md`

### 一键部署（推荐）
```bash
./scripts/deploy-to-mcp2.sh        # 同步代码
./scripts/deploy-to-mcp2.sh --db   # 同步代码 + 数据库（自动备份）
```

### 部署流程
1. 推送代码 → `git push origin HEAD:mcp2`
2. 服务器拉取 → `git reset --hard origin/mcp2`
3. **前端构建** → `npm run build`（必须！）
4. **后端重启** → 重启 uvicorn（必须！）

> ⚠️ 代码同步后必须重建前端、重启后端，否则改动不生效

### Git 仓库

| 远程 | 地址 | 说明 |
|------|------|------|
| origin | git@github.com:realyn/weekly-report.git | GitHub 主仓库 |
| mcp2 | mcp2:~/projects/weekly-report | 生产服务器 (SSH) |

## 注意事项

1. **周报状态**: draft(草稿) / submitted(已提交)，提交后不可修改
2. **定时任务**: 每周六 18:00 自动汇总 (`tasks/scheduler.py`)
3. **LLM 降级**: 若 LLM 调用失败，回退到关键词匹配 (`summary_service.py:64-93`)
4. **数据库迁移**: 使用 SQLAlchemy create_all，无 Alembic
