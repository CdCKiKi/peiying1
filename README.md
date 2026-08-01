# 培英中学 AI 数智化行政管理平台

> Pui Ying AI Digital Administration Platform

为香港培英中学量身打造的 AI 数智化行政管理平台，目标是让不同岗位的行政人员各自拥有专属的 AI 辅助工作台，通过 OCR、LLM、文档解析等能力，将重复繁琐的行政工作自动化。

---

## 📂 项目结构

```
peiying1-main/
├── design.md                 # 项目整体设计指引（架构、规范、协作流程）
├── README.md                 # 本文件 - 项目总览
├── 展示页面/                  # Tommy 子系统静态演示页面（HTML + Tailwind CDN）
│   └── index.html
└── school-ai-platform/       # 主代码工程（Monorepo）
    ├── apps/
    │   ├── web/              # Next.js 16 前端（TypeScript + Tailwind CSS）
    │   └── api/              # FastAPI 后端（Python）
    ├── infra/
    │   └── docker-compose.yml  # PostgreSQL + Redis 容器编排
    ├── workers/               # 异步任务 Worker（规划中）
    │   ├── ocr_worker/
    │   ├── llm_worker/
    │   └── file_worker/
    └── README.md              # 主工程详细文档
```

| 文件/目录 | 说明 |
| --------- | ---- |
| `design.md` | **必读。** 项目整体设计指引，包含架构设计、前后端规范、AI/OCR 规范、权限设计、多人协作规范和开发流程模板。所有开发者在开始前应阅读此文件。 |
| `展示页面/index.html` | Tommy 子系统的静态 UI 演示页面，可直接在浏览器打开查看最终效果。用于快速对齐 UI 风格和交互流程。 |
| `school-ai-platform/` | 主代码仓库，包含完整的前后端工程代码。 |

---

## 🎯 项目目标

### 核心设计理念：「一个底座，多个子系统」

不同岗位的行政人员登录后只看到自己的专属工作台，但底层共用同一套基础设施：

| 共用能力 | 说明 |
| -------- | ---- |
| 登录与权限 | 统一 JWT 认证 + 基于角色的权限控制（RBAC） |
| 文件上传 | 统一文件存储与管理 |
| OCR 任务 | 扫描件文字识别（讯飞 OCR / 本地 Tesseract） |
| AI 生成任务 | 文档分类、内容生成、结构化抽取 |
| 审计日志 | 所有敏感操作自动记录 |
| 通知与邮件 | 统一消息推送 |

### 子系统规划

| 用户 | 子系统入口 | 核心功能 | 开发状态 |
| ---- | ---------- | -------- | -------- |
| **Tommy** | `/dashboard/tommy` | 文件智能归档、租务管理 | ✅ 开发中 |
| Apple | `/dashboard/apple` | 奖状奖学金、报价单、资产管理 | 🔜 规划中 |
| Danielle | `/dashboard/danielle` | 宿费对账、零用金 | 🔜 规划中 |
| Steven | `/dashboard/steven` | 标书报价、采购、库存 | 🔜 规划中 |
| Wendy | `/dashboard/wendy` | 家长通告、代课安排 | 🔜 规划中 |
| 梁小姐 | `/dashboard/leung` | 资讯汇总、薪酬计算 | 🔜 规划中 |
| Admin | `/dashboard/admin` | 用户管理、权限配置、系统设置 | 🔜 规划中 |

---

## 🚀 快速启动

### 前置要求

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **Docker**（仅生产模式需要 PostgreSQL/Redis）

### 1. 启动后端

```bash
cd school-ai-platform/apps/api

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（默认 SQLite，无需 Docker）
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档自动生成：访问 http://localhost:8000/docs

### 2. 启动前端

```bash
cd school-ai-platform/apps/web

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000

### 3. 测试账号

| 用户名 | 密码 | 角色 |
| ------ | ---- | ---- |
| `tommy` | `tommy123` | Tommy（文件归档 & 租务管理） |
| `admin` | `admin123` | 管理员 |

### 4. 生产环境（PostgreSQL + Redis）

```bash
cd school-ai-platform/infra
docker compose up -d

# 设置环境变量
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/school_ai
```

