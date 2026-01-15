# 周报管理系统

企业周报在线填写、智能汇总与 Word 文档自动生成系统。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ / FastAPI / SQLAlchemy / SQLite(MySQL) |
| 前端 | Vue 3 / Element Plus / Pinia / ECharts |
| 文档 | python-docx |
| 定时 | APScheduler |
| AI | Qwen / DeepSeek / OpenAI 兼容接口 |

## 目录结构

```
weekly-report/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   ├── models/            # 数据模型
│   │   ├── routers/           # API 路由
│   │   ├── schemas/           # 数据验证
│   │   ├── services/          # 业务逻辑
│   │   ├── tasks/             # 定时任务
│   │   └── utils/             # 工具函数
│   ├── data/                  # 数据存储
│   │   ├── weekly_report.db   # SQLite 数据库
│   │   ├── documents/         # 生成的文档
│   │   └── projects.json      # 项目知识库
│   ├── .env                   # 环境配置
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── views/             # 页面组件
│   │   ├── components/        # 通用组件
│   │   ├── api/               # API 客户端
│   │   ├── stores/            # Pinia 状态
│   │   └── router/            # 路由配置
│   ├── package.json
│   └── vite.config.js
│
└── data/                       # 共享数据目录
    ├── documents/             # Word 文档
    └── templates/             # 文档模板
```

## 核心功能

### 1. 用户认证
- JWT 令牌认证（24小时有效期）
- Bcrypt 密码加密
- 基于角色的访问控制（管理员/普通用户）

### 2. 周报管理
- 按周填写本周工作和下周计划
- 支持逐条录入工作项
- 草稿/已提交状态管理
- 历史周报查看

### 3. 智能汇总
- 汇总所有员工周报数据
- LLM 智能分析项目参与度和工作分类
- 可视化图表展示（ECharts）
- 自动生成 Word 文档

### 4. 定时任务
- 每周六 18:00 自动汇总生成文档

### 5. 用户管理（管理员）
- 创建/编辑/删除用户
- 重置用户密码
- 部门和角色管理

## 系统架构

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3)                          │
├─────────────────────────────────────────────────────────────┤
│  Login.vue    Report.vue    Chart.vue    Admin/Users.vue    │
│      │            │             │              │             │
│      └────────────┴─────────────┴──────────────┘             │
│                          │                                   │
│                    Pinia Store                               │
│                    (user / report)                           │
│                          │                                   │
│                    Axios Client                              │
└─────────────────────────────────────────────────────────────┘
                           │
                      HTTP API
                           │
┌─────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI)                          │
├─────────────────────────────────────────────────────────────┤
│  Routers                                                     │
│  ├── /api/auth      认证接口                                 │
│  ├── /api/reports   周报接口                                 │
│  ├── /api/summary   汇总接口                                 │
│  └── /api/admin     管理接口                                 │
├─────────────────────────────────────────────────────────────┤
│  Services                                                    │
│  ├── auth_service        用户认证                            │
│  ├── report_service      周报 CRUD                           │
│  ├── summary_service     数据汇总                            │
│  ├── llm_service         LLM 调用                            │
│  └── word_generator      文档生成                            │
├─────────────────────────────────────────────────────────────┤
│  Models (SQLAlchemy)                                         │
│  ├── User           用户表                                   │
│  ├── Report         周报表                                   │
│  └── WeeklySummary  汇总缓存表                               │
└─────────────────────────────────────────────────────────────┘
                           │
                       Database
                    (SQLite / MySQL)
```

### LLM 智能分析流程

```
用户提交周报 (status=submitted)
        │
        ▼
  BackgroundTasks 触发
        │
        ▼
┌───────────────────────┐
│  trigger_llm_analysis │
│  ├── 收集该周所有周报   │
│  ├── 调用 LLM 分析      │
│  │   ├── 提取项目名称   │
│  │   ├── 分类工作类型   │
│  │   └── 计算参与度     │
│  └── 缓存到数据库       │
└───────────────────────┘
        │
        ▼
  weekly_summary.llm_analysis (JSON)
        │
        ▼
  用户查看汇总页面
        │
        ▼
  get_cached_llm_analysis()
        │
        ▼
  返回缓存的分析结果
