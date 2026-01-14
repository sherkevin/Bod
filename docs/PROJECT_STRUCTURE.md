# Bod 项目文件目录结构规范

本文档定义了 Bod 项目的全局文件目录结构，所有开发 Agent 必须严格遵守此规范。

---

## 项目根目录结构

```
bod/
├── README.md                 # 项目说明文档
├── .env                      # 环境变量（不提交）
├── .env.example              # 环境变量示例
├── .gitignore                # Git 忽略规则
├── docker-compose.yml        # 开发环境 Docker 编排
├── docker-compose.prod.yml   # 生产环境 Docker 编排
├── Makefile                  # 常用命令快捷方式
│
├── docs/                     # 项目文档
│   ├── PRD.md               # 产品需求文档
│   ├── TASK_BREAKDOWN.md    # 任务拆分总览
│   ├── PROJECT_STRUCTURE.md # 本文档 - 目录结构规范
│   └── tasks/               # 各任务详细文档
│       ├── project-setup.md
│       ├── backend-framework.md
│       ├── frontend-framework.md
│       ├── database-schema.md
│       ├── auth-system.md
│       ├── user-profile.md
│       ├── equipment-management.md
│       ├── workout-plan.md
│       ├── workout-execution.md
│       ├── voice-interaction.md
│       ├── notification-checkin.md
│       ├── ai-coach.md
│       ├── pwa-support.md
│       └── deployment-config.md
│
├── backend/                 # 后端服务（Python/FastAPI）
│   ├── app/                 # 应用主目录
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI 应用入口
│   │   ├── config.py        # 配置管理
│   │   │
│   │   ├── api/             # API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── deps.py      # 依赖注入
│   │   │   └── v1/          # API v1 版本
│   │   │       ├── __init__.py
│   │   │       ├── auth.py        # 认证相关接口
│   │   │       ├── users.py       # 用户相关接口
│   │   │       ├── equipment.py   # 器材相关接口
│   │   │       ├── plans.py       # 计划相关接口
│   │   │       ├── workout.py     # 训练执行接口
│   │   │       ├── voice.py       # 语音交互接口
│   │   │       ├── notifications.py # 通知相关接口
│   │   │       ├── coach.py       # AI 教练接口
│   │   │       └── checkin.py     # 打卡相关接口
│   │   │
│   │   ├── core/            # 核心功能模块
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # 配置类
│   │   │   ├── security.py      # 安全相关（JWT, 密码哈希）
│   │   │   ├── database.py      # 数据库连接
│   │   │   └── auth.py          # 认证逻辑
│   │   │
│   │   ├── models/          # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Base 模型类
│   │   │   ├── user.py          # 用户模型
│   │   │   ├── equipment.py     # 器材模型
│   │   │   ├── workout.py       # 训练相关模型（Plan, Session, SetLog）
│   │   │   ├── checkin.py       # 打卡模型
│   │   │   ├── message.py       # 消息模型
│   │   │   └── notification.py  # 推送订阅模型
│   │   │
│   │   ├── schemas/         # Pydantic 模型（请求/响应）
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── equipment.py
│   │   │   ├── plan.py
│   │   │   ├── workout.py
│   │   │   ├── voice.py
│   │   │   ├── notification.py
│   │   │   ├── checkin.py
│   │   │   └── coach.py
│   │   │
│   │   ├── services/        # 业务逻辑服务层
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   ├── equipment_service.py
│   │   │   ├── plan_service.py
│   │   │   ├── workout_service.py
│   │   │   ├── checkin_service.py
│   │   │   ├── notification_service.py
│   │   │   │
│   │   │   ├── llm/         # AI 服务子目录
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py       # LLM 服务基类
│   │   │   │   ├── llm_service.py   # LLM 服务
│   │   │   │   ├── vlm_service.py  # VLM 服务
│   │   │   │   ├── asr_service.py  # ASR 服务
│   │   │   │   ├── tts_service.py  # TTS 服务
│   │   │   │   └── coach_service.py # AI 教练服务
│   │   │   │
│   │   │   └── scheduler/   # 定时任务子目录
│   │   │       ├── __init__.py
│   │   │       └── scheduler_service.py
│   │   │
│   │   ├── tasks/           # Celery 异步任务
│   │   │   ├── __init__.py
│   │   │   └── celery_app.py
│   │   │
│   │   ├── db/              # 数据库相关
│   │   │   ├── __init__.py
│   │   │   ├── session.py        # 数据库会话管理
│   │   │   └── seed_data/        # 种子数据
│   │   │       ├── __init__.py
│   │   │       └── exercises.py  # 动作库数据
│   │   │
│   │   ├── middleware/      # 中间件
│   │   │   ├── __init__.py
│   │   │   ├── cors.py
│   │   │   └── error_handler.py
│   │   │
│   │   ├── utils/           # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── datetime.py
│   │   │   ├── validators.py
│   │   │   └── helpers.py
│   │   │
│   │   └── websocket/       # WebSocket 路由
│   │       ├── __init__.py
│   │       └── voice.py     # 语音通话 WebSocket
│   │
│   ├── alembic/            # 数据库迁移
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/       # 迁移版本文件
│   │
│   ├── tests/              # 测试文件
│   │   ├── __init__.py
│   │   ├── conftest.py     # pytest 配置
│   │   ├── unit/           # 单元测试
│   │   │   ├── test_models.py
│   │   │   ├── test_services.py
│   │   │   └── test_api.py
│   │   └── integration/    # 集成测试
│   │       └── test_workout_flow.py
│   │
│   ├── scripts/            # 脚本文件
│   │   ├── init_db.py      # 初始化数据库
│   │   └── seed_exercises.py
│   │
│   ├── Dockerfile          # 后端 Docker 镜像
│   ├── Dockerfile.dev      # 开发环境 Dockerfile
│   ├── requirements.txt    # Python 依赖
│   ├── requirements.dev.txt # 开发依赖
│   └── pyproject.toml      # 项目配置
│
├── frontend/               # 前端应用（Next.js）
│   ├── app/                # App Router (Next.js 13+)
│   │   ├── (auth)/         # 认证相关页面组
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── register/
│   │   │   │   └── page.tsx
│   │   │   └── layout.tsx
│   │   │
│   │   ├── (main)/         # 主应用页面组（需要认证）
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # 首页（仪表盘）
│   │   │   ├── plan/               # 训练计划页面
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx    # 计划详情
│   │   │   ├── workout/            # 训练执行页面
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx    # 训练详情
│   │   │   ├── equipment/          # 器材管理页面
│   │   │   │   └── page.tsx
│   │   │   ├── progress/           # 进度统计页面
│   │   │   │   └── page.tsx
│   │   │   ├── messages/           # AI 教练消息页面
│   │   │   │   └── page.tsx
│   │   │   └── profile/            # 个人设置页面
│   │   │       ├── page.tsx
│   │   │       └── settings/
│   │   │           └── page.tsx
│   │   │
│   │   ├── api/             # API Routes（可选，如果需要）
│   │   │   └── health/
│   │   │       └── route.ts
│   │   │
│   │   ├── layout.tsx       # 根布局
│   │   ├── page.tsx         # 根页面（重定向）
│   │   ├── globals.css      # 全局样式
│   │   └── error.tsx        # 错误页面
│   │
│   ├── components/          # React 组件
│   │   ├── ui/              # shadcn/ui 基础组件
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ...          # 其他 UI 组件
│   │   │
│   │   ├── layout/          # 布局组件
│   │   │   ├── header.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── footer.tsx
│   │   │   └── navigation.tsx
│   │   │
│   │   ├── workout/         # 训练相关组件
│   │   │   ├── workout-card.tsx
│   │   │   ├── set-logger.tsx
│   │   │   ├── rest-timer.tsx
│   │   │   └── exercise-display.tsx
│   │   │
│   │   ├── voice/           # 语音相关组件
│   │   │   ├── voice-button.tsx
│   │   │   ├── voice-call-modal.tsx
│   │   │   └── waveform.tsx
│   │   │
│   │   ├── coach/           # AI 教练相关组件
│   │   │   ├── coach-chat.tsx
│   │   │   ├── coach-style-selector.tsx
│   │   │   └── daily-greeting.tsx
│   │   │
│   │   ├── equipment/       # 器材相关组件
│   │   │   ├── equipment-list.tsx
│   │   │   ├── equipment-card.tsx
│   │   │   └── photo-upload.tsx
│   │   │
│   │   ├── plan/            # 计划相关组件
│   │   │   ├── plan-week-view.tsx
│   │   │   ├── plan-calendar.tsx
│   │   │   └── exercise-item.tsx
│   │   │
│   │   ├── checkin/         # 打卡相关组件
│   │   │   ├── checkin-modal.tsx
│   │   │   ├── streak-display.tsx
│   │   │   └── achievement-badge.tsx
│   │   │
│   │   └── common/          # 通用组件
│   │       ├── loading.tsx
│   │       ├── error-boundary.tsx
│   │       ├── empty-state.tsx
│   │       └── offline-indicator.tsx
│   │
│   ├── lib/                 # 工具库
│   │   ├── api/             # API 客户端
│   │   │   ├── client.ts    # 基础 API 客户端
│   │   │   ├── auth.ts      # 认证 API
│   │   │   ├── user.ts      # 用户 API
│   │   │   ├── equipment.ts # 器材 API
│   │   │   ├── plan.ts      # 计划 API
│   │   │   ├── workout.ts   # 训练 API
│   │   │   ├── voice.ts     # 语音 API
│   │   │   ├── checkin.ts   # 打卡 API
│   │   │   └── coach.ts     # 教练 API
│   │   │
│   │   ├── hooks/           # 自定义 Hooks
│   │   │   ├── use-auth.ts
│   │   │   ├── use-online-status.ts
│   │   │   ├── use-workout.ts
│   │   │   └── use-local-storage.ts
│   │   │
│   │   ├── stores/          # 状态管理 (Zustand)
│   │   │   ├── auth.ts
│   │   │   ├── workout.ts
│   │   │   ├── user.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── utils/           # 工具函数
│   │   │   ├── date.ts
│   │   │   ├── format.ts
│   │   │   ├── validation.ts
│   │   │   └── constants.ts
│   │   │
│   │   ├── types/           # TypeScript 类型定义
│   │   │   ├── index.ts
│   │   │   ├── api.ts
│   │   │   ├── models.ts
│   │   │   └── enums.ts
│   │   │
│   │   ├── notifications/   # 通知相关
│   │   │   ├── push.ts
│   │   │   └── service-worker.ts
│   │   │
│   │   └── offline-storage.ts # 离线存储
│   │
│   ├── public/              # 静态资源
│   │   ├── icons/           # 图标
│   │   │   ├── icon-72.png
│   │   │   ├── icon-96.png
│   │   │   ├── icon-128.png
│   │   │   ├── icon-144.png
│   │   │   ├── icon-152.png
│   │   │   ├── icon-192.png
│   │   │   ├── icon-384.png
│   │   │   ├── icon-512.png
│   │   │   └── badge-72.png
│   │   │
│   │   ├── images/          # 图片资源
│   │   ├── manifest.json    # PWA 清单
│   │   ├── sw.js            # Service Worker
│   │   ├── offline.html     # 离线页面
│   │   └── robots.txt
│   │
│   ├── styles/              # 样式文件
│   │   └── globals.css      # Tailwind + 自定义样式
│   │
│   ├── tests/               # 前端测试
│   │   ├── unit/
│   │   ├── integration/
│   │   └── setup.ts
│   │
│   ├── .eslintrc.json       # ESLint 配置
│   ├── .prettierrc          # Prettier 配置
│   ├── next.config.js       # Next.js 配置
│   ├── tailwind.config.ts   # Tailwind 配置
│   ├── tsconfig.json        # TypeScript 配置
│   ├── postcss.config.js    # PostCSS 配置
│   ├── package.json         # npm 依赖
│   └── Dockerfile           # 前端 Docker 镜像
│
├── k8s/                     # Kubernetes 部署配置
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── ingress.yaml
│   │
│   ├── backend/             # 后端部署
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   │
│   ├── frontend/            # 前端部署
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   │
│   ├── postgres/            # 数据库部署
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   │
│   ├── redis/               # Redis 部署
│   │   └── service.yaml
│   │
│   ├── minio/               # 对象存储部署
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   │
│   └── vllm/                # LLM 服务部署
│       ├── deployment.yaml
│       ├── service.yaml
│       └── pvc.yaml
│
├── monitoring/              # 监控配置
│   ├── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   └── alertmanager/
│
├── scripts/                 # 项目级脚本
│   ├── setup.sh             # 初始化脚本
│   ├── dev.sh               # 启动开发环境
│   ├── build.sh             # 构建脚本
│   └── deploy.sh            # 部署脚本
│
└── .github/                 # GitHub 配置
    └── workflows/           # GitHub Actions
        ├── ci.yml           # 持续集成
        ├── deploy.yml       # 部署流程
        └── test.yml         # 测试流程
```

