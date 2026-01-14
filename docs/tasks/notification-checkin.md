# Task: Notification and Check-in System

## Overview

Implement workout reminders, daily greetings, check-in functionality, and streak tracking using Web Push API.

## Dependencies

- Requires `workout-execution` to be completed

## Deliverables

### 1. Backend Implementation

#### `services/notification_service.py`
```python
import json
from datetime import datetime, time
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.workout import WorkoutSession, CheckIn
from app.schemas.notification import NotificationCreate, NotificationResponse

class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.vapid_keys = self._load_vapid_keys()

    def _load_vapid_keys(self) -> dict:
        """Load VAPID keys for Web Push"""
        import os
        from app.config import settings

        return {
            "public_key": os.getenv("VAPID_PUBLIC_KEY"),
            "private_key": os.getenv("VAPID_PRIVATE_KEY"),
        }

    async def register_subscription(
        self, user_id: str, subscription: dict
    ) -> dict:
        """
        Register user's push subscription

        Subscription format:
        {
            "endpoint": "https://fcm.googleapis.com/...",
            "keys": {
                "p256dh": "key",
                "auth": "auth"
            }
        }
        """
        from app.models.notification import PushSubscription

        # Remove old subscriptions for this user
        self.db.query(PushSubscription).filter(
            PushSubscription.user_id == user_id
        ).delete()

        # Create new subscription
        sub = PushSubscription(
            user_id=user_id,
            endpoint=subscription["endpoint"],
            p256dh_key=subscription["keys"]["p256dh"],
            auth_key=subscription["keys"]["auth"],
            created_at=datetime.now()
        )
        self.db.add(sub)
        self.db.commit()

        return {"status": "registered"}

    async def send_notification(
        self,
        user_id: str,
        notification: NotificationCreate
    ) -> bool:
        """Send push notification to user"""
        from app.models.notification import PushSubscription
        from pywebpush import webpush

        subscriptions = (
            self.db.query(PushSubscription)
            .filter(PushSubscription.user_id == user_id)
            .all()
        )

        if not subscriptions:
            return False

        payload = json.dumps({
            "title": notification.title,
            "body": notification.body,
            "icon": "/icon-192.png",
            "badge": "/badge-72.png",
            "data": notification.data or {},
            "actions": notification.actions or []
        })

        for sub in subscriptions:
            try:
                subscription_info = {
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh_key,
                        "auth": sub.auth_key
                    }
                }

                webpush(
                    subscription_info,
                    payload,
                    vapid_private_key=self.vapid_keys["private_key"],
                    vapid_claims={
                        "sub": "mailto:contact@bod.fit"
                    }
                )
            except Exception as e:
                print(f"Failed to send notification: {e}")

        return True

    async def send_workout_reminder(
        self, user_id: str, session: WorkoutSession
    ) -> None:
        """Send workout reminder notification"""
        notification = NotificationCreate(
            title="Time to workout! 💪",
            body=f"Today's session: {session.theme}",
            data={
                "type": "workout_reminder",
                "session_id": session.id
            },
            actions=[
                {"action": "start", "title": "Start Workout"},
                {"action": "snooze", "title": "10 min later"}
            ]
        )
        await self.send_notification(user_id, notification)

    async def send_daily_greeting(
        self, user_id: str, greeting_type: str
    ) -> None:
        """Send daily greeting from AI coach"""
        # Generate personalized greeting
        greeting = self._generate_greeting(greeting_type)

        notification = NotificationCreate(
            title="Your Coach 👋",
            body=greeting,
            data={
                "type": "daily_greeting",
                "greeting_type": greeting_type
            },
            actions=[
                {"action": "reply", "title": "Reply"},
                {"action": "view", "title": "View Plan"}
            ]
        )
        await self.send_notification(user_id, notification)

    async def send_missed_workout_reminder(self, user_id: str, days_missed: int) -> None:
        """Send notification for missed workouts"""
        notification = NotificationCreate(
            title=f"Missed you! {days_missed} days",
            body="Ready to get back on track? Let's do this!",
            data={"type": "missed_workout", "days": days_missed},
            actions=[
                {"action": "start", "title": "Workout Now"},
                {"action": "rest", "title": "Rest Day"}
            ]
        )
        await self.send_notification(user_id, notification)

    def _generate_greeting(self, greeting_type: str) -> str:
        """Generate greeting based on type"""
        greetings = {
            "pre_workout": "Today's going to be great! Are you ready for your session?",
            "post_workout": "Great job today! How did you feel about the workout?",
            "rest_day": "Enjoy your rest day! Recovery is key to progress.",
            "check_in": "Hey! How's your training going? Let me know how you're feeling.",
            "missed": "I haven't seen you in a while. Everything okay?"
        }
        return greetings.get(greeting_type, "How's your fitness journey going?")
```

