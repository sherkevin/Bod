# Task: User Profile Management

## Overview

Implement user profile CRUD operations, including personal information, fitness goals, body data tracking, and preferences management.

## Dependencies

- Requires `auth-system` to be completed

## Deliverables

### 1. Backend Implementation

#### `models/user_profile.py` (Extensions)
```python
from sqlalchemy import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# Add to User model
class User(Base, TimestampMixin):
    # ... existing fields

    # Extended profile fields
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")

    # Preferences (JSONB)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {
    #   "coach_style": "encouraging",
    #   "notification_enabled": true,
    #   "daily_greeting_time": "20:00",
    #   "units": "metric"  # or "imperial"
    # }

    # Training history
    total_workouts: Mapped[int] = mapped_column(Integer, default=0)
    last_workout_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

#### `services/user_service.py`
```python
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserProfileUpdate, WeightRecord

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_profile(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        return user

    def update_profile(self, user_id: str, data: UserProfileUpdate) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def add_weight_record(self, user_id: str, weight: float) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        record = {
            "date": date.today().isoformat(),
            "weight": weight
        }
        user.weight_history.append(record)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_goals(self, user_id: str, goals: dict) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        user.primary_goal = goals.get("primary_goal", user.primary_goal)
        user.workout_frequency = goals.get("workout_frequency", user.workout_frequency)
        user.workout_duration = goals.get("workout_duration", user.workout_duration)
        user.fitness_level = goals.get("fitness_level", user.fitness_level)

        self.db.commit()
        self.db.refresh(user)
        return user

    def update_preferences(self, user_id: str, preferences: dict) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        user.preferences = {**user.preferences, **preferences}
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_weight_history(self, user_id: str) -> list[dict]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        return user.weight_history
```

#### `api/v1/users.py`
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserProfileUpdate, WeightUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.get_profile(current_user.id)

@router.patch("/me", response_model=UserProfileResponse)
def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.update_profile(current_user.id, data)

@router.post("/me/weight", response_model=UserProfileResponse)
def add_weight(
    data: WeightUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.add_weight_record(current_user.id, data.weight)

@router.get("/me/weight-history")
def get_weight_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.get_weight_history(current_user.id)

@router.patch("/me/goals", response_model=UserProfileResponse)
def update_goals(
    goals: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.update_goals(current_user.id, goals)

@router.patch("/me/preferences", response_model=UserProfileResponse)
def update_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.update_preferences(current_user.id, preferences)
```

### 2. Pydantic Schemas

#### `schemas/user.py`
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal

class UserProfileResponse(BaseModel):
    id: str
    email: str
    nickname: str
    gender: Literal["male", "female"]
    birth_year: int
    height: int
    weight_history: list[dict]
    current_weight: Optional[float] = None
    fitness_level: Literal["beginner", "intermediate", "advanced"]
    primary_goal: Literal["fat_loss", "muscle_gain", "tone", "strength", "health"]
    workout_frequency: int
    workout_duration: int
    injuries: Optional[str] = None
    gym_location: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: dict
    total_workouts: int
    last_workout_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    height: Optional[int] = None
    injuries: Optional[str] = None
    gym_location: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

class WeightUpdate(BaseModel):
    weight: float = Field(..., gt=20, lt=300, description="Weight in kg")

class GoalsUpdate(BaseModel):
    primary_goal: Optional[Literal["fat_loss", "muscle_gain", "tone", "strength", "health"]] = None
    fitness_level: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    workout_frequency: Optional[int] = Field(None, ge=1, le=7)
    workout_duration: Optional[int] = Field(None, ge=15, le=180)

class PreferencesUpdate(BaseModel):
    coach_style: Optional[Literal["strict", "encouraging", "humorous", "professional", "balanced"]] = None
    notification_enabled: Optional[bool] = None
    daily_greeting_time: Optional[str] = None  # HH:MM format
    units: Optional[Literal["metric", "imperial"]] = None
```

### 3. Frontend Implementation

#### `app/(main)/profile/page.tsx`
```typescript
'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth';
import { useQuery, useMutation } from '@tanstack/react-query';
import { userApi } from '@/lib/api/user';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: userApi.getProfile,
  });

  const updateMutation = useMutation({
    mutationFn: userApi.updateProfile,
    onSuccess: () => {
      // Refresh profile
    },
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="container max-w-2xl mx-auto py-8">
      <h1 className="text-2xl font-bold mb-6">My Profile</h1>

      <Card className="p-6 space-y-6">
        {/* Basic Info */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Basic Information</h2>
          <div>
            <Label>Nickname</Label>
            <Input defaultValue={profile?.nickname} />
          </div>
          <div>
            <Label>Email</Label>
            <Input value={profile?.email} disabled />
          </div>
        </div>

        {/* Body Data */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Body Data</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Height (cm)</Label>
              <Input type="number" defaultValue={profile?.height} />
            </div>
            <div>
              <Label>Current Weight (kg)</Label>
              <Input type="number" defaultValue={profile?.current_weight} />
            </div>
          </div>
        </div>

        {/* Fitness Goals */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Fitness Goals</h2>
          <div>
            <Label>Primary Goal</Label>
            <select className="w-full p-2 border rounded">
              <option value="fat_loss">Fat Loss</option>
              <option value="muscle_gain">Muscle Gain</option>
              <option value="tone">Tone</option>
              <option value="strength">Strength</option>
              <option value="health">Health</option>
            </select>
          </div>
        </div>

        <Button onClick={() => updateMutation.mutate(/* data */)}>
          Save Changes
        </Button>
      </Card>
    </div>
  );
}
```

#### `lib/api/user.ts`
```typescript
import api from '@/lib/api';

export interface UserProfile {
  id: string;
  email: string;
  nickname: string;
  gender: 'male' | 'female';
  birth_year: number;
  height: number;
  weight_history: Array<{ date: string; weight: number }>;
  current_weight: number | null;
  fitness_level: 'beginner' | 'intermediate' | 'advanced';
  primary_goal: string;
  workout_frequency: number;
  workout_duration: number;
  injuries: string | null;
  gym_location: string | null;
  phone: string | null;
  avatar_url: string | null;
  preferences: {
    coach_style: string;
    notification_enabled: boolean;
    daily_greeting_time: string;
    units: 'metric' | 'imperial';
  };
  total_workouts: number;
  last_workout_date: string | null;
  created_at: string;
}

export const userApi = {
  getProfile: async (): Promise<UserProfile> => {
    const response = await api.get('/api/v1/users/me');
    return response.data;
  },

  updateProfile: async (data: Partial<UserProfile>): Promise<UserProfile> => {
    const response = await api.patch('/api/v1/users/me', data);
    return response.data;
  },

  addWeight: async (weight: number): Promise<UserProfile> => {
    const response = await api.post('/api/v1/users/me/weight', { weight });
    return response.data;
  },

  getWeightHistory: async (): Promise<Array<{ date: string; weight: number }>> => {
    const response = await api.get('/api/v1/users/me/weight-history');
    return response.data;
  },

  updateGoals: async (goals: {
    primary_goal?: string;
    fitness_level?: string;
    workout_frequency?: number;
    workout_duration?: number;
  }): Promise<UserProfile> => {
    const response = await api.patch('/api/v1/users/me/goals', goals);
    return response.data;
  },

  updatePreferences: async (preferences: {
    coach_style?: string;
    notification_enabled?: boolean;
    daily_greeting_time?: string;
    units?: 'metric' | 'imperial';
  }): Promise<UserProfile> => {
    const response = await api.patch('/api/v1/users/me/preferences', preferences);
    return response.data;
  },
};
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users/me` | Get user profile |
| PATCH | `/api/v1/users/me` | Update profile |
| POST | `/api/v1/users/me/weight` | Add weight record |
| GET | `/api/v1/users/me/weight-history` | Get weight history |
| PATCH | `/api/v1/users/me/goals` | Update fitness goals |
| PATCH | `/api/v1/users/me/preferences` | Update preferences |

## Technical Requirements

- React Query for data fetching
- Optimistic updates for better UX
- Form validation with Zod
- Avatar upload to MinIO/S3

## Acceptance Criteria

- [ ] User can view complete profile
- [ ] User can update nickname, height, injuries
- [ ] User can add weight records
- [ ] Weight history displays as chart
- [ ] User can change fitness goals
- [ ] User can select coach style
- [ ] Notification settings work
- [ ] Avatar uploads and displays

## Notes

- Weight history should be used for progress tracking
- Goals update should trigger plan regeneration notification
- Preferences affect AI coach behavior
