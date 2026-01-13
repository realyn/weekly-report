#!/bin/bash

# 启动后端
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 启动前端
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "后端运行在: http://localhost:8000"
echo "前端运行在: http://localhost:3000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
