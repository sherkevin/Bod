<!--
 * @Author: shervin sherkevin@163.com
 * @Date: 2026-01-15 14:35:48
 * @LastEditors: shervin sherkevin@163.com
 * @LastEditTime: 2026-01-16 11:11:13
 * @FilePath: \Bod\TODO.md
 * @Description: 
 * 
 * Copyright (c) 2026 by ${git_name_email}, All Rights Reserved. 
-->
# 项目进度跟踪 (Project Status)

本文档基于现有代码库 (`backend/`, `frontend/`) 和设计文档 (`README.md`, `README_MVP.md`) 整理。

## ✅ 已完成功能 (Completed)

### 核心功能 (MVP)
- [x] **语音录入与上传**: 前端支持录音并上传至后端 API (`POST /api/v1/voice`)。
- [x] **本地语音转文字 (ASR)**: 后端集成 `faster-whisper` (tiny model)，支持离线/本地语音转写。
- [x] **智能语义分析 (LLM)**: 集成 OpenAI SDK (DeepSeek/Moonshot)，能从文本中提取动作、重量、组数、次数。
- [x] **基础数据持久化**: 使用 SQLAlchemy + SQLite/PostgreSQL 存储用户 (`User`) 和训练日志 (`WorkoutLog`)。
- [x] **历史记录查看**: 前端可以展示训练日志列表，包括解析出的结构化数据和 AI 反馈。
- [x] **基础 Web UI**: 简单的 HTML/JS 前端，支持录音交互和日志展示。
- [x] **用户认证系统**: 实现注册、登录和 JWT 认证 (`/register`, `/token`)，支持多用户隔离。

## 🚧 进行中/部分完成 (In Progress / Partial)
- [ ] **Docker 部署**: 有 `Dockerfile` 和 `docker-compose.yml`，但需要确认是否完全可用（特别是 GPU 支持和环境变量配置）。

## 📝 待办任务 (To Do)

### 核心功能补全 (Backlog)
- [x] **LangGraph Agent 编排**: 已创建 Agent 结构（State, Nodes, Graph）并集成到主 API，目前支持基本的意图分类和提取。
- [x] **Agent 持久化 (Persistence)**: 已实现基于 MemorySaver 的状态记忆，API 已更新支持 `thread_id` 参数。
- [x] **视觉识别 (VLM)**: 实现图片上传 API，集成 Qwen-VL/GPT-4o 进行器械识别 (`POST /api/v1/image`)。
- [x] **语音反馈 (TTS)**: 将 AI 的文本反馈转换为语音并在前端播放 (`POST /api/v1/tts`)。
- [x] **任务队列 (Celery)**: 引入异步任务队列处理耗时的 AI 推理任务，避免阻塞 API 请求。

### 进阶功能 (Advanced)
- [x] **数据可视化**: 添加图表展示训练进度（如力量增长曲线）。
- [x] **智能计划生成**: 根据历史数据和目标生成个性化训练计划。
- [x] **实时反馈优化**: 降低端到端延迟，提供更流畅的交互体验 (WebSocket)。
- [x] **PWA 支持**: 完善 Service Worker 和离线功能，使其更像原生 App。

### 代码质量与工程化
- [x] **单元测试**: 为 API 和 AI 服务添加测试用例 (`backend/tests/test_api.py`)。
- [ ] **错误处理**: 增强 ASR/LLM 调用失败时的重试机制和用户提示。
- [ ] **配置管理**: 完善 `.env` 配置项，区分开发和生产环境。
