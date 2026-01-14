# Task: Project Setup

## Overview

Initialize the Bod project with proper directory structure, development environment configuration, and CI/CD setup.

## Dependencies

None - This is the foundational task that must be completed first.

## Deliverables

### 1. Project Structure

```
bod/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Config, security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── main.py         # FastAPI app
│   ├── tests/
│   ├── alembic/            # Database migrations
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # App router pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities
│   │   ├── stores/        # Zustand stores
│   │   └── styles/        # Global styles
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── deployment/             # K8s configs
│   ├── base/
│   └── overlays/
│
├── docker/
│   └── docker-compose.yml  # Local development
│
├── .github/
│   └── workflows/          # CI/CD
│
├── docs/                   # Documentation
└── README.md
```

### 2. Configuration Files

#### Root Level
- `.gitignore` - Comprehensive ignore patterns
- `docker-compose.yml` - Local development setup
- `Makefile` - Common commands
- `.editorconfig` - Editor settings

#### Backend (`backend/`)
- `pyproject.toml` - Python dependencies (poetry)
- `.env.example` - Environment variables template
- `Dockerfile` - Backend container
- `alembic.ini` - Database migration config

#### Frontend (`frontend/`)
- `package.json` - Node dependencies
- `next.config.js` - Next.js config
- `tailwind.config.ts` - Tailwind CSS config
- `tsconfig.json` - TypeScript config
- `components.json` - shadcn/ui config
- `Dockerfile` - Frontend container

### 3. Docker Compose Setup

Services to include:
- `frontend` - Next.js dev server (port 3000)
- `backend` - FastAPI with hot-reload (port 8000)
- `postgres` - PostgreSQL 15 (port 5432)
- `redis` - Redis 7 (port 6379)
- `milvus` - Vector database (port 19530)
- `minio` - Object storage (port 9000)
- `vllm` - LLM serving (port 8001)
- `asr` - FunASR service (port 8002)
- `tts` - TTS service (port 8003)

### 4. CI/CD Pipeline

`.github/workflows/ci.yml`:
- Lint check (ESLint, Ruff)
- Type check (tsc, mypy)
- Unit tests (pytest, vitest)
- Build verification

### 5. Development Documentation

- `README.md` - Project overview, quick start
- `docs/DEVELOPMENT.md` - Development guide
- `docs/CONTRIBUTING.md` - Contribution guidelines

## Technical Requirements

### Backend Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.100.0"
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"
redis = "^5.0.0"
celery = "^5.3.0"
langchain = "^0.1.0"
langgraph = "^0.0.30"
httpx = "^0.25.0"
python-multipart = "^0.0.6"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
```

### Frontend Dependencies
```json
{
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "@radix-ui/react-*": "latest",
    "zustand": "^4.4.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0"
  }
}
```

## Acceptance Criteria

- [ ] `docker-compose up` starts all services successfully
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend API docs at http://localhost:8000/docs
- [ ] Database migrations can run
- [ ] CI/CD pipeline passes on empty project
- [ ] README includes setup instructions

## Notes

- Use Poetry for Python dependency management
- Use pnpm for Node dependency management
- Configure hot-reload for both frontend and backend
- Set up proper volume mounts for local development
