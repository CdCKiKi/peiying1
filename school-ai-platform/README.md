# School AI Platform（学校智能平台）

一款用于学校/教育场景的全栈示例平台，包含基于 Next.js 的前端（Web 仪表盘与登录）与独立的后端服务（位于 apps/api）。前端使用 Next.js App Router + TypeScript 构建，项目包含可复用组件、API 调用封装与仪表盘页面，适合作为学校管理、教学数据展示或 AI 辅助教学系统的前端基座。

## 技术栈（推断）
- 前端
  - Next.js（App Router，TypeScript）
  - React
  - TypeScript
  - PostCSS（项目包含 postcss.config.mjs）
  - CSS（全局样式 / globals.css）
  - ESLint（存在 eslint.config.mjs）
- 后端
  - Python（项目整体语言成分中包含 Python，apps/api 目录用于后端服务）
- 其他
  - 静态/仪表盘页面（仓库包含 tommy_dashboard.html）
  - 打包与依赖：npm / package-lock.json（apps/web 下）

> 注：具体依赖包（如 Tailwind、axios、FastAPI/Flask 等）请参考各子项目的 package.json / requirements.txt。此 README 基于仓库结构与存在的配置文件推断，安装前建议核对具体文件。

---

## 功能特性（根据 apps/web/ 目录结构提取）
- 登录页（src/app/login/page.tsx）：提供用户登录入口（前端登录 UI）。
- 仪表盘（src/app/dashboard）：包含面向管理或教学数据展示的仪表盘页面与模块化组件。
- 主页面（src/app/page.tsx）与全局布局（src/app/layout.tsx、globals.css、favicon）：项目采用 App Router，内置全局样式与布局。
- 可复用组件（src/components/shared、src/components/modules）：组件化、模块化的 UI 组织方式，便于扩展。
- API 封装（src/lib/api.ts）：前端侧的 API 调用封装，集中管理后端请求与接口调用逻辑。
- 多应用目录结构（apps/）：前端（apps/web）与后端（apps/api）独立管理，便于本地并行开发与分离部署。

---

## 本地开发（快速开始）

以下提供典型的前后端分别启动步骤。请在运行前根据仓库中对应子项目的 README 或配置文件（package.json / requirements.txt / pyproject.toml 等）核对真实命令与依赖版本。

1. 克隆仓库
```bash
git clone https://github.com/shanshan1010/peiying11.git
cd peiying11/school-ai-platform
```

2. 前端（apps/web） — 本地开发
```bash
# 进入前端目录
cd apps/web

# 安装依赖（使用 npm 或 pnpm/yarn，根据项目偏好）
npm install

# 开发模式（默认监听 3000）
npm run dev
# 或（如果 package.json 定义了）
# pnpm dev
# yarn dev
```
访问 http://localhost:3000 查看前端界面。

常用命令（示例，实际请参考 apps/web/package.json）：
- npm run build — 生产构建
- npm start / npm run start — 启动 production 服务（若配置）
- npm run lint — 代码检查

3. 后端（apps/api） — 本地开发（如为 Python 服务）
```bash
cd ../../apps/api

# 建议使用虚拟环境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# 安装依赖（若有 requirements.txt）
pip install -r requirements.txt

# 启动（示例：FastAPI 的常用启动）
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
访问 http://localhost:8000（或后端指定端口）进行接口联调。若后端使用 Node.js，请使用相应的 npm install 与 npm run dev 命令。

4. 联调
- 确保前端的 API 基地址（如 NEXT_PUBLIC_API_BASE_URL）指向本地后端地址（例如 http://localhost:8000）。
- 前端的 src/lib/api.ts 提供请求封装，可在此处调整 base URL 或鉴权头。

---

## 项目结构说明（关键目录）
（只列出与开发运维密切相关的部分）

```
school-ai-platform/
├─ apps/
│  ├─ web/                 # Next.js 前端应用（TypeScript, App Router）
│  │  ├─ package.json
│  │  ├─ next.config.ts
│  │  ├─ postcss.config.mjs
│  │  ├─ src/
│  │  │  ├─ app/
│  │  │  │  ├─ page.tsx            # 首页/根页面
│  │  │  │  ├─ layout.tsx          # 全局布局
│  │  │  │  ├─ login/              # 登录页
│  │  │  │  └─ dashboard/          # 仪表盘页面
│  │  │  ├─ components/
│  │  │  │  ├─ modules/            # 模块化组件
│  │  │  │  └─ shared/             # 共享组件
│  │  │  └─ lib/
│  │  │     └─ api.ts              # API 封装（前端）
│  │  └─ public/                   # 静态资源
│  ├─ api/                 # 后端服务（Python / Node 等）——具体实现查看此目录
├─ infra/                  # 基础设施配置（部署脚本 / IaC）
└─ tommy_dashboard.html    # 单文件仪表盘示例/导出页面
```

各部分职责：
- apps/web：前端 UI、路由、样式与 API 调用逻辑。
- apps/api：后端 API，实现数据提供、鉴权或业务逻辑（需要查看该目录以确认框架与运行方式）。
- infra：部署与基础设施配置（可能包含 Docker、K8s、Terraform 等）。

---

## 环境变量（说明）
- 我在仓库的 web 子项目下未发现公开的 `.env.example` 文件（基于当前可见文件列表）。若项目中存在 `.env.example` 或类似示例，请优先参考该文件。
- 建议前端（apps/web）使用的常见环境变量示例（在根目录或 apps/web 下创建 `.env.local`）：

```
# 前端（Next.js）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_ENV=development
# 如果有第三方服务（示例）
NEXT_PUBLIC_ANALYTICS_KEY=your_analytics_key
```

- 常见后端环境变量（在 apps/api 下创建 .env 或通过启动环境注入）：

```
# 后端示例
API_PORT=8000
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
SECRET_KEY=changeme
```

请根据实际后端实现（apps/api）中的代码或配置文件（如 settings.py、config.py、.env.example、docker-compose.yml 等）补充准确的变量名与说明。

---

## 开发建议与注意事项
- 在首次运行前，请核对 apps/web/package.json 与 apps/api 下的依赖清单，确保 Node / Python 版本匹配（建议在项目中添加 engines 或 runtime 指定）。
- 若使用数据库或外部 AI服务（OpenAI 等），请在 infra/ 或相应服务文档中查找部署与密钥管理方式，并避免将敏感信息提交到仓库。
- 使用 .env.local / .env.development 等文件进行本地开发配置，切勿将实际秘钥提交到版本库。

---

## 常见命令速查（示例）
- 前端
  - 安装：cd apps/web && npm install
  - 开发：npm run dev
  - 构建：npm run build
  - 启动（生产）：npm start
- 后端（Python 示例）
  - 安装依赖：pip install -r requirements.txt
  - 开发启动：uvicorn main:app --reload

---

## 后续操作
我已经准备好将此 README.md 提交到仓库的 school-ai-platform/ 目录下。请确认是否：
1) 覆盖（如果已存在 README.md 会被替换），或
2) 创建新文件（如 README_SCHOOL_AI.md）以避免覆盖。

如确认“覆盖”，我将把文件写到 `school-ai-platform/README.md`。