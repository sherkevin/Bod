# Task: Workout Plan Generation

## Overview

Implement AI-powered workout plan generation based on user profile, goals, and available equipment.

## Dependencies

- Requires `user-profile` to be completed
- Requires `equipment-management` to be completed

## Deliverables

### 1. Backend Implementation

#### `services/plan_service.py`
```python
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.workout import WorkoutPlan, WorkoutSession
from app.models.user import User
from app.models.equipment import UserEquipment
from app.services.llm import LLMService
from app.schemas.plan import PlanGenerateRequest, PlanResponse

class PlanService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService()

    async def generate_plan(self, user_id: str, request: PlanGenerateRequest) -> WorkoutPlan:
        # Get user data
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        # Get available equipment
        equipment = (
            self.db.query(UserEquipment)
            .filter(UserEquipment.user_id == user_id, UserEquipment.is_available == True)
            .all()
        )

        # Build prompt for LLM
        prompt = self._build_plan_prompt(user, equipment, request)

        # Generate plan using LLM
        plan_data = await self.llm.generate_plan(prompt)

        # Create plan in database
        plan = WorkoutPlan(
            user_id=user_id,
            name=request.name or f"{user.primary_goal} Plan",
            start_date=request.start_date,
            end_date=request.start_date + timedelta(weeks=request.weeks),
            weeks_count=request.weeks,
            goals={
                "primary_goal": user.primary_goal,
                "fitness_level": user.fitness_level,
                "frequency": user.workout_frequency,
                "duration": user.workout_duration,
            },
            preferences=request.preferences or {},
            status="draft",
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        # Create sessions
        await self._create_sessions(plan, plan_data)

        return plan

    def _build_plan_prompt(self, user: User, equipment: list, request: PlanGenerateRequest) -> str:
        equipment_list = [e.name for e in equipment]
        equipment_by_category = {
            "free_weight": [e.name for e in equipment if e.category == "free_weight"],
            "machine": [e.name for e in equipment if e.category == "machine"],
            "cardio": [e.name for e in equipment if e.category == "cardio"],
        }

        return f"""
Generate a {request.weeks}-week workout plan with the following specifications:

USER PROFILE:
- Goal: {user.primary_goal}
- Fitness Level: {user.fitness_level}
- Frequency: {user.workout_frequency} days per week
- Duration: {user.workout_duration} minutes per session
- Injuries: {user.injuries or 'None'}

AVAILABLE EQUIPMENT:
- Free weights: {', '.join(equipment_by_category['free_weight']) or 'None'}
- Machines: {', '.join(equipment_by_category['machine']) or 'None'}
- Cardio: {', '.join(equipment_by_category['cardio']) or 'None'}

REQUIREMENTS:
1. Create a weekly schedule based on the frequency
2. Each workout session should target specific muscle groups
3. Include exercise name, sets, reps, rest time
4. Consider the user's fitness level for exercise selection
5. For fat loss: include cardio components
6. For muscle gain: focus on progressive overload
7. Respect injury limitations

Return the plan in the following JSON format:
{{
  "weeks": [
    {{
      "week": 1,
      "sessions": [
        {{
          "day_of_week": "Monday",
          "theme": "Chest + Triceps",
          "exercises": [
            {{
              "name": "Bench Press",
              "sets": 4,
              "reps": "8-12",
              "rest_seconds": 90,
              "category": "compound"
            }}
          ]
        }}
      ]
    }}
  ]
}}
"""

    async def _create_sessions(self, plan: WorkoutPlan, plan_data: dict) -> None:
        """Create workout sessions from generated plan data"""
        # Implementation for creating sessions
        pass

    def get_plan(self, user_id: str, plan_id: str) -> WorkoutPlan:
        plan = (
            self.db.query(WorkoutPlan)
            .filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id)
            .first()
        )
        if not plan:
            raise NotFoundException("Plan not found")
        return plan

    def list_plans(self, user_id: str) -> list[WorkoutPlan]:
        return (
            self.db.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.created_at.desc())
            .all()
        )

    def update_plan_status(self, user_id: str, plan_id: str, status: str) -> WorkoutPlan:
        plan = self.get_plan(user_id, plan_id)
        plan.status = status
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def regenerate_week(
        self, user_id: str, plan_id: str, week_number: int
    ) -> dict:
        """Regenerate a specific week of the plan"""
        plan = self.get_plan(user_id, plan_id)
        # Implementation for week regeneration
        pass
```

