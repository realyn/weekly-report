#!/bin/bash
# 部署脚本：同步代码到 mcp2 并确保生效
# 使用方法: ./scripts/deploy-to-mcp2.sh [--db]
#   --db  同时同步数据库文件（会先备份服务器端数据库）

set -e

REMOTE="mcp2"
REMOTE_DIR="~/projects/weekly-report"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "📦 部署到 mcp2"
echo "=========================================="

# 1. 推送代码到 origin/mcp2
echo ""
echo "📤 [1/4] 推送代码到 origin/mcp2..."
git push origin HEAD:mcp2

# 2. 远程拉取代码
echo ""
echo "📥 [2/4] mcp2 拉取最新代码..."
ssh $REMOTE "cd $REMOTE_DIR && git fetch origin && git reset --hard origin/mcp2"

# 3. 重新构建前端
echo ""
echo "🔨 [3/4] 重新构建前端..."
ssh $REMOTE "cd $REMOTE_DIR/frontend && npm run build"

# 4. 重启后端服务
echo ""
echo "🔄 [4/4] 重启后端服务..."
ssh $REMOTE "cd $REMOTE_DIR/backend && pkill -f 'uvicorn app.main:app' || true && sleep 1 && nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"

# 可选：同步数据库
if [[ "$1" == "--db" ]]; then
    echo ""
    echo "=========================================="
    echo "⚠️  警告：即将同步数据库"
    echo "=========================================="
    echo "此操作会用本地数据库覆盖服务器数据库！"
    echo ""
    echo "本地数据库: $LOCAL_DIR/backend/data/weekly_report.db"
    echo "目标位置:   $REMOTE:$REMOTE_DIR/backend/data/weekly_report.db"
    echo ""
    read -p "确认要继续吗？(y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "❌ 已取消数据库同步"
        exit 0
    fi

    echo ""
    echo "💾 同步数据库文件..."

    # 先备份服务器端数据库
    BACKUP_NAME="weekly_report.db.backup_${TIMESTAMP}"
    echo "   📋 备份服务器端数据库: $BACKUP_NAME"
    ssh $REMOTE "cd $REMOTE_DIR/backend/data && cp weekly_report.db $BACKUP_NAME"

    # 同步本地数据库到服务器
    echo "   📤 上传本地数据库..."
    scp "$LOCAL_DIR/backend/data/weekly_report.db" "$REMOTE:$REMOTE_DIR/backend/data/weekly_report.db"

    # 重启后端以重新连接数据库
    echo "   🔄 重启后端服务..."
    ssh $REMOTE "cd $REMOTE_DIR/backend && pkill -f 'uvicorn app.main:app' || true && sleep 1 && nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"

    echo "   ✅ 数据库同步完成，备份文件: $BACKUP_NAME"
fi

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "验证方式:"
echo "  1. 访问 https://mcp.realyn.cn/weekly-report/"
echo "  2. 检查后端: ssh mcp2 'pgrep -fa uvicorn'"
echo ""
