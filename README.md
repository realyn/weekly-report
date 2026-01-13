# 周报管理系统

企业周报在线填写、汇总与 Word 文档自动生成系统。

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy + SQLite
- **前端**: Vue 3 + Element Plus + Pinia
- **文档生成**: python-docx

## 快速开始

### 后端

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 访问

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 默认账号

- 管理员: admin / admin123

## 功能

- 用户登录/登出
- 周报填写与提交
- 周报汇总查看
- Word 文档下载
- 用户管理（管理员）

## 部署

### 直接部署

1. 后端使用 gunicorn 或 uvicorn 运行
2. 前端 `npm run build` 后用 nginx 托管静态文件
3. 配置 nginx 反向代理 API 请求

### 生产环境配置

修改 `backend/.env`:
```
DATABASE_URL=mysql+aiomysql://user:pass@host:3306/weekly_report
SECRET_KEY=your-production-secret-key
DEBUG=false
```