---

## 🛠 技术栈

| 层 | 技术 | 说明 |
| -- | ---- | ---- |
| **前端** | Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 | App Router，服务端组件优先 |
| **后端** | FastAPI + SQLAlchemy 2 + Pydantic v2 | 异步 Python，自动生成 OpenAPI 文档 |
| **数据库** | PostgreSQL 16（生产）/ SQLite（开发） | 开发模式零配置 |
| **缓存/队列** | Redis 7 | Celery / RQ 任务队列 |
| **OCR** | 讯飞 OCR / Tesseract / Mock | 可配置后端 |
| **LLM** | Mock（当前）/ OpenAI / 本地模型（规划） | 可配置后端 |
| **容器化** | Docker Compose | PostgreSQL + Redis |
| **认证** | JWT（HS256） | 24 小时过期 |

---

## 📋 当前实现进度

### Tommy 子系统 ✅

Tommy 是第一个样板子系统，已实现核心流程：

| 功能模块 | 前端路由 | 后端 API 前缀 | 状态 |
| -------- | -------- | ------------ | ---- |
| 总览面板 | `/dashboard/tommy` | - | ✅ 已完成 |
| 文件智能归档 | `/dashboard/tommy/archive` | `/api/v1/tommy/archive-documents` | ✅ 已完成 |
| 租务管理 | `/dashboard/tommy/rental` | `/api/v1/tommy/rental-units` | ✅ 已完成 |
| 个人设定 | `/dashboard/tommy/settings` | - | 🚧 开发中 |

**核心流程：** 上传扫描件 → OCR 识别 → AI 自动分类/命名 → 人工确认 → 归档入库 → 写入审计日志

### 共用模块 ✅

| 模块 | 说明 |
| ---- | ---- |
| `accounts` | 用户登录、JWT 认证、角色权限 |
| `files` | 文件上传与管理 |
| `ocr` | OCR 任务创建与状态跟踪 |
| `ai` | AI 生成任务 |
| `audit` | 审计日志记录 |

---

## 🎨 UI 风格

- **设计风格：** 专业、清晰、低干扰，适合行政人员长时间使用
- **主色：** 深青绿 `#23675f`
- **背景：** `#F6F7F9`
- **卡片：** `#FFFFFF`
- **边框：** `#D8DEE6`
- **正文：** `#1D2939`
- **弱文本：** `#667085`

演示页面（`展示页面/index.html`）可直接在浏览器打开预览完整 UI 效果。

---

## 📐 设计原则

1. **AI 结果必须人工确认** — 涉及学生、财务、人事等敏感结论不允许自动入库
2. **用户隔离** — 登录后只看到自己的子系统，不显示其他角色功能
3. **先模块自治，再统一集成** — 每个子系统独立开发、独立验收，再挂载到统一平台
4. **敏感数据优先本地化** — 不将敏感原文发送到未评估的外部模型
5. **首屏信息量控制** — 辅助功能放入弹窗/抽屉，不堆叠在主页面

> 📖 详细设计规范和开发指南请阅读 [`design.md`](./design.md)

---

## 👩‍💻 开发指南

### 开发顺序

1. 模块独立开发（静态页面 → mock API → 验证交互）
2. 接真实 API
3. 接入 AI/OCR 任务
4. 添加权限校验
5. 添加审计日志
6. 通过统一导航和权限集成到平台

### API 规范

- 统一前缀：`/api/v1/{module}/{resource}`
- 统一返回格式：`{ "data": ..., "meta": { "request_id": "..." } }`
- 列表返回：`{ "data": [...], "pagination": { "page": 1, "page_size": 20, "total": 100 } }`

### 给 AI 的任务格式

每次提交 AI 任务时请明确：模块、用户、业务目标、已有文件、要修改的文件、不要修改的文件、输入数据、输出效果、验收标准。

---

## 📄 许可

内部项目，培英中学专用。

---

## 📮 相关资源

- [design.md](./design.md) — 项目整体设计指引
- [school-ai-platform/README.md](./school-ai-platform/README.md) — 主工程详细文档
- [展示页面/index.html](./展示页面/index.html) — Tommy 子系统 UI 演示
