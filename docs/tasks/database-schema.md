# Task: Database Schema

## Overview

Design and implement the complete database schema for Bod using SQLAlchemy and Alembic migrations.

## Dependencies

- Requires `project-setup` to be completed

## Deliverables

### 1. Database Models

#### `models/base.py` - Base Model Class
```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

#### `models/user.py` - User Model
```python
import uuid
from sqlalchemy import ENUM, Integer, String, Text, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nickname: Mapped[str] = mapped_column(String(50))
    gender: Mapped[str] = mapped_column(ENUM("male", "female", name="gender_enum"))
    birth_year: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)  # cm
    weight_history: Mapped[dict] = mapped_column(JSONB, default=list)
    fitness_level: Mapped[str] = mapped_column(
        ENUM("beginner", "intermediate", "advanced", name="fitness_level_enum")
    )
    primary_goal: Mapped[str] = mapped_column(
        ENUM("fat_loss", "muscle_gain", "tone", "strength", "health", name="goal_enum")
    )
    workout_frequency: Mapped[int] = mapped_column(Integer)  # sessions per week
    workout_duration: Mapped[int] = mapped_column(Integer)  # minutes
    injuries: Mapped[str | None] = mapped_column(Text, nullable=True)
    gym_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
```

#### `models/equipment.py` - Equipment Model
```python
import uuid
from sqlalchemy import Boolean, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class UserEquipment(Base, TimestampMixin):
    __tablename__ = "user_equipment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(
        ENUM("free_weight", "machine", "cardio", "functional", name="equipment_category_enum")
    )
    weight_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
```

#### `models/workout.py` - Workout Models
```python
import uuid
from sqlalchemy import Date, Enum, Integer, String, Text, JSONB, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date

from .base import Base, TimestampMixin


class WorkoutPlan(Base, TimestampMixin):
    __tablename__ = "workout_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    weeks_count: Mapped[int] = mapped_column(Integer)
    goals: Mapped[dict] = mapped_column(JSONB, default=dict)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(
        ENUM("draft", "active", "completed", "paused", name="plan_status_enum"),
        default="draft"
    )


class WorkoutSession(Base, TimestampMixin):
    __tablename__ = "workout_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("workout_plans.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    scheduled_date: Mapped[date] = mapped_column(Date)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    theme: Mapped[str] = mapped_column(String(100))
    exercises_plan: Mapped[dict] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(
        ENUM("scheduled", "in_progress", "completed", "skipped", "rest_day", name="session_status_enum"),
        default="scheduled"
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SessionExercise(Base, TimestampMixin):
    __tablename__ = "session_exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("workout_sessions.id"))
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id"))
    sets_planned: Mapped[int] = mapped_column(Integer)
    reps_planned: Mapped[str] = mapped_column(String(20))  # e.g., "8-12"
    weight_planned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_seconds: Mapped[int] = mapped_column(Integer, default=90)
    order: Mapped[int] = mapped_column(Integer)


class SetLog(Base, TimestampMixin):
    __tablename__ = "set_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("workout_sessions.id"))
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id"))
    set_number: Mapped[int] = mapped_column(Integer)
    weight: Mapped[float] = mapped_column(Numeric(10, 2))
    reps: Mapped[int] = mapped_column(Integer)
    rpe: Mapped[int] = mapped_column(Integer)  # 1-10
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)


class Exercise(Base, TimestampMixin):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(
        ENUM("compound", "isolation", "cardio", "stretch", name="exercise_category_enum")
    )
    target_muscles: Mapped[list] = mapped_column(JSONB, default=list)
    equipment_needed: Mapped[list] = mapped_column(JSONB, default=list)
    difficulty: Mapped[str] = mapped_column(
        ENUM("beginner", "intermediate", "advanced", name="exercise_difficulty_enum")
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[list] = mapped_column(JSONB, default=list)
```

#### `models/checkin.py` - Check-in Model
```python
import uuid
from sqlalchemy import Date, Integer, String, Numeric, ForeignKey, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date

from .base import Base, TimestampMixin


class CheckIn(Base, TimestampMixin):
    __tablename__ = "check_ins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workout_sessions.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    achievements_unlocked: Mapped[list] = mapped_column(JSONB, default=list)
    mood: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

#### `models/message.py` - AI Message Model
```python
import uuid
from sqlalchemy import Boolean, String, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class AIMessage(Base, TimestampMixin):
    __tablename__ = "ai_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(
        Enum("daily_greeting", "workout_feedback", "system_notification", "progress_check", name="message_type_enum")
    )
    content: Mapped[str] = mapped_column(Text)
    voice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    coach_style: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

### 2. Alembic Migrations

Create migrations for:
1. Initial schema creation
2. Users table
3. Exercises reference data
4. Equipment, Plans, Sessions
5. Set logs, Check-ins
6. AI Messages

### 3. Seed Data

#### `alembic/seeds/exercises.py`

Populate `exercises` table with common exercises:
- Compound movements: squat, deadlift, bench press, overhead press, pull-up, row
- Isolation movements: bicep curl, tricep extension, lateral raise
- Cardio: running, cycling, jumping jacks
- Stretch: various stretches

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │──────<│ WorkoutPlan │──────<│   Session   │
│  (users)    │  1:N  │(workout_    │  1:N  │(workout_    │
│             │       │   plans)    │       │  sessions)  │
└─────────────┘       └─────────────┘       └─────────────┘
       │                                           │
       │                                           │ 1:N
       │                                           ▼
       │                               ┌─────────────┐       ┌─────────────┐
       │ 1:N                           │SessionExercise│       │   SetLog    │
       ▼                               │(session_     │ 1:N   │ (set_logs)  │
┌─────────────┐                       │  exercises)  │──────<│             │
│UserEquipment│                       └─────────────┘       └─────────────┘
│(user_       │
│ equipment)  │
└─────────────┘

┌─────────────┐       ┌─────────────┐
│  CheckIn    │       │  AIMessage  │
│(check_ins)  │       │(ai_messages)│
└─────────────┘       └─────────────┘
```

## Technical Requirements

- SQLAlchemy 2.0 with declarative base
- Alembic for migrations
- UUID primary keys
- Timestamp mixin for created_at/updated_at
- Proper foreign key relationships
- Indexes on frequently queried columns

## Acceptance Criteria

- [ ] All models defined with proper types
- [ ] Alembic migrations created and tested
- [ ] `alembic upgrade head` runs successfully
- [ ] Reference exercises data seeded
- [ ] Foreign key constraints working
- [ ] Indexes created on:
  - users.email
  - user_equipment.user_id
  - workout_plans.user_id
  - workout_sessions.user_id, scheduled_date
  - set_logs.session_id

## Notes

- Use PostgreSQL-specific JSONB type for flexible data
- Add cascade delete where appropriate
- Consider adding soft delete mixin
- Add database-level constraints for enums