```

## API 接口

### 认证 `/api/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /login | 用户登录 |
| GET | /me | 获取当前用户 |
| PUT | /password | 修改密码 |

### 周报 `/api/reports`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /current | 获取当前周周报 |
| GET | / | 获取周报列表 |
| GET | /{id} | 获取单个周报 |
| POST | / | 创建周报 |
| PUT | /{id} | 更新周报 |
| DELETE | /{id} | 删除周报 |

### 汇总 `/api/summary`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /weekly | 获取周汇总数据 |
| GET | /dashboard | 获取可视化面板 |
| GET | /chart-data | 获取图表统计 |
| GET | /download/{year}/{week} | 下载 Word 文档 |

### 管理 `/api/admin/users`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 用户列表 |
| POST | / | 创建用户 |
| PUT | /{id} | 更新用户 |
| DELETE | /{id} | 删除用户 |
| PUT | /{id}/reset-password | 重置密码 |

## 数据模型

### User 用户表
```sql
CREATE TABLE users (
    id          INTEGER PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,
    real_name   VARCHAR(50) NOT NULL,
    department  VARCHAR(50),
    role        VARCHAR(20) DEFAULT 'user',  -- admin/user
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  DATETIME,
    updated_at  DATETIME
);
```

### Report 周报表
```sql
CREATE TABLE reports (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER REFERENCES users(id),
    year           INTEGER NOT NULL,
    week_num       INTEGER NOT NULL,
    this_week_work TEXT,      -- 本周工作（每行一条）
    next_week_plan TEXT,      -- 下周计划（每行一条）
    status         VARCHAR(20) DEFAULT 'draft',  -- draft/submitted
    created_at     DATETIME,
    updated_at     DATETIME,
    UNIQUE(user_id, year, week_num)
);
```

### WeeklySummary 汇总表
```sql
CREATE TABLE weekly_summary (
    id           INTEGER PRIMARY KEY,
    year         INTEGER NOT NULL,
    week_num     INTEGER NOT NULL,
    summary_data TEXT,      -- 汇总数据 JSON
    statistics   TEXT,      -- 统计数据 JSON
    llm_analysis TEXT,      -- LLM 分析结果缓存 JSON
    doc_path     VARCHAR(255),
    created_at   DATETIME,
    analyzed_at  DATETIME,
    UNIQUE(year, week_num)
);
```

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- SQLite 或 MySQL

### 后端安装

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库和 LLM API

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端安装

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

### 访问地址

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 默认账号

- 管理员: admin / admin123

## 环境变量配置

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/weekly_report.db

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM 配置
LLM_PROVIDER=qwen  # qwen/deepseek/openai
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DASHSCOPE_API_KEY=your-dashscope-key
```

## 生产部署

### 直接部署

1. 后端使用 gunicorn 或 uvicorn 运行
2. 前端 `npm run build` 后用 nginx 托管静态文件
3. 配置 nginx 反向代理 API 请求

### 生产环境配置

修改 `backend/.env`:
```env
DATABASE_URL=mysql+aiomysql://user:pass@host:3306/weekly_report
SECRET_KEY=your-production-secret-key
DEBUG=false
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 一键部署 (deploy.sh)

### 部署原则

**本地环境是数据主源**，所有修改应在本地完成测试后再同步到服务器。

### 为什么本地调试好后同步到服务器会出问题？

本地和服务器之间可能存在以下差异：

| 差异类型 | 说明 | 解决方案 |
|---------|------|---------|
| 数据库结构 | 新增字段未同步 | 运行 `migrate.py` |
| 数据文件 | projects.json、embeddings 等 | 使用 `--data-only` 同步 |
| 环境变量 | .env 中的 LLM API Key 等 | 手动检查服务器 .env |
| 前端构建 | dist/ 目录未更新 | 部署前执行 `npm run build` |

