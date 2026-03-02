# FitAgent 系统设计文档 (SDD) v1.0

| 文档类型 | 系统架构与详细设计 (System Design Document) |
| --- | --- |
| **项目代号** | IronMind (铁意) |
| **技术核心** | LangGraph (Agent编排) + Local LLM/VLM + Web App (React/Next.js) |
| **作者** | Gemini |
| **更新日期** | 2026-01-04 |

## 1. 系统总体架构 (System Architecture)

系统采用经典的 **Client-Server** 架构，但在后端引入了独立的 **Model Serving Layer（模型服务层）** 以解耦业务逻辑与高算力推理任务。

### 1.1 架构图 (Mermaid)

```mermaid
graph TD
    User[用户 (Web 浏览器)]

    subgraph "Frontend Layer"
        UI[Web App 界面 (React/Next.js)]
        Recorder[音频录制模块 (Web Audio API/MediaRecorder)]
        Uploader[文件上传模块]
    end
    
    subgraph "Gateway & Business Layer (Python/FastAPI)"
        API_GW[API Gateway (Nginx)]
        Main_API[业务后端 (FastAPI)]
        Auth[鉴权模块 (JWT)]
        Task_Q[任务队列 (Celery/Redis)]
    end
    
    subgraph "Data Persistence Layer"
        PG[(PostgreSQL - 业务数据)]
        Redis[(Redis - 缓存/会话状态)]
        Milvus[(Milvus - 向量知识库)]
        OSS[对象存储 (MinIO/S3 - 图片/音频)]
    end
    
    subgraph "Model Serving Layer (GPU Cluster/Docker)"
        Orchestrator[Agent Orchestrator (LangGraph)]
        
        direction TB
        ASR_Svc[ASR 服务 (FunASR)]
        LLM_Svc[LLM 推理服务 (vLLM/Ollama)]
        VLM_Svc[VLM 视觉服务 (Qwen-VL)]
        TTS_Svc[TTS 服务 (ChatTTS/CosyVoice)]
    end

    User -->|HTTPS| API_GW
    API_GW --> Main_API
    Main_API -->|Read/Write| PG
    Main_API -->|Cache| Redis
    Main_API -->|Async Task| Task_Q
    
    Task_Q -->|Invoke| Orchestrator
    Orchestrator -->|Vector Search| Milvus
    Orchestrator -->|Speech-to-Text| ASR_Svc
    Orchestrator -->|Reasoning| LLM_Svc
    Orchestrator -->|Image Analysis| VLM_Svc
    Orchestrator -->|Text-to-Speech| TTS_Svc

```

---

## 2. 技术选型 (Tech Stack Strategy)

针对**开源**和**低延迟**需求，我们精选以下技术栈。考虑到你的科研背景，这套栈也非常适合作为毕设或开源项目展示。

### 2.1 模型层 (The "Brain")

* **LLM (推理核心):** **Qwen-2.5-14B-Instruct** 或 **DeepSeek-V3 (Distilled)**。
* *理由：* 中文能力极强，且 14B/32B 尺寸在消费级显卡（如 RTX 3090/4090）上配合量化可流畅运行。
* *推理引擎：* **vLLM** (追求高吞吐) 或 **Ollama** (部署极简)。


* **VLM (视觉感知):** **Qwen-VL-Chat-Int4**。
* *理由：* 对中文场景（健身房标语、器械说明）OCR 识别率高，且支持图文对话。


* **ASR (语音转文):** **FunASR (Paraformer模型)** - 阿里达摩院开源。
* *理由：* 专为中文优化，识别速度极快（RTF < 0.1），远优于 Whisper 的中文表现。


* **TTS (文转语音):** **ChatTTS** 或 **CosyVoice**。
* *理由：* ChatTTS 擅长生成带有语气词（"呃..."、"嗯..."）的口语化音频，非常适合模拟教练的自然对话。



### 2.2 后端与编排

* **Web 框架:** **FastAPI** (Python)。利用其原生 Async 特性处理并发 I/O。
* **Agent 框架:** **LangGraph**。
* *理由：* 我们需要有状态的 Agent（Stateful）。健身过程是一个典型的**状态机**（热身 -> 组1 -> 休息 -> 组2），LangGraph 比 LangChain Chain 更适合这种循环逻辑。