#### `services/llm.py` - LLM Service Wrapper
```python
import httpx
import json
from app.config import settings

class LLMService:
    def __init__(self):
        self.base_url = settings.VLLM_URL

    async def generate_plan(self, prompt: str) -> dict:
        """Generate workout plan using LLM"""
        payload = {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert fitness coach. Generate workout plans in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

        content = result["choices"][0]["message"]["content"]
        return json.loads(content)

    async def chat(self, messages: list, coach_style: str = "balanced") -> str:
        """Generate chat response"""
        system_prompts = {
            "strict": "You are a strict, no-nonsense fitness coach. Be direct and demanding.",
            "encouraging": "You are a warm, encouraging fitness coach. Be supportive and positive.",
            "humorous": "You are a fun, humorous fitness coach. Use humor to motivate.",
            "professional": "You are a professional, scientific fitness coach. Provide data-driven advice.",
            "balanced": "You are a balanced fitness coach. Adapt your style to the situation."
        }

        payload = {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {"role": "system", "content": system_prompts.get(coach_style, system_prompts["balanced"])},
                *messages
            ],
            "temperature": 0.8
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

        return result["choices"][0]["message"]["content"]
```

#### `api/v1/plans.py`
```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.plan import PlanGenerateRequest, PlanResponse, PlanDetailResponse
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["plans"])

@router.post("", response_model=PlanResponse)
async def generate_plan(
    request: PlanGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PlanService(db)
    plan = await service.generate_plan(current_user.id, request)
    return plan

@router.get("", response_model=list[PlanResponse])
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PlanService(db)
    return service.list_plans(current_user.id)

@router.get("/{plan_id}", response_model=PlanDetailResponse)
def get_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PlanService(db)
    return service.get_plan(current_user.id, plan_id)

@router.patch("/{plan_id}/status")
def update_status(
    plan_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PlanService(db)
    return service.update_plan_status(current_user.id, plan_id, status)

@router.post("/{plan_id}/regenerate/{week_number}")
async def regenerate_week(
    plan_id: str,
    week_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PlanService(db)
    return await service.regenerate_week(current_user.id, plan_id, week_number)
```

### 2. Pydantic Schemas

#### `schemas/plan.py`
```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List

class PlanGenerateRequest(BaseModel):
    name: Optional[str] = None
    weeks: int = Field(8, ge=4, le=16, description="Plan duration in weeks")
    start_date: date = Field(default_factory=date.today)
    preferences: Optional[dict] = None

class ExerciseInPlan(BaseModel):
    name: str
    sets: int
    reps: str
    rest_seconds: int
    category: str

class SessionInPlan(BaseModel):
    id: str
    date: date
    day_of_week: str
    theme: str
    exercises: List[ExerciseInPlan]
    status: str

class WeekInPlan(BaseModel):
    week_number: int
    sessions: List[SessionInPlan]

class PlanResponse(BaseModel):
    id: str
    name: str
    start_date: date
    end_date: date
    weeks_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class PlanDetailResponse(PlanResponse):
    goals: dict
    preferences: dict
    weeks: List[WeekInPlan]
```

### 3. Frontend Implementation