---

## 命名规范

### 文件命名

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 模块 | 小写下划线 | `user_service.py`, `workout_plan.py` |
| Python 类 | 大驼峰 | `UserService`, `WorkoutPlan` |
| React 组件 | 大驼峰 | `VoiceButton.tsx`, `WorkoutCard.tsx` |
| React Hooks | 小写驼峰，use 前缀 | `useAuth.ts`, `useWorkout.ts` |
| 工具函数 | 小写驼峰 | `formatDate.ts`, `validateInput.ts` |
| 类型定义 | 大驼峰，类型后缀 | `UserTypes.ts`, `ApiModels.ts` |
| 配置文件 | 小写点分隔 | `tailwind.config.ts`, `.eslintrc.json` |

### 目录命名

- 全部使用小写
- 多词用连字符 `-` 连接
- 例外：`__pycache__`, `node_modules`

### 组件组织

```
components/
├── ui/              # shadcn/ui 基础组件（不修改）
├── layout/          # 布局组件
├── [feature]/       # 功能相关组件组
│   ├── [feature]-card.tsx
│   ├── [feature]-list.tsx
│   └── [feature]-form.tsx
└── common/          # 通用组件
```

---

## 导入路径规范

### 后端（Python）

```python
# 绝对导入（推荐）
from app.models.user import User
from app.services.user_service import UserService
from app.api.v1.users import router as users_router

# 相对导入（仅限同目录内）
from .base import Base
from ..deps import get_current_user
```

