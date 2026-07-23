# 培英 AI 行政平台

培英中學 AI 數智化行政管理平台 - Tommy 子系统

## 项目结构

```
school-ai-platform/
├─ apps/
│  ├─ web/                  # Next.js 前端 (Next.js 16 + React 19 + TypeScript + Tailwind CSS)
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

### 前端（apps/web）

这是一个使用 Next.js 16 + React 19 + TypeScript + Tailwind CSS 的应用。项目中已经包含了常用的 npm 脚本：

- `npm run dev` — 本地开发（next dev）
- `npm run build` — 生产构建（next build）
- `npm run start` — 生产启动（next start）
- `npm run lint` — 运行 ESLint

建议在仓库根目录或 `school-ai-platform` 下运行下面命令进入前端目录：

```bash
cd apps/web
npm install
npm run dev
# 或者使用 yarn / pnpm / bun：
# yarn dev
# pnpm dev
# bun dev
```

默认开发服务器监听 http://localhost:3000。要开始编辑页面，可修改 `app/page.tsx`（使用 App Router），保存后浏览器会热重载。

测试帐号：tommy / tommy123 或 admin / admin123

备注：前端 package.json 指定了 Next.js 16、React 19、tailwindcss v4 等依赖；若在本地遇到问题，请确保 Node 版本与 Next.js 16 的兼容性（常见使用 Node 18+）。

### 后端（apps/api）

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 访问 http://localhost:8000/docs 查看 API 文档
```

开发模式使用 SQLite，无需 Docker。生产环境可通过环境变量切换到 PostgreSQL。

### 生产环境

设置环境变量切换到 PostgreSQL：

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/school_ai
```

启动 Docker Compose（infra 目录）：

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
| 前端 | Next.js 16 + React 19 + TypeScript + Tailwind CSS  + App Router |
| 后端 | FastAPI + SQLAlchemy 2 + Pydantic |
| 数据库 | PostgreSQL (生产) / SQLite (开发) |
| 异步任务 | Celery + Redis |
| AI/OCR | Mock (后续接入真实 OCR/LLM) |

## 开发提示

- 前端目录 `apps/web` 包含一个标准的 Next.js 应用；常见的编辑入口为 `app/` 下的路由文件（App Router）。
- 若要部署前端到 Vercel，可直接连接仓库并使用默认构建命令（`npm run build` / `npm run start`）。
- AI 处理结果必须人工确认后入库；界面和后端都遵循这一设计原则。
- Tommy 登录后只看到自己的子系统；首屏信息量控制，辅助功能放入弹窗。

