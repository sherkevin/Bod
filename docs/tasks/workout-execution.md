# Task: Workout Execution

## Overview

Implement the workout execution interface where users follow their planned exercises, log sets, and track their training sessions.

## Dependencies

- Requires `workout-plan` to be completed

## Deliverables

### 1. Backend Implementation

#### `services/workout_service.py`
```python
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.workout import WorkoutSession, SessionExercise, SetLog
from app.schemas.workout import SessionStartRequest, SetLogCreate, SessionComplete

class WorkoutService:
    def __init__(self, db: Session):
        self.db = db

    def start_session(self, user_id: str, session_id: str) -> WorkoutSession:
        """Start a workout session"""
        session = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
            .first()
        )
        if not session:
            raise NotFoundException("Session not found")

        session.status = "in_progress"
        session.actual_date = datetime.now().date()
        self.db.commit()
        self.db.refresh(session)

        # Create session exercise records
        for idx, exercise_data in enumerate(session.exercises_plan):
            ex = SessionExercise(
                id=str(uuid.uuid4()),
                session_id=session.id,
                exercise_id=exercise_data["exercise_id"],
                sets_planned=exercise_data["sets"],
                reps_planned=exercise_data["reps"],
                weight_planned=exercise_data.get("weight"),
                rest_seconds=exercise_data.get("rest", 90),
                order=idx,
            )
            self.db.add(ex)

        self.db.commit()
        return session

    def log_set(
        self, user_id: str, session_id: str, exercise_id: str, data: SetLogCreate
    ) -> SetLog:
        """Log a completed set"""
        session = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
            .first()
        )
        if not session:
            raise NotFoundException("Session not found")

        log = SetLog(
            id=str(uuid.uuid4()),
            session_id=session_id,
            exercise_id=exercise_id,
            set_number=data.set_number,
            weight=data.weight,
            reps=data.reps,
            rpe=data.rpe,
            rest_seconds=data.rest_seconds,
            transcript=data.transcript,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_session_logs(self, user_id: str, session_id: str) -> list:
        """Get all logs for a session"""
        logs = (
            self.db.query(SetLog)
            .filter(SetLog.session_id == session_id)
            .order_by(SetLog.logged_at)
            .all()
        )
        # Group by exercise
        result = {}
        for log in logs:
            if log.exercise_id not in result:
                result[log.exercise_id] = []
            result[log.exercise_id].append({
                "set_number": log.set_number,
                "weight": float(log.weight),
                "reps": log.reps,
                "rpe": log.rpe,
            })
        return result

    def complete_session(
        self, user_id: str, session_id: str, data: SessionComplete
    ) -> WorkoutSession:
        """Mark session as completed"""
        session = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
            .first()
        )
        if not session:
            raise NotFoundException("Session not found")

        session.status = "completed"
        session.duration_minutes = data.duration_minutes
        session.notes = data.notes

        # Update user stats
        from app.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.total_workouts += 1
            user.last_workout_date = datetime.now().date()

        self.db.commit()
        self.db.refresh(session)
        return session

    def skip_session(self, user_id: str, session_id: str, reason: str = None) -> WorkoutSession:
        """Skip a scheduled session"""
        session = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
            .first()
        )
        if not session:
            raise NotFoundException("Session not found")

        session.status = "skipped"
        session.notes = reason

        self.db.commit()
        self.db.refresh(session)
        return session

    def get_current_exercise(
        self, user_id: str, session_id: str
    ) -> dict:
        """Get current exercise with progress"""
        session = (
            self.db.query(WorkoutSession)
            .filter(WorkoutSession.id == session_id)
            .first()
        )

        session_exercises = (
            self.db.query(SessionExercise)
            .filter(SessionExercise.session_id == session_id)
            .order_by(SessionExercise.order)
            .all()
        )

        # Find current exercise (first incomplete or last)
        current = None
        for se in session_exercises:
            logs = (
                self.db.query(SetLog)
                .filter(
                    SetLog.session_id == session_id,
                    SetLog.exercise_id == se.exercise_id
                )
                .count()
            )
            if logs < se.sets_planned:
                current = {
                    "exercise": se,
                    "completed_sets": logs,
                    "total_sets": se.sets_planned,
                    "last_log": self._get_last_log(session_id, se.exercise_id),
                }
                break

        return current or {}

    def _get_last_log(self, session_id: str, exercise_id: str) -> dict:
        log = (
            self.db.query(SetLog)
            .filter(
                SetLog.session_id == session_id,
                SetLog.exercise_id == exercise_id
            )
            .order_by(SetLog.logged_at.desc())
            .first()
        )
        if log:
            return {"weight": float(log.weight), "reps": log.reps, "rpe": log.rpe}
        return {}
```