#### `services/checkin_service.py`
```python
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.workout import WorkoutSession, CheckIn
from app.models.user import User

class CheckInService:
    def __init__(self, db: Session):
        self.db = db

    def check_in(
        self,
        user_id: str,
        session_id: str,
        mood: str = None,
        notes: str = None
    ) -> CheckIn:
        """Create check-in after workout completion"""
        session = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id
            )
            .first()
        )
        if not session:
            raise NotFoundException("Session not found")

        # Calculate streak
        streak = self._calculate_streak(user_id)
        streak += 1

        # Calculate completion rate
        completion_rate = self._calculate_completion_rate(user_id)

        # Check for achievements
        achievements = self._check_achievements(user_id, streak, completion_rate)

        checkin = CheckIn(
            user_id=user_id,
            session_id=session_id,
            date=date.today(),
            streak_days=streak,
            completion_rate=completion_rate,
            achievements_unlocked=achievements,
            mood=mood,
            notes=notes
        )
        self.db.add(checkin)
        self.db.commit()
        self.db.refresh(checkin)

        return checkin

    def get_streak(self, user_id: str) -> int:
        """Get current streak days"""
        latest_checkin = (
            self.db.query(CheckIn)
            .filter(CheckIn.user_id == user_id)
            .order_by(CheckIn.date.desc())
            .first()
        )
        if not latest_checkin:
            return 0

        # Check if streak is still valid (within 2 days)
        days_since = (date.today() - latest_checkin.date).days
        if days_since > 2:
            return 0

        return latest_checkin.streak_days

    def get_checkin_history(
        self, user_id: str, days: int = 30
    ) -> list[CheckIn]:
        """Get check-in history"""
        start_date = date.today() - timedelta(days=days)

        return (
            self.db.query(CheckIn)
            .filter(
                CheckIn.user_id == user_id,
                CheckIn.date >= start_date
            )
            .order_by(CheckIn.date.desc())
            .all()
        )

    def get_checkin_calendar(
        self, user_id: str, year: int, month: int
    ) -> dict:
        """Get check-in status for each day in a month"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        checkins = (
            self.db.query(CheckIn)
            .filter(
                CheckIn.user_id == user_id,
                CheckIn.date >= start_date,
                CheckIn.date <= end_date
            )
            .all()
        )

        return {
            c.day: {"completed": True, "streak": c.streak_days}
            for c in checkins
        }

    def _calculate_streak(self, user_id: str) -> int:
        """Calculate streak from check-ins"""
        streak = 0
        current_date = date.today() - timedelta(days=1)  # Start from yesterday

        while True:
            checkin = (
                self.db.query(CheckIn)
                .filter(
                    CheckIn.user_id == user_id,
                    CheckIn.date == current_date
                )
                .first()
            )

            if checkin:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

        return streak

    def _calculate_completion_rate(self, user_id: str) -> float:
        """Calculate workout completion rate (last 30 days)"""
        thirty_days_ago = date.today() - timedelta(days=30)

        total = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.scheduled_date >= thirty_days_ago
            )
            .count()
        )

        completed = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.scheduled_date >= thirty_days_ago,
                WorkoutSession.status == "completed"
            )
            .count()
        )

        if total == 0:
            return 0.0

        return round((completed / total) * 100, 2)

    def _check_achievements(
        self, user_id: str, streak: int, completion_rate: float
    ) -> list:
        """Check for unlocked achievements"""
        achievements = []

        # Streak achievements
        streak_milestones = [3, 7, 14, 30, 60, 100]
        for milestone in streak_milestones:
            if streak == milestone:
                achievements.append({
                    "id": f"streak_{milestone}",
                    "name": f"{milestone} Day Streak",
                    "icon": "🔥"
                })

        # Completion achievements
        if completion_rate >= 90:
            achievements.append({
                "id": "dedicated",
                "name": "Dedicated Athlete",
                "icon": "💎"
            })

        # First workout
        if streak == 1:
            achievements.append({
                "id": "first_workout",
                "name": "First Steps",
                "icon": "🎯"
            })

        return achievements
```