### 前端（TypeScript）

```typescript
// 绝对导入（使用 @ 别名）
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/hooks/use-auth';
import { workoutApi } from '@/lib/api/workout';

// 相对导入（仅限同目录内）
import { WorkoutsList } from './workouts-list';
import { styles } from './styles.module.css';
```

---

## 环境变量规范

### 后端环境变量（`.env`）

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0

# API
SECRET_KEY=your-secret-key
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000

# AI 服务
VLLM_URL=http://localhost:8001
ASR_URL=http://localhost:8002
TTS_URL=http://localhost:8003

# 存储
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# 推送通知
VAPID_PUBLIC_KEY=your-public-key
VAPID_PRIVATE_KEY=your-private-key
```

### 前端环境变量（`.env.local`）

```bash
# API 端点
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# 功能开关
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_SENTRY=false
```

---

## Git 提交规范

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `refactor` | 代码重构 |
| `style` | 样式修改 |
| `docs` | 文档更新 |
| `test` | 测试相关 |
| `chore` | 构建/工具相关 |

### 示例

```
feat(workout): 添加语音记录训练日志功能

- 实现按住说话按钮组件
- 集成 ASR 服务进行语音识别
- 添加语音播放功能

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## API 版本规范

所有 API 路由必须包含版本前缀：