* **数据库:** **PostgreSQL** (pgvector 插件可选，或独立 Milvus)。

---

## 3. 数据库设计 (Schema Design)

这里只展示核心业务实体关系。

### 3.1 核心 E-R 逻辑

1. **User (用户)** 1:N **Plan (计划)**
2. **Plan** 1:N **Session (单次训练日)**
3. **Session** 1:N **SessionExercise (训练动作快照)**
4. **SessionExercise** 1:N **SetLog (组数据)**

### 3.2 关键表结构 (SQL Definition)

```sql
-- 1. 动作库 (静态数据)
CREATE TABLE exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    target_muscle VARCHAR(50), -- e.g., 'Chest', 'Quads'
    equipment_type VARCHAR(50), -- e.g., 'Barbell', 'Dumbbell', 'Machine'
    mechanics VARCHAR(50), -- 'Compound' or 'Isolation'
    video_url VARCHAR(255)
);

-- 2. 用户器械清单 (视觉识别结果)
CREATE TABLE user_equipment_inventory (
    user_id UUID REFERENCES users(id),
    equipment_tags JSONB, -- e.g., ["dumbbell", "bench", "pullup_bar"]
    scan_image_url VARCHAR(255),
    updated_at TIMESTAMP
);

-- 3. 训练日志 (核心动态数据)
CREATE TABLE set_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES workout_sessions(id),
    exercise_id INT REFERENCES exercises(id),
    set_order INT, -- 第几组
    weight DECIMAL(5,2), -- 重量 (kg)
    reps INT, -- 次数
    rpe INT, -- 自觉强度 (1-10)
    
    -- Agent 的分析与建议 (用于复盘)
    user_voice_input TEXT, -- ASR 结果: "80kg做不动了"
    agent_feedback TEXT, -- LLM 建议: "降重到75kg"
    
    created_at TIMESTAMP DEFAULT NOW()
);

```

---

## 4. API 接口设计 (Interface Design)

采用 RESTful 风格。对于语音交互，使用 **Multipart/form-data** 上传音频文件。

### 4.1 核心交互接口：语音日志上传

* **Endpoint:** `POST /api/v1/workout/voice-log`
* **Description:** 用户在小程序按住说话，松开后调用此接口。
* **Request Header:** `Authorization: Bearer <token>`
* **Request Body (Multipart):**
* `audio_file`: (Binary, .mp3/.wav/.pcm)
* `session_id`: (String) 当前训练的会话ID
* `current_exercise_id`: (Int, Optional) 当前正在做的动作ID
* `context`: (JSON) 上一组的数据（用于 LLM 上下文）


* **Response (JSON):**
```json
{
  "status": "success",
  "data": {
    "transcription": "这组80公斤做了8个，感觉RPE 8",
    "extracted_data": { "weight": 80, "reps": 8, "rpe": 8 },
    "agent_text_response": "很棒！RPE 8 说明还有保留。下一组保持重量，尝试把动作离心阶段放慢。",
    "agent_audio_url": "https://oss.fitagent.com/audio/response_xyz.mp3", // TTS生成的音频
    "next_set_suggestion": { "weight": 80, "reps": 8 }
  }
}

```



---

## 5. Agent 核心逻辑设计 (LangGraph Implementation)

这是系统的“大脑”。我们将构建一个 **StateGraph**。

### 5.1 状态定义 (State Schema)

```python
class AgentState(TypedDict):
    session_id: str
    chat_history: List[BaseMessage]
    current_exercise: str
    last_set_data: dict  # {weight: 100, reps: 5}
    user_input_audio: bytes
    user_input_text: str
    plan_queue: List[dict] # 剩余未做动作

```

### 5.2 节点流转逻辑 (Node Logic)

1. **Input Node:** 接收 API 请求，调用 `FunASR` 将音频转文本，存入 `user_input_text`。
2. **Intent Classifier (Router):** 使用 LLM 判断用户意图。
* *Intent: LOG_SET* (记录数据)  转入 **DataProcessor Node**。
* *Intent: COMPLAIN* (累了/痛了)  转入 **Adjuster Node**。
* *Intent: CHIT_CHAT* (闲聊)  转入 **Chat Node**。