#### `services/scheduler_service.py`
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.workout import WorkoutSession
from app.services.notification_service import NotificationService

class SchedulerService:
    def __init__(self, db: Session):
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self.notification_service = NotificationService(db)
        self._setup_jobs()

    def _setup_jobs(self):
        """Setup scheduled jobs"""
        # Check for workout reminders every 5 minutes
        self.scheduler.add_job(
            self.check_workout_reminders,
            'interval',
            minutes=5,
            id='workout_reminders'
        )

        # Send daily greetings at scheduled times
        self.scheduler.add_job(
            self.send_daily_greetings,
            'cron',
            hour='*/6',  # Every 6 hours
            id='daily_greetings'
        )

        # Check for missed workouts
        self.scheduler.add_job(
            self.check_missed_workouts,
            'cron',
            hour=20,  # 8 PM
            id='missed_workouts'
        )

        self.scheduler.start()

    async def check_workout_reminders(self):
        """Check and send workout reminders"""
        from app.config import settings

        now = datetime.now()
        reminder_time = (now + timedelta(minutes=30)).time()

        # Find sessions starting in 30 minutes
        sessions = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.status == "scheduled",
                WorkoutSession.scheduled_date == now.date()
            )
            .all()
        )

        for session in sessions:
            # Get user's reminder preference
            user = self.db.query(User).filter(User.id == session.user_id).first()
            if user.reminder_time == reminder_time:
                await self.notification_service.send_workout_reminder(
                    session.user_id, session
                )

    async def send_daily_greetings(self):
        """Send daily greetings to users"""
        users = self.db.query(User).all()

        for user in users:
            if not user.greeting_enabled:
                continue

            # Determine greeting type based on user's schedule
            greeting_type = self._determine_greeting_type(user)
            await self.notification_service.send_daily_greeting(
                user.id, greeting_type
            )

    async def check_missed_workouts(self):
        """Check for users who missed workouts"""
        from datetime import date, timedelta

        yesterday = date.today() - timedelta(days=1)

        # Find users who missed scheduled sessions
        missed_sessions = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.scheduled_date == yesterday,
                WorkoutSession.status == "scheduled"
            )
            .all()
        )

        # Group by user
        user_missed = {}
        for session in missed_sessions:
            if session.user_id not in user_missed:
                user_missed[session.user_id] = []
            user_missed[session.user_id].append(session)

        # Send reminders
        for user_id, sessions in user_missed.items():
            # Check consecutive missed days
            consecutive_missed = self._count_consecutive_missed(user_id)
            if consecutive_missed >= 2:
                await self.notification_service.send_missed_workout_reminder(
                    user_id, consecutive_missed
                )

    def _determine_greeting_type(self, user: User) -> str:
        """Determine appropriate greeting type"""
        now = datetime.now()
        today_session = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user.id,
                WorkoutSession.scheduled_date == now.date()
            )
            .first()
        )

        if today_session:
            if today_session.status == "completed":
                return "post_workout"
            else:
                return "pre_workout"
        else:
            return "rest_day"

    def _count_consecutive_missed(self, user_id: str) -> int:
        """Count consecutive missed workout days"""
        from datetime import date, timedelta

        count = 0
        check_date = date.today() - timedelta(days=1)

        while True:
            session = (
                self.db.query(WorkoutSession)
                .filter(
                    WorkoutSession.user_id == user_id,
                    WorkoutSession.scheduled_date == check_date
                )
                .first()
            )

            if not session or session.status == "completed":
                break

            if session.status == "scheduled":
                count += 1
                check_date -= timedelta(days=1)
            else:
                break

        return count
```

#### `api/v1/checkin.py`
```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.checkin import CheckInCreate, CheckInResponse, CheckInCalendar
from app.services.checkin_service import CheckInService

router = APIRouter(prefix="/checkin", tags=["checkin"])