```
/api/v1/{resource}
/api/v2/{resource}  # 未来版本
```

---

## 数据库迁移规范

迁移文件命名：`{YYYYMMDD}_{description}.py`

```bash
alembic/versions/
├── 20250114_01_create_users_table.py
├── 20250114_02_create_equipment_table.py
├── 20250114_03_create_workout_tables.py
└── 20250115_01_add_user_preferences.py
```

---

## 文档规范

### 代码注释

```python
def create_workout_plan(user_id: str, data: PlanCreate) -> WorkoutPlan:
    """
    创建用户训练计划

    Args:
        user_id: 用户ID
        data: 计划创建请求数据

    Returns:
        创建的训练计划对象

    Raises:
        NotFoundException: 用户不存在
        ValidationError: 数据验证失败
    """
    pass
```

### README 结构

每个子模块（如果有独立 README）应包含：

1. 模块说明
2. 功能列表
3. 使用示例
4. API 文档链接
5. 开发指南

---

## 依赖管理规范

### 后端依赖分组

```txt
# requirements.txt
fastapi==0.104.0
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.13.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
httpx==0.25.2
redis==5.0.1
celery==5.3.4
langchain==0.1.0
```

### 前端依赖分组

```json
{
  "dependencies": {
    "next": "14.0.4",
    "react": "^18.2.0",
    "zustand": "^4.4.7",
    "@tanstack/react-query": "^5.14.0"
  },
  "devDependencies": {
    "typescript": "^5.3.3",
    "eslint": "^8.56.0",
    "prettier": "^3.1.1",
    "tailwindcss": "^3.4.0"
  }
}
```

---

## 开发工作流

1. **创建功能分支**：从 `main` 或 `vk/2c85-` 创建
   - 命名：`feat/feature-name`, `fix/bug-name`

2. **开发**：按照本规范组织文件

3. **测试**：确保测试通过

4. **提交**：使用规范的提交消息

5. **创建 PR**：填写 PR 模板

6. **代码审查**：确保符合规范

7. **合并**：合并到主分支

---

**版本**: v1.0
**最后更新**: 2025-01-14
**状态**: 生效中