### 使用方法

```bash
# 完整部署（默认）：代码 + 数据
./deploy.sh

# 仅同步代码（不覆盖服务器数据）
./deploy.sh --code-only

# 仅同步数据（保留服务器代码）
./deploy.sh --data-only
```

### 部署流程

```
./deploy.sh
    │
    ├── [1/5] 构建前端 (npm run build)
    │
    ├── [2/5] 提交代码到 Git
    │
    ├── [3/5] 服务器拉取代码 (git pull)
    │
    ├── [4/5] rsync 同步前端 dist/
    │
    ├── [5/5] rsync 同步数据文件
    │
    └── 重启后端服务 (uvicorn)
```

### 数据库迁移

如果新增了数据库字段，需要在服务器上运行迁移脚本：

```bash
ssh mcp2 "cd ~/projects/weekly-report/backend && source venv/bin/activate && python scripts/migrate.py"
```

迁移脚本 `backend/scripts/migrate.py` 会自动检测并添加缺失的列：
- `users.must_change_password` - 首次登录强制改密
- `weekly_summary.llm_analysis` - LLM 分析缓存
- `weekly_summary.analyzed_at` - 分析时间戳

### 注意事项

1. **首次部署**：确保服务器 `.env` 配置完整（特别是 LLM API Key）
2. **数据覆盖**：`--data-only` 会覆盖服务器数据，谨慎使用
3. **服务重启**：部署脚本会自动重启后端服务
4. **验证部署**：部署完成后检查 https://mcp.realyn.cn/weekly-report/ 是否正常

## 使用说明

### 普通用户

1. **登录系统**：使用管理员分配的账号密码登录
2. **填写周报**：在周报页面填写本周工作和下周计划
3. **提交周报**：确认无误后点击提交（提交后不可修改）
4. **查看汇总**：在图表页面查看团队汇总和可视化数据

### 管理员

1. **用户管理**：创建新用户、重置密码、管理权限
2. **数据查看**：查看所有用户的周报提交情况
3. **文档下载**：下载自动生成的周报汇总 Word 文档

## 开发指南

### 添加新的 API 路由

1. 在 `routers/` 目录创建路由文件
2. 在 `main.py` 注册路由
3. 在 `services/` 编写业务逻辑
4. 在 `schemas/` 定义数据验证

### 添加新的页面

1. 在 `views/` 创建 Vue 组件
2. 在 `router/index.js` 添加路由
3. 在 `api/` 添加 API 调用函数

### LLM 提供商切换

修改 `.env` 中的 `LLM_PROVIDER` 配置：
- `qwen` - 阿里通义千问（需要 DASHSCOPE_API_KEY 或 OPENAI 兼容配置）
- `deepseek` - DeepSeek（需要 DEEPSEEK_API_KEY）
- `openai` - OpenAI 或兼容接口

## 常见问题

### Q: 如何重置管理员密码？
```python
# 使用 Python 脚本
from app.utils.security import get_password_hash
print(get_password_hash("new_password"))
# 然后在数据库中更新 password 字段
```

### Q: 如何修改定时任务时间？
编辑 `tasks/scheduler.py`：
```python
scheduler.add_job(
    weekly_summary_job,
    'cron',
    day_of_week='sat',  # 星期几
    hour=18,            # 小时
    minute=0            # 分钟
)
```

### Q: 如何添加新的项目关键词？
编辑 `data/projects.json` 或让 LLM 自动学习新项目。

## 依赖版本

### 后端
```
FastAPI 0.109.0
uvicorn 0.27.0
SQLAlchemy 2.0.25
Pydantic 2.5.3
python-jose 3.3.0
passlib 1.7.4
python-docx 1.1.0
APScheduler 3.10.4
aiosqlite 0.19.0
httpx 0.27.0
```

### 前端
```
Vue 3.5.x
Vue Router 4.x
Pinia 3.x
Element Plus 2.x
axios 1.x
echarts 6.x
Vite 7.x
```

## 许可证

MIT License