#### `app/(main)/plan/page.tsx`
```typescript
'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { planApi } from '@/lib/api/plan';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export default function PlanPage() {
  const [showGenerate, setShowGenerate] = useState(false);

  const { data: plans, isLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: planApi.listPlans,
  });

  const generateMutation = useMutation({
    mutationFn: planApi.generatePlan,
    onSuccess: () => {
      setShowGenerate(false);
    },
  });

  const activePlan = plans?.find(p => p.status === 'active');

  return (
    <div className="container max-w-4xl mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Workout Plan</h1>
        <Button onClick={() => setShowGenerate(true)}>
          Generate New Plan
        </Button>
      </div>

      {/* Active Plan */}
      {activePlan ? (
        <ActivePlanView plan={activePlan} />
      ) : (
        <Card className="p-8 text-center">
          <h2 className="text-lg font-semibold mb-2">No Active Plan</h2>
          <p className="text-muted-foreground mb-4">
            Generate a personalized workout plan to get started
          </p>
          <Button onClick={() => setShowGenerate(true)}>
            Create Plan
          </Button>
        </Card>
      )}

      {/* Plan History */}
      {plans && plans.length > 1 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-4">Plan History</h2>
          <div className="space-y-2">
            {plans.filter(p => p.id !== activePlan?.id).map(plan => (
              <Card key={plan.id} className="p-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="font-medium">{plan.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {plan.weeks_count} weeks • {plan.status}
                    </p>
                  </div>
                  <Button variant="outline" size="sm">
                    View
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Generate Dialog */}
      <GeneratePlanDialog
        open={showGenerate}
        onClose={() => setShowGenerate(false)}
        onGenerate={(data) => generateMutation.mutate(data)}
      />
    </div>
  );
}

function ActivePlanView({ plan }: { plan: Plan }) {
  const { data: detail } = useQuery({
    queryKey: ['plan', plan.id],
    queryFn: () => planApi.getPlan(plan.id),
    enabled: !!plan.id,
  });

  if (!detail) return null;

  return (
    <Card className="p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-xl font-bold">{detail.name}</h2>
          <p className="text-muted-foreground">
            {detail.weeks.length} weeks • {detail.goals.frequency} days/week
          </p>
        </div>
        <Button variant="outline">Edit Plan</Button>
      </div>

      {/* Week Navigation */}
      <div className="flex gap-2 overflow-x-auto pb-4">
        {detail.weeks.map((week, index) => (
          <button
            key={week.week_number}
            className="px-4 py-2 rounded-lg bg-secondary text-sm"
          >
            Week {week.week_number}
          </button>
        ))}
      </div>

      {/* Weekly Schedule */}
      <div className="space-y-2">
        {detail.weeks[0]?.sessions.map((session) => (
          <div
            key={session.id}
            className="p-4 rounded-lg border flex justify-between items-center"
          >
            <div>
              <div className="font-medium">{session.theme}</div>
              <div className="text-sm text-muted-foreground">
                {session.day_of_week} • {session.exercises.length} exercises
              </div>
            </div>
            <Button variant="ghost" size="sm">
              View
            </Button>
          </div>
        ))}
      </div>
    </Card>
  );
}
```

#### `lib/api/plan.ts`
```typescript
import api from '@/lib/api';

export interface Exercise {
  name: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  category: string;
}

export interface Session {
  id: string;
  date: string;
  day_of_week: string;
  theme: string;
  exercises: Exercise[];
  status: string;
}

export interface Week {
  week_number: number;
  sessions: Session[];
}

export interface Plan {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  weeks_count: number;
  status: 'draft' | 'active' | 'completed' | 'paused';
  goals: {
    primary_goal: string;
    fitness_level: string;
    frequency: number;
    duration: number;
  };
  preferences: Record<string, unknown>;
  weeks: Week[];
  created_at: string;
}

export const planApi = {
  listPlans: async (): Promise<Plan[]> => {
    const response = await api.get('/api/v1/plans');
    return response.data;
  },

  getPlan: async (id: string): Promise<Plan> => {
    const response = await api.get(`/api/v1/plans/${id}`);
    return response.data;
  },

  generatePlan: async (data: {
    name?: string;
    weeks?: number;
    start_date?: string;
    preferences?: Record<string, unknown>;
  }): Promise<Plan> => {
    const response = await api.post('/api/v1/plans', data);
    return response.data;
  },

  updateStatus: async (id: string, status: string): Promise<Plan> => {
    const response = await api.patch(`/api/v1/plans/${id}/status`, null, {
      params: { status },
    });
    return response.data;
  },

  regenerateWeek: async (id: string, weekNumber: number): Promise<Week> => {
    const response = await api.post(`/api/v1/plans/${id}/regenerate/${weekNumber}`);
    return response.data;
  },
};
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/plans` | Generate new plan |
| GET | `/api/v1/plans` | List user's plans |
| GET | `/api/v1/plans/{id}` | Get plan details |
| PATCH | `/api/v1/plans/{id}/status` | Update plan status |
| POST | `/api/v1/plans/{id}/regenerate/{week}` | Regenerate week |

## Technical Requirements

- LLM: Qwen-2.5-14B-Instruct via vLLM
- Prompt engineering for structured JSON output
- Async processing for plan generation
- Week-based progression logic

## Acceptance Criteria

- [ ] User can generate plan from profile
- [ ] Plan considers available equipment
- [ ] Plan adapts to fitness level
- [ ] Plan structure is valid JSON
- [ ] Plan displays week by week
- [ ] User can regenerate specific week
- [ ] Plan status can be changed
- [ ] Plan duration is 4-16 weeks

## Notes

- Include progression between weeks
- Add deload weeks every 4th week
- Consider muscle group splits
- Account for rest days properly
