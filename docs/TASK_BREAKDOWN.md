# Bod 项目任务拆分总览

本文档将 Bod 个人健身助手项目的开发任务拆分为可并行执行的若干子任务。

## 任务依赖关系

```
                    ┌─────────────────┐
                    │  01-project-setup  │  (必须第一个完成)
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │ 02-backend  │ │ 03-frontend │ │ 04-database │
     │  -framework │ │  -framework │ │  -schema    │
     └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
              ┌─────────────────────────────┐
              │   并行执行 (可多个Agent一起)  │
              └─────────────────────────────┘
    ┌──────────────┬──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  05-    │ │  06-    │ │  07-    │ │  08-    │ │  09-    │
│  auth   │ │  user   │ │  equip  │ │  plan   │ │ workout │
│  认证系统│ │  用户档案│ │  器材管理│ │  计划生成│ │  训练执行│
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘

    ┌──────────────┬──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  10-    │ │  11-    │ │  12-    │ │  13-    │ │  14-    │
│  voice  │ │  notify │ │  coach  │ │  pwa    │ │ deploy  │
│  语音交互│ │  提醒打卡│ │  AI教练 │ │  离线支持│ │  部署配置│
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

## 任务列表

| # | 任务名称 | 分支名 | 说明 | 依赖 |
|---|----------|--------|------|------|
| 1 | project-setup | feat/project-setup | 项目脚手架、Docker配置、CI/CD | 无 |
| 2 | backend-framework | feat/backend-framework | FastAPI框架、目录结构、中间件 | 1 |
| 3 | frontend-framework | feat/frontend-framework | Next.js框架、目录结构、路由 | 1 |
| 4 | database-schema | feat/database-schema | 数据库表设计、Alembic迁移 | 1 |
| 5 | auth-system | feat/auth-system | JWT认证、注册登录、权限管理 | 2,4 |
| 6 | user-profile | feat/user-profile | 用户档案CRUD、目标管理 | 5 |
| 7 | equipment-management | feat/equipment-management | 器材识别、清单管理 | 5 |
| 8 | workout-plan | feat/workout-plan | 计划生成、展示、调整 | 6,7 |
| 9 | workout-execution | feat/workout-execution | 训练执行、日志记录 | 8 |
| 10 | voice-interaction | feat/voice-interaction | ASR/TTS集成、语音交互 | 9 |
| 11 | notification-checkin | feat/notification-checkin | 系统通知、打卡功能 | 9 |
| 12 | ai-coach | feat/ai-coach | 教练风格、每日问候 | 10,11 |
| 13 | pwa-support | feat/pwa-support | Service Worker、离线支持 | 3 |
| 14 | deployment-config | feat/deployment-config | K8s配置、生产部署准备 | 全部 |

## 并行执行建议

### 第一阶段（基础设施）
- Agent 1: `01-project-setup` - 必须首先完成
- 完成后可并行启动后续所有任务

### 第二阶段（核心开发）- 可并行
- Agent 1: `05-auth-system` + `06-user-profile`
- Agent 2: `07-equipment-management`
- Agent 3: `08-workout-plan` (依赖6,7，可稍后启动)
- Agent 4: `13-pwa-support` (独立任务)
- Agent 5: `10-voice-interaction` (独立任务)
- Agent 6: `11-notification-checkin` (独立任务)
- Agent 7: `12-ai-coach` (依赖10,11)
- Agent 8: `09-workout-execution` (依赖8)
- Agent 9: `14-deployment-config` (最后收尾)

## 任务文档位置

每个任务的详细文档位于 `docs/tasks/TASK_NAME.md`

| 任务 | 文档路径 |
|------|----------|
| project-setup | docs/tasks/project-setup.md |
| backend-framework | docs/tasks/backend-framework.md |
| frontend-framework | docs/tasks/frontend-framework.md |
| database-schema | docs/tasks/database-schema.md |
| auth-system | docs/tasks/auth-system.md |
| user-profile | docs/tasks/user-profile.md |
| equipment-management | docs/tasks/equipment-management.md |
| workout-plan | docs/tasks/workout-plan.md |
| workout-execution | docs/tasks/workout-execution.md |
| voice-interaction | docs/tasks/voice-interaction.md |
| notification-checkin | docs/tasks/notification-checkin.md |
| ai-coach | docs/tasks/ai-coach.md |
| pwa-support | docs/tasks/pwa-support.md |
| deployment-config | docs/tasks/deployment-config.md |

## 分支策略

每个任务对应一个独立的特性分支：
- 分支命名: `feat/TASK_NAME`
- 基础分支: `vk/2c85-`
- 合并目标: `vk/2c85-` 或 `main`

开发完成后，通过 Pull Request 合并到主分支。
