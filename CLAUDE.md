# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Bod (Project Code: IronMind)** is an AI-powered fitness coaching agent that uses voice-first interaction to guide users through workout sessions. The system combines computer vision (equipment recognition), voice interaction (ASR/TTS), and LangGraph-based agent orchestration to provide real-time coaching feedback.

### Core Concept
Users take photos of their gym equipment → AI builds an equipment inventory → Agent generates personalized workout plans → During workouts, users "push-to-talk" to log sets and receive real-time voice feedback.

## Architecture

The system follows a **Client-Server** architecture with a dedicated **Model Serving Layer**:

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Web App - Next.js/React)                        │
│  - Voice recording (Web Audio API)                         │
│  - Equipment photo upload                                   │
│  - PWA support (Service Worker + IndexedDB)                │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTPS
┌─────────────────────────────────────────────────────────────┐
│  Gateway & Business Layer (Python/FastAPI)                 │
│  - REST API endpoints                                       │
│  - JWT Authentication                                       │
│  - Task Queue (Celery/Redis)                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Agent Orchestrator (LangGraph)                            │
│  - State machine: ASR → Intent Classification → Logic      │
│  - Progressive overload calculation                        │
│  - Workout plan generation                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Model Serving Layer (Self-hosted / API)                   │
│  - LLM: Qwen-2.5-14B or DeepSeek-V3                        │
│  - VLM: Qwen-VL-Chat (equipment recognition)               │
│  - ASR: FunASR Paraformer (Chinese speech-to-text)         │
│  - TTS: ChatTTS/CosyVoice (text-to-speech)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Data Layer                                                │
│  - PostgreSQL (user data, workout logs)                    │
│  - Milvus (vector knowledge base for exercises)            │
│  - Redis (cache, session state)                            │
│  - MinIO/S3 (audio/image storage)                          │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Framework**: FastAPI (async Python)
- **Agent Orchestration**: LangGraph (stateful agents)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL with pgvector or Milvus for vectors

### AI Models (Self-hosted or API)
- **LLM**: Qwen-2.5-14B-Instruct (via vLLM/Ollama) or API
- **VLM**: Qwen-VL-Chat-Int4 (for equipment recognition)
- **ASR**: FunASR Paraformer (Chinese-optimized speech recognition)
- **TTS**: ChatTTS or CosyVoice (natural conversational voice)

### Frontend
- **Framework**: Next.js 14 (React) with TypeScript
- **UI Library**: shadcn/ui + Tailwind CSS
- **State Management**: Zustand
- **Audio**: Web Audio API + MediaRecorder
- **PWA**: Service Worker + IndexedDB for offline support
- **Key Features**: Voice recording (push-to-talk), photo upload, haptic feedback (mobile)

### API Configuration
The project uses an external LLM API. Configuration is stored in `.env`:
```
API_KEY=<api_key>
BASE_URL="https://llmapi.paratera.com/v1/chat/"
```

## Agent State Machine (LangGraph)

The core workout session follows this state flow:

```
[Audio Input] → ASR → Intent Classifier → {Router}
                                      ├─→ LOG_SET → DataProcessor → ResponseGen → TTS
                                      ├─→ COMPLAIN → Adjuster → TTS
                                      └─→ CHIT_CHAT → Chat → TTS
```

**Key State Schema**:
- `session_id`: Current workout session
- `chat_history`: Conversation history
- `current_exercise`: Active exercise
- `last_set_data`: {weight, reps, rpe}
- `plan_queue`: Remaining exercises

## Database Schema Highlights

### Core Entities
1. **exercises** - Exercise library (id, name, target_muscle, equipment_type, mechanics)
2. **user_equipment_inventory** - User's available equipment (JSONB tags from VLM scan)
3. **set_logs** - Individual set records with agent feedback
   - Includes: weight, reps, rpe, user_voice_input (ASR), agent_feedback (LLM)

### Key Relationships
User 1:N Plan 1:N Session 1:N SessionExercise 1:N SetLog

## Key API Endpoints

- **POST /api/v1/workout/voice-log**
  - Main interaction endpoint
  - Accepts: `audio_file`, `session_id`, `current_exercise_id`, `context`
  - Returns: transcription, extracted_data, agent_text_response, agent_audio_url, next_set_suggestion

## Development Commands

Currently this is a new project without implementation. When code is added, typical commands will include:

```bash
# Backend (FastAPI)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Docker Compose (local development)
docker-compose up -d

# Tests
pytest tests/

# Database migrations
alembic upgrade head
```

## Hardware Requirements for Self-hosted Models

If running models locally (not using API):
- **GPU**: NVIDIA RTX 3090/4090 (24GB VRAM minimum)
- **RAM**: 32GB
- **CPU**: 8 vCPU
- VRAM allocation:
  - Qwen-14B-Int4: ~9GB
  - Qwen-VL-Int4: ~10GB
  - ASR/TTS: ~3GB

## Language Notes

- PRD and DESIGN documents are in Chinese
- API keys and configuration use Chinese provider (Paratera)
- Models are optimized for Chinese language (FunASR, Qwen)
- UI/UX is designed for Chinese market (Web App with PWA support)

## Project Status

**Phase**: Greenfield - Planning stage only
- PRD and DESIGN documents completed
- No code implementation yet
- Ready for initial scaffold setup
