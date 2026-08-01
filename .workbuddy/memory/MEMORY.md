# 培英 AI 行政平台项目笔记

## 项目概况
- 培英中學 AI 数智化行政平台，目前开发 Tommy 子系统
- 多角色平台：Apple, Danielle, Steven, Tommy, Wendy, 梁小姐, Admin
- Tommy 核心需求：文件智能归档 + 租务管理（俊杰花园 8住宅+9车位）

## 技术栈
- 前端：Next.js 16 + TypeScript + Tailwind CSS + App Router
- 后端：FastAPI + SQLAlchemy 2 + Pydantic + Celery + Redis
- 数据库：PostgreSQL (生产) / SQLite (开发模式)
- 项目结构：monorepo (school-ai-platform/)

## 设计原则（来自 design.md）
- AI 结果必须可复核（人工确认后才入库）
- Tommy 登录后只看到自己的子系统入口
- 首屏信息量控制，辅助功能放入弹窗
- UI 风格对标 前端页面参考.html 的配色（深青绿主色 #23675f）
- OCR/AI 先 mock，后续接入真实服务

## 开发状态
- 阶段1-6 基本完成（项目脚手架 + 登录权限 + 文件OCR审计 + Tommy归档模块 + Tommy租务模块 + 侧边栏）
- 扫描件处理、归档记录、个人设定为占位页面
- 后端 API 全部 mock 模式运行
