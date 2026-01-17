# 部署指南

## 服务器信息

| 环境 | 地址 | 说明 |
|------|------|------|
| 本地开发 | localhost:8000 / localhost:3000 | 开发调试 |
| 生产服务器 | mcp2 (mcp.realyn.cn) | 通过 SSH 配置访问 |

## 一键部署

```bash
# 只同步代码（推荐）
./scripts/deploy-to-mcp2.sh

# 同步代码 + 数据库（会自动备份服务器数据库）
./scripts/deploy-to-mcp2.sh --db
```

## 部署脚本执行流程

1. **推送代码** - `git push origin HEAD:mcp2`
2. **服务器拉取** - `git reset --hard origin/mcp2`
3. **前端构建** - `npm run build`（必须！否则改动不生效）
4. **后端重启** - `pkill + uvicorn`（必须！否则改动不生效）
5. **[可选] 数据库同步** - 先备份再覆盖

## 手动部署步骤

如需手动操作，按以下顺序执行：

### 1. 同步代码

```bash
# 本地推送
git push origin HEAD:mcp2

# 服务器拉取
ssh mcp2 "cd ~/projects/weekly-report && git fetch origin && git reset --hard origin/mcp2"
```

### 2. 重建前端

```bash
ssh mcp2 "cd ~/projects/weekly-report/frontend && npm run build"
```

> ⚠️ **必须执行**：前端源码变更后，不重建 dist 目录，改动不会生效

### 3. 重启后端

```bash
ssh mcp2 "cd ~/projects/weekly-report/backend && pkill -f 'uvicorn app.main:app' || true"
ssh mcp2 "cd ~/projects/weekly-report/backend && nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"
```

> ⚠️ **必须执行**：后端代码变更后，不重启服务，改动不会生效

### 4. 同步数据库（可选）

```bash
# 先备份服务器数据库
ssh mcp2 "cd ~/projects/weekly-report/backend/data && cp weekly_report.db weekly_report.db.backup_$(date +%Y%m%d_%H%M%S)"

# 上传本地数据库
scp backend/data/weekly_report.db mcp2:~/projects/weekly-report/backend/data/

# 重启后端
ssh mcp2 "cd ~/projects/weekly-report/backend && pkill -f 'uvicorn app.main:app' || true && sleep 1 && nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"
```

## 验证部署

```bash
# 检查后端进程
ssh mcp2 "pgrep -fa uvicorn"

# 检查前端构建时间
ssh mcp2 "ls -la ~/projects/weekly-report/frontend/dist/index.html"

# 访问网站
open https://mcp.realyn.cn/weekly-report/
```

## 常见问题

### Q: 代码同步了但改动没生效？

| 改动类型 | 需要的操作 |
|---------|-----------|
| 前端代码 | `npm run build` |
| 后端代码 | 重启 uvicorn |
| 数据库结构 | 重启 uvicorn |
| 静态配置文件 | 无需额外操作 |

### Q: 数据库备份在哪里？

服务器端备份位置：`~/projects/weekly-report/backend/data/weekly_report.db.backup_*`

查看备份文件：
```bash
ssh mcp2 "ls -la ~/projects/weekly-report/backend/data/*.backup_*"
```

### Q: 如何回滚数据库？

```bash
# 查看可用备份
ssh mcp2 "ls -la ~/projects/weekly-report/backend/data/*.backup_*"

# 恢复指定备份
ssh mcp2 "cd ~/projects/weekly-report/backend/data && cp weekly_report.db.backup_20260117_104647 weekly_report.db"

# 重启后端
ssh mcp2 "cd ~/projects/weekly-report/backend && pkill -f 'uvicorn app.main:app' || true && sleep 1 && nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"
```