@router.post("", response_model=CheckInResponse)
def check_in(
    data: CheckInCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create check-in after workout"""
    service = CheckInService(db)
    return service.check_in(
        current_user.id,
        data.session_id,
        data.mood,
        data.notes
    )

@router.get("/streak")
def get_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current streak"""
    service = CheckInService(db)
    return {"streak_days": service.get_streak(current_user.id)}

@router.get("/history", response_model=list[CheckInResponse])
def get_history(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get check-in history"""
    service = CheckInService(db)
    return service.get_checkin_history(current_user.id, days)

@router.get("/calendar/{year}/{month}")
def get_calendar(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get check-in calendar"""
    service = CheckInService(db)
    return service.get_checkin_calendar(current_user.id, year, month)
```

#### `api/v1/notifications.py`
```python
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationCreate, SubscriptionCreate
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("/subscribe")
async def subscribe(
    subscription: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register push subscription"""
    service = NotificationService(db)
    return await service.register_subscription(current_user.id, subscription.subscription)

@router.get("/vapid-public-key")
def get_vapid_key():
    """Get VAPID public key for client"""
    import os
    return {"public_key": os.getenv("VAPID_PUBLIC_KEY")}

@router.post("/test")
async def test_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send test notification"""
    service = NotificationService(db)
    notification = NotificationCreate(
        title="Test Notification",
        body="If you see this, notifications are working! 🎉",
        data={"type": "test"}
    )
    result = await service.send_notification(current_user.id, notification)
    return {"sent": result}
```

### 2. Pydantic Schemas

#### `schemas/checkin.py`
```python
from pydantic import BaseModel, Field
from datetime import date

class CheckInCreate(BaseModel):
    session_id: str
    mood: str | None = Field(None, description="How user felt after workout")
    notes: str | None = Field(None, max_length=500)

class CheckInResponse(BaseModel):
    id: str
    date: date
    streak_days: int
    completion_rate: float
    achievements_unlocked: list
    mood: str | None

    class Config:
        from_attributes = True
```

#### `schemas/notification.py`
```python
from pydantic import BaseModel

class SubscriptionCreate(BaseModel):
    subscription: dict

class NotificationCreate(BaseModel):
    title: str
    body: str
    data: dict | None = None
    actions: list | None = None
```

### 3. Frontend Implementation

#### `lib/notifications.ts`
```typescript
import { register } from 'register-service-worker';
import type { Registration } from 'workbox-navigation-preload';

const PUBLIC_VAPID_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || '';

// Convert base64 string to Uint8Array
function urlBase64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function subscribeToNotifications(): Promise<PushSubscription | null> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('Push notifications not supported');
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY),
    });

    // Send subscription to server
    await fetch('/api/v1/notifications/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subscription }),
    });

    return subscription;
  } catch (error) {
    console.error('Failed to subscribe:', error);
    return null;
  }
}

export async function requestNotificationPermission(): Promise<boolean> {
  if (!('Notification' in window)) {
    return false;
  }

  if (Notification.permission === 'granted') {
    return true;
  }

  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }

  return false;
}

export function onNotificationClick(callback: (data: any) => void) {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data.type === 'NOTIFICATION_CLICK') {
        callback(event.data.payload);
      }
    });
  }
}
```

#### `app/service-worker.ts`
```typescript
/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options: NotificationOptions = {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    vibrate: [200, 100, 200],
    data: data.data || {},
    actions: data.actions || [],
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const action = event.action;

  if (action === 'start') {
    // Open workout session
    event.waitUntil(
      self.clients.openWindow(`/workout/${event.notification.data.session_id}`)
    );
  } else if (action === 'reply') {
    // Open chat
    event.waitUntil(self.clients.openWindow('/messages'));
  } else {
    // Default: open app
    event.waitUntil(self.clients.openWindow('/'));
  }
});

export {};
```

#### `components/CheckInModal.tsx`
```typescript
'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { checkinApi } from '@/lib/api/checkin';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Flame, Star, Trophy } from 'lucide-react';

interface CheckInModalProps {
  open: boolean;
  onClose: () => void;
  sessionId: string;
}

