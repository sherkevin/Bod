# Task: Backend Framework

## Overview

Set up the FastAPI backend framework with proper directory structure, middleware, error handling, and common utilities.

## Dependencies

- Requires `project-setup` to be completed

## Deliverables

### 1. Core Application Structure

```
backend/app/
├── main.py                 # FastAPI app initialization
├── config.py              # Configuration management
├── dependencies.py        # Dependency injection
└── __init__.py

core/
├── __init__.py
├── security.py           # JWT, password hashing
├── auth.py               # Auth dependencies
├── database.py           # DB session management
└── exceptions.py         # Custom exceptions

api/
├── __init__.py
├── deps.py               # Common dependencies
└── v1/                   # API v1 routes
    ├── __init__.py
    ├── router.py         # Main v1 router
    └── health.py         # Health check endpoint

models/
├── __init__.py
├── base.py               # Base model class
├── user.py               # User model (from database-schema task)
└── ...

schemas/
├── __init__.py
├── common.py             # Common schemas (pagination, etc)
└── ...

services/
├── __init__.py
├── llm.py                # LLM service wrapper
├── vlm.py                # VLM service wrapper
├── asr.py                # ASR service wrapper
└── tts.py                # TTS service wrapper
```

### 2. Configuration (`app/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Bod Fitness Assistant"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # AI Services
    VLLM_URL: str = "http://vllm:8000"
    ASR_URL: str = "http://asr:8002"
    TTS_URL: str = "http://tts:8003"

    # Storage
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "bod"

    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. Database Session (`core/database.py`)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 4. Security (`core/security.py`)

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

### 5. Exception Handlers

Custom exceptions for:
- `NotFoundException` - 404
- `UnauthorizedException` - 401
- `ForbiddenException` - 403
- `BadRequestException` - 400
- `InternalServerException` - 500

### 6. Middleware

- CORS middleware configuration
- Request ID middleware
- Logging middleware
- Timing middleware

### 7. Health Check Endpoint

`GET /api/v1/health` returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "0.1.0"
}
```

## Technical Requirements

- FastAPI 0.100+
- SQLAlchemy 2.0 with async support
- Pydantic v2 for validation
- Proper type hints throughout
- OpenAPI documentation

## Acceptance Criteria

- [ ] `docker-compose up backend` starts successfully
- [ ] API docs accessible at http://localhost:8000/docs
- [ ] Health check endpoint returns proper status
- [ ] CORS configured correctly for frontend
- [ ] Database connection pooling configured
- [ ] Environment variables properly loaded
- [ ] All middleware functioning

## API Endpoints to Create

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |

## Notes

- Follow FastAPI best practices
- Use dependency injection for database sessions
- Implement proper error response schemas
- Add request validation examples in docs
