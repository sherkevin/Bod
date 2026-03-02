# Bod MVP (Minimum Viable Product)

这是一个基于语音交互的健身记录应用原型 (MVP)。

## 🚀 核心功能

1.  **语音录入**: 点击“按住说话”，记录你的训练内容。
2.  **本地转写 (Local ASR)**: 使用 `faster-whisper` (tiny model) 在本地无需联网即可将语音转为文本。
3.  **智能分析 (LLM)**: 使用 Cloud LLM (DeepSeek) 分析语义，识别动作、组数、重量，并给出鼓励反馈。
4.  **持久化存储**: 训练记录自动保存到 SQLite 数据库。

## 🛠️ 技术栈

*   **后端**: Python (FastAPI, SQLAlchemy, Alembic)
*   **前端**: HTML/JS (Native Fetch API, MediaRecorder)
*   **AI**:
    *   ASR: `faster-whisper` (运行于 CPU, 只需约 200MB 内存)
    *   LLM: OpenAI SDK (兼容 DeepSeek/Moonshot 等 API)
*   **DB**: SQLite (Dev 模式) / PostgreSQL (Prod 模式)

## 📦 快速启动 (本地开发)

### 1. 准备环境

确保安装了 Python 3.8+。

```bash
# 创建虚拟环境
python -m venv venv

# Windows 激活
.\venv\Scripts\Activate.ps1

# 安装依赖 (核心+AI)
pip install -r backend/requirements.txt
```

### 2. 配置 AI 密钥

在 `backend/ai_service.py` 中已预置了默认 Key (如果您在对话中提供了)。
如果需要修改，设置环境变量：

```powershell
$env:AI_API_KEY="your-key"
$env:AI_BASE_URL="https://llmapi.paratera.com/v1"
$env:AI_MODEL_NAME="DeepSeek-V3.1"
```

### 3. 初始化数据库

```bash
# 进入 backend 目录执行
cd backend
alembic upgrade head
cd ..
```

### 4. 启动服务

```bash
# 在根目录下
python -m uvicorn backend.main:app --port 8000 --reload
```
*(注意：首次启动当你上传语音时，会自动下载 ASR 模型约 70MB，请保持耐心等待)*

### 5. 访问前端

打开浏览器访问: [http://localhost:8000](http://localhost:8000)

## 📂 目录结构

```
Bod/
├── backend/
│   ├── main.py        # 核心 API 入口
│   ├── ai_service.py  # ASR 与 LLM 调用逻辑
│   ├── models.py      # 数据库模型
│   ├── database.py    # DB 连接配置
│   ├── alembic/       # 数据库迁移脚本
│   └── uploads/       # 存放上传的录音文件
├── frontend/
│   ├── index.html     # Web UI
│   ├── app.js         # 录音与交互逻辑
│   └── styles.css
└── docker-compose.yml # 容器化配置 (暂未完全启用 GPU 支持)
```
