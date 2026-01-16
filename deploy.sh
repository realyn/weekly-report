#!/bin/bash
# 周报系统一键部署脚本
# 用法: ./deploy.sh [选项]
#   --code-only    只同步代码（不同步数据）
#   --data-only    只同步数据（不同步代码）
#   --all          同步全部（默认）

set -e

SERVER="mcp2"
REMOTE_PATH="~/projects/weekly-report"
LOCAL_PATH="/Users/yn/projects/weekly-report"

log_step() { echo -e "\n[$1] $2"; }

echo "=========================================="
echo "  周报系统部署脚本"
echo "=========================================="

# 解析参数
SYNC_CODE=true
SYNC_DATA=true

case "$1" in
    --code-only) SYNC_DATA=false ;;
    --data-only) SYNC_CODE=false ;;
esac

STEP=1

# 同步代码
if [ "$SYNC_CODE" = true ]; then
    log_step $((STEP++)) "构建前端..."
    cd "$LOCAL_PATH/frontend" && npm run build

    log_step $((STEP++)) "提交代码到 Git..."
    cd "$LOCAL_PATH"
    git add -A
    if git diff --cached --quiet; then
        echo "没有需要提交的更改"
    else
        read -p "请输入提交信息: " commit_msg
        git commit -m "$commit_msg"
    fi
    git push origin main

    log_step $((STEP++)) "同步代码到服务器..."
    ssh $SERVER "cd $REMOTE_PATH && git pull origin main"

    log_step $((STEP++)) "同步前端构建文件..."
    rsync -avz --delete "$LOCAL_PATH/frontend/dist/" "$SERVER:$REMOTE_PATH/frontend/dist/"
fi

# 同步数据
if [ "$SYNC_DATA" = true ]; then
    log_step $((STEP++)) "同步数据文件..."
    rsync -avz "$LOCAL_PATH/backend/data/" "$SERVER:$REMOTE_PATH/backend/data/"
fi

# 重启服务
log_step $((STEP++)) "重启后端服务..."
ssh $SERVER "pkill -f 'uvicorn.*8010' 2>/dev/null || true; sleep 2; cd $REMOTE_PATH/backend && source venv/bin/activate && nohup uvicorn app.main:app --host 127.0.0.1 --port 8010 > /tmp/weekly-report.log 2>&1 &"
sleep 3

# 验证
log_step $((STEP++)) "验证服务状态..."
if ssh $SERVER "ps aux | grep 'uvicorn.*8010' | grep -v grep" > /dev/null; then
    echo "后端服务运行正常"
else
    echo "后端服务启动失败"
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "  访问地址: https://mcp.realyn.cn/weekly-report/"
echo "=========================================="