3. **DataProcessor Node:**
* 提取实体 (Weight, Reps)。
* 对比历史 PR。
* 计算 `Progressive Overload` (渐进超负荷)。
* 输出：下一组建议。


4. **Response Node:**
* 整合数据，生成鼓励性/指导性文本。
* 调用 `ChatTTS` 生成音频。
* 返回结果给前端。



### 5.3 伪代码 (LangGraph)

```python
# 这是一个概念性的伪代码
from langgraph.graph import StateGraph, END

def speech_to_text(state):
    text = fun_asr_model.generate(state["user_input_audio"])
    return {"user_input_text": text}

def logic_router(state):
    # LLM 决策
    intent = llm.invoke(f"Analyze intent: {state['user_input_text']}")
    if intent == "LOG_DATA": return "processor"
    elif intent == "INJURY": return "adjuster"
    return "chatter"

def data_processor(state):
    # 提取数据并计算
    data = extract_entities(state["user_input_text"])
    next_set = calculate_next_set(state["last_set_data"], data)
    response_text = f"记下了，下一组建议 {next_set['weight']}kg。"
    return {"response_text": response_text}

workflow = StateGraph(AgentState)
workflow.add_node("asr", speech_to_text)
workflow.add_node("processor", data_processor)
# ... 添加其他节点

workflow.set_entry_point("asr")
workflow.add_conditional_edges("asr", logic_router)
workflow.add_edge("processor", END)

app = workflow.compile()

```

---

## 6. 部署与运维 (DevOps Strategy)

既然你熟悉 Docker 和 K8s，建议采用以下部署方案：

### 6.1 Docker Compose (单机开发环境)

```yaml
version: '3.8'
services:
  # 业务后端
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db, redis]

  # 数据库
  db:
    image: postgres:15
    volumes: [pg_data:/var/lib/postgresql/data]

  # 模型服务 (建议单独部署或按需开启，非常吃资源)
  model_serving:
    image: vllm/vllm-openai
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    command: "--model Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4"

```

### 6.2 资源预估 (Resource Requirements)

* **最低配置 (MVP):**
* CPU: 8 vCPU
* RAM: 32 GB
* GPU: **NVIDIA RTX 3090 (24GB VRAM)** 或 **4090**。
* *说明：* 24GB 显存刚好能塞下：Qwen-14B-Int4 (约9GB) + Qwen-VL-Int4 (约10GB) + FunASR/ChatTTS (约3GB)。如果显存吃紧，需要做模型卸载（Offloading）或使用更小的模型（如 Qwen-7B）。



---

## 7. 呈现方式建议 (Final UI/UX)

**Web 应用 (Web App)**

* **技术栈选择：**
  * **框架**: Next.js 14 (React) - 支持 SSR/SSG，SEO 友好
  * **UI 库**: shadcn/ui + Tailwind CSS - 现代化设计系统
  * **状态管理**: Zustand 或 React Context - 轻量级状态管理
  * **录音**: Web Audio API + MediaRecorder - 浏览器原生支持


* **录音交互优化：**
* 使用 `MediaRecorder API` 进行音频录制。
* UI 设计：屏幕底部放置一个**巨大的圆形按钮**，上面写着"按住说话"（PC端支持鼠标长按，移动端支持触摸长按）。
* **触觉反馈 (Haptic)**: 移动端使用 `navigator.vibrate()` API，按下时手机短震，松开时双震，模拟对讲机手感。


* **离线兼容：**
* 使用 Service Worker + IndexedDB 实现离线缓存。
* 如果网络极差，录音先保存在本地 IndexedDB，显示"待同步"图标。等有网时自动上传。
* 支持 PWA (Progressive Web App)，可添加到主屏幕，接近原生体验。


* **响应式设计：**
* 移动端优先 (Mobile-first) 设计策略。
* 支持桌面端和移动端自适应布局。
* 桌面端提供侧边栏导航，移动端使用底部标签栏。

---
