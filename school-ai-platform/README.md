# 培英 AI 行政平台

培英中學 AI 數智化行政管理平台 - Tommy 子系统

## 项目结构

```
school-ai-platform/
├─ apps/
│  ├─ web/                  # Next.js 前端 (TypeScript + Tailwind CSS)
│  └─ api/                  # FastAPI 后端 (Python)
├─ workers/
│  ├─ ocr_worker/           # OCR Worker (mock)
│  ├─ llm_worker/           # LLM Worker (mock)
│  └─ file_worker/
├─ infra/
│  ├─ docker-compose.yml    # PostgreSQL + Redis
│  └─ nginx/
├─ docs/
├─ packages/
└─ README.md
```

## 快速启动

### 前端

```bash
cd apps/web
npm install
npm run dev
# 访问 http://localhost:3000
```

测试帐号：tommy / tommy123 或 admin / admin123

### 后端

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 访问 http://localhost:8000/docs 查看 API 文档
```

开发模式使用 SQLite，无需 Docker。

### 生产环境

设置环境变量切换到 PostgreSQL：

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/school_ai
```

启动 Docker：

```bash
cd infra
docker compose up -d
```

## Tommy 子系统功能

| 页面 | 路径 | 功能 |
|---|---|---|
| 总览 | /dashboard/tommy | 快捷入口 + 统计 |
| 文件归档 | /dashboard/tommy/archive | OCR + AI分类 + 人工确认 + 归档 |
| 租务管理 | /dashboard/tommy/rental | 8住宅 + 9车位仪表板 |
| 扫描件处理 | /dashboard/tommy/scan | 批量 OCR（开发中） |
| 归档记录 | /dashboard/tommy/records | 历史查询（开发中） |
| 个人设定 | /dashboard/tommy/settings | 基础设定（开发中） |

## 后端 API

所有 API 前缀：`/api/v1`

| 模块 | 主要端点 |
|---|---|
| accounts | /accounts/login, /accounts/me |
| files | /files/upload |
| ocr | /ocr/jobs |
| ai | /ai/generate |
| tommy-archive | /tommy/archive-documents, /tommy/archive-documents/{id}/run-ocr, /confirm, /archive |
| tommy-rental | /tommy/rental-units, /tommy/rental-units/{id}/payments, /send-reminder, /generate-lease |
| audit | /audit/logs |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 16 + TypeScript + Tailwind CSS + App Router |
| 后端 | FastAPI + SQLAlchemy 2 + Pydantic |
| 数据库 | PostgreSQL (生产) / SQLite (开发) |
| 异步任务 | Celery + Redis |
| AI/OCR | Mock (后续接入真实 OCR/LLM) |

## 设计原则

- AI 结果必须人工确认后入库
- Tommy 登录后只看到自己的子系统
- 首屏信息量控制，辅助功能放入弹窗
- 对标 `前端页面参考.html` 的 UI 风格