export function CheckInModal({ open, onClose, sessionId }: CheckInModalProps) {
  const [mood, setMood] = useState<string | null>(null);
  const [notes, setNotes] = useState('');

  const checkinMutation = useMutation({
    mutationFn: (data: { mood: string; notes?: string }) =>
      checkinApi.create(sessionId, data),
    onSuccess: (result) => {
      // Show success with achievements
    },
  });

  const moods = [
    { value: 'great', emoji: '💪', label: 'Great' },
    { value: 'good', emoji: '👍', label: 'Good' },
    { value: 'okay', emoji: '😐', label: 'Okay' },
    { value: 'tired', emoji: '😫', label: 'Tired' },
    { value: 'pain', emoji: '🤕', label: 'Pain' },
  ];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Workout Complete! 🎉</DialogTitle>
        </DialogHeader>

        <div className="py-6">
          <p className="text-center text-muted-foreground mb-6">
            How are you feeling after this workout?
          </p>

          {/* Mood Selector */}
          <div className="flex justify-center gap-4 mb-6">
            {moods.map((m) => (
              <button
                key={m.value}
                onClick={() => setMood(m.value)}
                className={`flex flex-col items-center p-4 rounded-lg transition-colors ${
                  mood === m.value ? 'bg-primary text-primary-foreground' : 'bg-secondary'
                }`}
              >
                <span className="text-3xl mb-1">{m.emoji}</span>
                <span className="text-sm">{m.label}</span>
              </button>
            ))}
          </div>

          {/* Notes */}
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any notes about your workout? (optional)"
            className="w-full p-3 border rounded-lg resize-none"
            rows={3}
          />
        </div>

        {/* Achievements Preview */}
        {checkinMutation.data?.achievements_unlocked.length > 0 && (
          <div className="mb-6 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-yellow-600" />
              Achievements Unlocked!
            </h3>
            <div className="flex gap-2 flex-wrap">
              {checkinMutation.data.achievements_unlocked.map((a) => (
                <Badge key={a.id} variant="secondary">
                  {a.icon} {a.name}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Streak Display */}
        <div className="flex items-center justify-center gap-4 p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg mb-6">
          <Flame className="w-8 h-8 text-orange-500" />
          <div className="text-center">
            <div className="text-3xl font-bold text-orange-600">
              {checkinMutation.data?.streak_days || 0}
            </div>
            <div className="text-sm text-muted-foreground">Day Streak</div>
          </div>
        </div>

        <Button
          onClick={() => checkinMutation.mutate({ mood: mood!, notes })}
          disabled={!mood || checkinMutation.isPending}
          className="w-full"
          size="lg"
        >
          {checkinMutation.isPending ? 'Saving...' : 'Check In'}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
```

#### `lib/api/checkin.ts`
```typescript
import api from '@/lib/api';

export interface CheckIn {
  id: string;
  date: string;
  streak_days: number;
  completion_rate: number;
  achievements_unlocked: Array<{
    id: string;
    name: string;
    icon: string;
  }>;
  mood: string | null;
  notes: string | null;
}

export const checkinApi = {
  create: async (sessionId: string, data: {
    mood: string;
    notes?: string;
  }): Promise<CheckIn> => {
    const response = await api.post('/api/v1/checkin', {
      session_id: sessionId,
      ...data,
    });
    return response.data;
  },

  getStreak: async (): Promise<{ streak_days: number }> => {
    const response = await api.get('/api/v1/checkin/streak');
    return response.data;
  },

  getHistory: async (days = 30): Promise<CheckIn[]> => {
    const response = await api.get(`/api/v1/checkin/history?days=${days}`);
    return response.data;
  },

  getCalendar: async (year: number, month: number): Promise<Record<number, {
    completed: boolean;
    streak: number;
  }>> => {
    const response = await api.get(`/api/v1/checkin/calendar/${year}/${month}`);
    return response.data;
  },
};
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/notifications/subscribe` | Register push subscription |
| GET | `/api/v1/notifications/vapid-public-key` | Get VAPID public key |
| POST | `/api/v1/notifications/test` | Send test notification |
| POST | `/api/v1/checkin` | Create check-in |
| GET | `/api/v1/checkin/streak` | Get current streak |
| GET | `/api/v1/checkin/history` | Get check-in history |
| GET | `/api/v1/checkin/calendar/{year}/{month}` | Get calendar data |

## Technical Requirements

- Web Push API with VAPID
- Service Worker for background sync
- APScheduler for scheduled jobs
- Celery for async tasks (optional)

## Acceptance Criteria

- [ ] User can grant notification permission
- [ ] Push subscription registered successfully
- [ ] Workout reminders sent 30 min before
- [ ] Daily greetings delivered at set time
- [ ] Missed workout reminders sent
- [ ] Check-in modal shows after workout
- [ ] Streak calculated correctly
- [ ] Achievements unlock on milestones

## Notes

- Handle notification permission denial gracefully
- Show permission request at appropriate time
- Respect user's quiet hours
- Provide in-app notifications as fallback