#### `api/v1/workout.py`
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.workout import SessionStartRequest, SetLogCreate, SessionComplete
from app.services.workout_service import WorkoutService

router = APIRouter(prefix="/workout", tags=["workout"])

@router.post("/sessions/{session_id}/start")
def start_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = WorkoutService(db)
    return service.start_session(current_user.id, session_id)

@router.get("/sessions/{session_id}/current")
def get_current_exercise(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = WorkoutService(db)
    return service.get_current_exercise(current_user.id, session_id)

@router.post("/sessions/{session_id}/logs")
def log_set(
    session_id: str,
    exercise_id: str,
    data: SetLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = WorkoutService(db)
    return service.log_set(current_user.id, session_id, exercise_id, data)

@router.get("/sessions/{session_id}/logs")
def get_session_logs(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = WorkoutService(db)
    return service.get_session_logs(current_user.id, session_id)

@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: str,
    data: SessionComplete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = WorkoutService(db)
    return service.complete_session(current_user.id, session_id, data)

@router.post("/sessions/{session_id}/skip")
def skip_session(
    session_id: str,
    reason: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = WorkoutService(db)
    return service.skip_session(current_user.id, session_id, reason)
```

### 2. Pydantic Schemas

#### `schemas/workout.py`
```python
from pydantic import BaseModel, Field
from typing import Optional

class SetLogCreate(BaseModel):
    set_number: int = Field(..., ge=1)
    weight: float = Field(..., ge=0)
    reps: int = Field(..., ge=1, le=100)
    rpe: int = Field(..., ge=1, le=10, description="Rate of Perceived Exertion")
    rest_seconds: Optional[int] = None
    transcript: Optional[str] = None

class SessionComplete(BaseModel):
    duration_minutes: int = Field(..., ge=1)
    notes: Optional[str] = None
    mood: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    plan_id: str
    scheduled_date: str
    theme: str
    status: str
    exercises: list
    duration_minutes: Optional[int] = None

    class Config:
        from_attributes = True
```

### 3. Frontend Implementation

#### `app/(main)/workout/page.tsx`
```typescript
'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { workoutApi } from '@/lib/api/workout';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

export default function WorkoutPage() {
  const [sessionId] = useState('current'); // From router params
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);

  const { data: currentData, isLoading } = useQuery({
    queryKey: ['workout', 'current', sessionId],
    queryFn: () => workoutApi.getCurrentExercise(sessionId),
    refetchInterval: 5000,
  });

  const logMutation = useMutation({
    mutationFn: (data: { exerciseId: string; set: number; weight: number; reps: number; rpe: number }) =>
      workoutApi.logSet(sessionId, data.exerciseId, data),
    onSuccess: () => {
      // Refetch current exercise
    },
  });

  const completeMutation = useMutation({
    mutationFn: (data: { duration: number; notes?: string }) =>
      workoutApi.completeSession(sessionId, data),
  });

  if (isLoading) return <div>Loading...</div>;

  const exercise = currentData?.exercise;
  const progress = currentData
    ? (currentData.completed_sets / currentData.total_sets) * 100
    : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b p-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">{exercise?.name}</h1>
            <p className="text-sm text-muted-foreground">
              Set {currentData?.completed_sets + 1} of {currentData?.total_sets}
            </p>
          </div>
          <Button variant="destructive" size="sm">
            End Workout
          </Button>
        </div>
        <Progress value={progress} className="mt-4" />
      </header>

      {/* Exercise Info */}
      <div className="p-4">
        <Card className="p-6 mb-4">
          <h2 className="text-2xl font-bold mb-2">{exercise?.name}</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-sm text-muted-foreground">Sets</div>
              <div className="text-2xl font-bold">
                {currentData?.completed_sets}/{currentData?.total_sets}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Reps</div>
              <div className="text-2xl font-bold">{exercise?.reps_planned}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Rest</div>
              <div className="text-2xl font-bold">
                {exercise?.rest_seconds}s
              </div>
            </div>
          </div>
        </Card>

        {/* Last Log */}
        {currentData?.last_log && (
          <Card className="p-4 mb-4 bg-secondary">
            <h3 className="font-semibold mb-2">Last Set</h3>
            <div className="flex gap-4">
              <span>{currentData.last_log.weight}kg</span>
              <span>{currentData.last_log.reps} reps</span>
              <span>RPE {currentData.last_log.rpe}</span>
            </div>
          </Card>
        )}

        {/* Set Logging */}
        <SetLogger
          exerciseId={exercise?.id || ''}
          setNumber={(currentData?.completed_sets || 0) + 1}
          suggestedWeight={currentData?.last_log?.weight}
          onSubmit={(data) => logMutation.mutate(data)}
        />

        {/* Navigation */}
        <div className="flex gap-2 mt-6">
          <Button variant="outline" className="flex-1">
            Previous Exercise
          </Button>
          <Button className="flex-1">
            Next Exercise
          </Button>
        </div>
      </div>

      {/* Complete Workout Button */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-background border-t">
        <Button
          className="w-full"
          size="lg"
          onClick={() => completeMutation.mutate({ duration: 45 })}
        >
          Complete Workout
        </Button>
      </div>
    </div>
  );
}

function SetLogger({
  exerciseId,
  setNumber,
  suggestedWeight,
  onSubmit,
}: {
  exerciseId: string;
  setNumber: number;
  suggestedWeight?: number;
  onSubmit: (data: { exerciseId: string; set: number; weight: number; reps: number; rpe: number }) => void;
}) {
  const [weight, setWeight] = useState(suggestedWeight?.toString() || '');
  const [reps, setReps] = useState('');
  const [rpe, setRpe] = useState('7');

  const handleSubmit = () => {
    onSubmit({
      exerciseId,
      set: setNumber,
      weight: parseFloat(weight),
      reps: parseInt(reps),
      rpe: parseInt(rpe),
    });
    setWeight('');
    setReps('');
  };

  return (
    <Card className="p-6">
      <h3 className="font-semibold mb-4">Log Set {setNumber}</h3>
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium">Weight (kg)</label>
          <input
            type="number"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className="w-full p-3 border rounded-lg text-2xl text-center"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Reps</label>
          <input
            type="number"
            value={reps}
            onChange={(e) => setReps(e.target.value)}
            className="w-full p-3 border rounded-lg text-2xl text-center"
          />
        </div>
        <div>
          <label className="text-sm font-medium">RPE (1-10)</label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((value) => (
              <button
                key={value}
                onClick={() => setRpe(value.toString())}
                className={`flex-1 py-2 rounded ${
                  rpe === value.toString()
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary'
                }`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>
        <Button onClick={handleSubmit} className="w-full" size="lg">
          Log Set
        </Button>
      </div>
    </Card>
  );
}
```

#### `lib/api/workout.ts`
```typescript
import api from '@/lib/api';

export interface CurrentExercise {
  exercise: {
    id: string;
    name: string;
    sets_planned: number;
    reps_planned: string;
    rest_seconds: number;
  };
  completed_sets: number;
  total_sets: number;
  last_log: {
    weight: number;
    reps: number;
    rpe: number;
  } | null;
}

export const workoutApi = {
  startSession: async (sessionId: string) => {
    const response = await api.post(`/api/v1/workout/sessions/${sessionId}/start`);
    return response.data;
  },

  getCurrentExercise: async (sessionId: string): Promise<CurrentExercise> => {
    const response = await api.get(`/api/v1/workout/sessions/${sessionId}/current`);
    return response.data;
  },

  logSet: async (sessionId: string, exerciseId: string, data: {
    set_number: number;
    weight: number;
    reps: number;
    rpe: number;
  }) => {
    const response = await api.post(
      `/api/v1/workout/sessions/${sessionId}/logs`,
      { ...data, exercise_id: exerciseId }
    );
    return response.data;
  },

  getSessionLogs: async (sessionId: string) => {
    const response = await api.get(`/api/v1/workout/sessions/${sessionId}/logs`);
    return response.data;
  },

  completeSession: async (sessionId: string, data: {
    duration_minutes: number;
    notes?: string;
  }) => {
    const response = await api.post(`/api/v1/workout/sessions/${sessionId}/complete`, data);
    return response.data;
  },

  skipSession: async (sessionId: string, reason?: string) => {
    const response = await api.post(`/api/v1/workout/sessions/${sessionId}/skip`, null, {
      params: { reason },
    });
    return response.data;
  },
};
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/workout/sessions/{id}/start` | Start workout session |
| GET | `/api/v1/workout/sessions/{id}/current` | Get current exercise |
| POST | `/api/v1/workout/sessions/{id}/logs` | Log a set |
| GET | `/api/v1/workout/sessions/{id}/logs` | Get session logs |
| POST | `/api/v1/workout/sessions/{id}/complete` | Complete session |
| POST | `/api/v1/workout/sessions/{id}/skip` | Skip session |

## Technical Requirements

- Real-time progress updates
- Large touch targets for gym use
- Rest timer with alerts
- Session state persistence

## Acceptance Criteria

- [ ] User can start a planned session
- [ ] Current exercise displays with details
- [ ] User can log sets with weight/reps/RPE
- [ ] Progress bar updates after each set
- [ ] Previous set data shown as suggestion
- [ ] User can navigate between exercises
- [ ] Session can be completed or skipped
- [ ] Duration is tracked automatically

## Notes

- This integrates with voice-interaction task
- Consider offline logging with sync
- Add rest timer functionality
- Show exercise instructions if available
