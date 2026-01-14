# Task: AI Coach with Style System

## Overview

Implement the AI coach system with multiple personality styles, daily greetings, progress tracking inquiries, and adaptive responses.

## Dependencies

- Requires `voice-interaction` to be completed
- Requires `notification-checkin` to be completed

## Deliverables

### 1. Backend Implementation

#### `services/coach_service.py`
```python
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.workout import WorkoutSession, CheckIn
from app.models.message import AIMessage
from app.services.llm import LLMService
from app.schemas.coach import CoachMessageRequest, CoachResponse

class CoachService:
    """AI Coach service with personality styles"""

    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService()

        # Coach style configurations
        self.styles = {
            "strict": {
                "name": "Hardcore Coach",
                "system": """你是一位严格的硬核健身教练。你的特点是：
- 说话直接、简洁，不废话
- 对用户要求严格，不轻易接受借口
- 强调纪律和坚持
- 用词有力，有时会用激将法

例子：
"累？累就是进步的开始！别找借口，最后一组！"
"别跟我谈感受，完成计划才是硬道理。"
- Keep responses brief and motivating""",
            },
            "encouraging": {
                "name": "Supportive Coach",
                "system": """你是一位温暖鼓励的健身教练。你的特点是：
- 说话温柔、正向，充满鼓励
- 关注用户的感受和状态
- 用夸奖和认可来激励
- 理解用户的困难，但温柔地推动

例子：
"辛苦了！你今天的表现很棒，我为你的坚持感到骄傲！"
"累是很正常的，你已经做得很棒了，我们一起慢慢来好吗？"
- Always be positive and supportive""",
            },
            "humorous": {
                "name": "Fun Coach",
                "system": """你是一位幽默风趣的健身教练。你的特点是：
- 说话轻松有趣，经常用幽默
- 用玩笑和梗来活跃气氛
- 不让健身变得沉重
- 偶尔调侃但保持善意

例子：
"累了？想想你办卡时交的钱，那可是真金白银啊！"
"今天练腿？祝你明天上下楼梯像企鹅一样可爱～"
- Use humor to make fitness fun""",
            },
            "professional": {
                "name": "Science Coach",
                "system": """你是一位专业科学的健身教练。你的特点是：
- 说话客观、专业，基于科学原理
- 解释训练方法和背后的原理
- 用数据和事实说话
- 给出具体的技术指导

例子：
"根据渐进超负荷原理，建议下一组增加5%重量。"
"你的RPE为8，处于有效的训练强度区间。"
- Provide scientific, evidence-based advice""",
            },
            "balanced": {
                "name": "Adaptive Coach",
                "system": """你是一位平衡的健身教练。你的特点是：
- 根据情况灵活调整风格
- 既专业又有亲和力
- 知道什么时候严格，什么时候温和
- 适应用户的状态和需求

例子：
- Adapt your response style based on context
- Be professional yet approachable
- Balance science with motivation""",
            },
        }

    async def send_daily_greeting(
        self, user_id: str, greeting_type: str = "check_in"
    ) -> AIMessage:
        """Send daily greeting to user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        # Build context
        context = await self._build_user_context(user)
        coach_style = user.coach_style or "balanced"

        # Generate greeting
        greeting = await self._generate_greeting(
            user, context, greeting_type, coach_style
        )

        # Save message
        message = AIMessage(
            user_id=user_id,
            type="daily_greeting",
            content=greeting["text"],
            coach_style=coach_style
        )
        self.db.add(message)
        self.db.commit()

        return message

    async def chat(
        self, user_id: str, request: CoachMessageRequest
    ) -> CoachResponse:
        """Handle chat interaction with AI coach"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        coach_style = request.coach_style or user.coach_style or "balanced"

        # Build conversation context
        context = await self._build_conversation_context(user, request)

        # Generate response
        response = await self._generate_response(
            user, context, request.message, coach_style
        )

        # Save message
        message = AIMessage(
            user_id=user_id,
            type="workout_feedback" if context.get("in_workout") else "daily_greeting",
            content=response["text"],
            coach_style=coach_style
        )
        self.db.add(message)
        self.db.commit()

        return CoachResponse(
            text=response["text"],
            suggestions=response.get("suggestions", []),
            mood=response.get("mood", "neutral"),
            requires_action=response.get("requires_action")
        )

    async def progress_inquiry(self, user_id: str) -> CoachResponse:
        """Send progress inquiry message"""
        user = self.db.query(User).filter(User.id == user_id).first()

        # Get recent activity
        recent_sessions = (
            self.db.query(WorkoutSession)
            .filter(WorkoutSession.user_id == user_id)
            .order_by(WorkoutSession.actual_date.desc())
            .limit(5)
            .all()
        )

        context = {
            "recent_sessions": [
                {
                    "theme": s.theme,
                    "date": s.actual_date.isoformat() if s.actual_date else None,
                    "status": s.status
                }
                for s in recent_sessions
            ]
        }

        # Generate inquiry
        prompt = self._build_progress_inquiry_prompt(user, context)
        response_text = await self.llm.chat(
            [{"role": "user", "content": prompt}],
            user.coach_style or "balanced"
        )

        return CoachResponse(
            text=response_text,
            suggestions=[
                {"action": "update_goal", "text": "Update Goal"},
                {"action": "log_workout", "text": "Log Workout"},
                {"action": "rest_day", "text": "Take Rest Day"}
            ]
        )

    async def _build_user_context(self, user: User) -> dict:
        """Build rich context about the user"""
        # Get current plan
        current_plan = (
            self.db.query(WorkoutPlan)
            .filter(
                WorkoutPlan.user_id == user.id,
                WorkoutPlan.status == "active"
            )
            .first()
        )

        # Get recent check-ins
        recent_checkins = (
            self.db.query(CheckIn)
            .filter(CheckIn.user_id == user.id)
            .order_by(CheckIn.date.desc())
            .limit(7)
            .all()
        )

        # Get today's session
        today = date.today()
        today_session = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user.id,
                WorkoutSession.scheduled_date == today
            )
            .first()
        )

        # Calculate stats
        total_workouts = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user.id,
                WorkoutSession.status == "completed"
            )
            .count()
        )

        avg_mood = "neutral"
        if recent_checkins:
            moods = [c.mood for c in recent_checkins if c.mood]
            if moods:
                avg_mood = max(set(moods), key=moods.count)

        return {
            "user": {
                "nickname": user.nickname,
                "goal": user.primary_goal,
                "level": user.fitness_level,
                "streak": recent_checkins[0].streak_days if recent_checkins else 0,
                "avg_mood": avg_mood,
                "total_workouts": total_workouts,
            },
            "plan": {
                "name": current_plan.name if current_plan else None,
                "goal": current_plan.goals if current_plan else None,
            },
            "today_session": {
                "theme": today_session.theme if today_session else None,
                "status": today_session.status if today_session else None,
                "time": today_session.scheduled_date.isoformat() if today_session else None,
            }
        }

    async def _build_conversation_context(
        self, user: User, request: CoachMessageRequest
    ) -> dict:
        """Build context for chat response"""
        context = await self._build_user_context(user)
        context["in_workout"] = request.session_id is not None
        context["current_exercise"] = request.current_exercise
        context["last_set"] = request.last_set
        return context

    async def _generate_greeting(
        self, user: User, context: dict, greeting_type: str, coach_style: str
    ) -> dict:
        """Generate personalized greeting"""
        style_prompt = self.styles[coach_style]["system"]

        base_prompts = {
            "check_in": f"""
生成每日问候，询问用户训练情况。

用户信息：
- 昵称：{context['user']['nickname']}
- 目标：{context['user']['goal']}
- 连续训练：{context['user']['streak']}天
- 最近心情：{context['user']['avg_mood']}

生成一句简短的问候语（20字以内），引导用户分享今天的训练情况。
""",
            "pre_workout": f"""
生成训练前鼓励语。

用户信息：
- 昵称：{context['user']['nickname']}
- 今日训练：{context['today_session']['theme']}

生成简短的鼓励语（20字以内），激励用户开始训练。
""",
            "post_workout": f"""
生成训练后问候语。

用户信息：
- 昵称：{context['user']['nickname']}
- 今日训练：{context['today_session']['theme']}

生成简短的问候语（20字以内），询问训练感受。
""",
            "missed": f"""
生成唤醒提醒语。

用户信息：
- 昵称：{context['user']['nickname']}
- 连续中断：{context['user']['streak']}天

生成提醒语（30字以内），鼓励用户回归训练。
"""
        }

        user_prompt = base_prompts.get(greeting_type, base_prompts["check_in"])

        messages = [
            {"role": "system", "content": style_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response_text = await self.llm.chat(messages, coach_style)

        return {"text": response_text.strip()}

    async def _generate_response(
        self, user: User, context: dict, user_message: str, coach_style: str
    ) -> dict:
        """Generate AI response to user message"""
        style_prompt = self.styles[coach_style]["system"]

        # Analyze user intent
        intent = self._analyze_intent(user_message)

        # Build context for LLM
        context_str = self._format_context_for_llm(context)

        user_prompt = f"""
用户说："{user_message}"

上下文：
{context_str}

检测到的意图：{intent}

生成回复（50字以内），保持{self.styles[coach_style]['name']}的风格。
"""

        messages = [
            {"role": "system", "content": style_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Include conversation history if available
        if context.get("conversation_history"):
            messages = context["conversation_history"] + messages

        response_text = await self.llm.chat(messages, coach_style)

        # Determine suggestions based on intent
        suggestions = self._get_suggestions_for_intent(intent, context)

        return {
            "text": response_text.strip(),
            "suggestions": suggestions,
            "mood": self._determine_response_mood(response_text)
        }

    def _analyze_intent(self, message: str) -> str:
        """Analyze user message intent"""
        message_lower = message.lower()

        intent_patterns = {
            "tired": ["累", " tired", "疲劳", "不想练", "没劲"],
            "progress": ["进步", "效果", " results", "变化"],
            "injury": ["疼", "伤", " injury", "痛", "不舒服"],
            "question": ["怎么", "如何", " what", " how", "?", "？"],
            "complaint": ["难", "重", " hard", "太累了"],
            "positive": ["好", "棒", " great", "可以", "还行"],
            "skip": ["不练", "休息", " skip", "今天算了"],
        }

        for intent, patterns in intent_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                return intent

        return "general"

    def _format_context_for_llm(self, context: dict) -> str:
        """Format context for LLM prompt"""
        parts = []

        if context.get("user"):
            u = context["user"]
            parts.append(f"用户：{u['nickname']}，目标：{u['goal']}")

        if context.get("today_session"):
            s = context["today_session"]
            if s["theme"]:
                parts.append(f"今日训练：{s['theme']}")

        if context.get("current_exercise"):
            parts.append(f"当前动作：{context['current_exercise']}")

        if context.get("last_set"):
            ls = context["last_set"]
            parts.append(f"上一组：{ls.get('weight', 0)}kg × {ls.get('reps', 0)}次")

        return "\n".join(parts)

    def _get_suggestions_for_intent(self, intent: str, context: dict) -> list:
        """Get suggested actions based on intent"""
        suggestions_map = {
            "tired": [
                {"action": "continue", "text": "继续训练"},
                {"action": "reduce_intensity", "text": "降低强度"},
                {"action": "end_workout", "text": "结束训练"}
            ],
            "injury": [
                {"action": "show_alternative", "text": "替换动作"},
                {"action": "skip_exercise", "text": "跳过此动作"},
                {"action": "end_workout", "text": "停止训练"}
            ],
            "question": [
                {"action": "explain", "text": "详细解释"},
                {"action": "show_video", "text": "视频教学"}
            ],
            "skip": [
                {"action": "confirm_rest", "text": "确认休息"},
                {"action": "motivate", "text": "再坚持一下"}
            ],
        }

        return suggestions_map.get(intent, [
            {"action": "continue", "text": "继续训练"}
        ])

    def _determine_response_mood(self, response: str) -> str:
        """Determine emotional tone of response"""
        positive_words = ["太棒了", "很好", "优秀", "骄傲", "amazing"]
        encouraging_words = ["加油", "坚持", "可以", "come on"]
        concerned_words = ["注意", "小心", "休息", "恢复"]

        response_lower = response.lower()

        if any(word in response_lower for word in positive_words):
            return "happy"
        elif any(word in response_lower for word in encouraging_words):
            return "encouraging"
        elif any(word in response_lower for word in concerned_words):
            return "concerned"

        return "neutral"

    def _build_progress_inquiry_prompt(self, user: User, context: dict) -> str:
        """Build prompt for progress inquiry"""
        sessions = context.get("recent_sessions", [])

        if not sessions:
            return f"你好{user.nickname}！最近好像没看到你训练，一切都好吗？"

        last_session = sessions[0]
        days_since = (date.today() - last_session["date"].date()).days if last_session["date"] else 999

        if days_since <= 1:
            return f"{user.nickname}，昨天的训练感觉怎么样？有什么想分享的吗？"
        elif days_since <= 3:
            return f"{user.nickname}，最近训练还好吗？继续保持！"
        else:
            return f"{user.nickname}，好久不见！是不是遇到什么困难了？需要帮忙吗？"

    def get_available_styles(self) -> list:
        """Get available coach styles"""
        return [
            {
                "id": key,
                "name": value["name"],
                "description": value["system"].split("\n")[0]
            }
            for key, value in self.styles.items()
        ]
```

#### `api/v1/coach.py`
```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.coach import CoachMessageRequest, CoachResponse
from app.services.coach_service import CoachService

router = APIRouter(prefix="/coach", tags=["coach"])

@router.post("/chat", response_model=CoachResponse)
async def chat(
    request: CoachMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat with AI coach"""
    service = CoachService(db)
    return await service.chat(current_user.id, request)

@router.post("/greeting")
async def send_greeting(
    greeting_type: str = "check_in",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send daily greeting"""
    service = CoachService(db)
    message = await service.send_daily_greeting(current_user.id, greeting_type)
    return {"message": message.content, "type": message.type}

@router.get("/inquiry")
async def progress_inquiry(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get progress inquiry message"""
    service = CoachService(db)
    return await service.progress_inquiry(current_user.id)

@router.get("/styles")
def get_styles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available coach styles"""
    service = CoachService(db)
    return service.get_available_styles()

@router.patch("/style")
def update_style(
    style: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update coach style preference"""
    if style not in ["strict", "encouraging", "humorous", "professional", "balanced"]:
        raise HTTPException(400, "Invalid coach style")

    current_user.coach_style = style
    db.commit()
    return {"style": style}
```

### 2. Pydantic Schemas

#### `schemas/coach.py`
```python
from pydantic import BaseModel, Field
from typing import Optional

class CoachMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    current_exercise: Optional[str] = None
    last_set: Optional[dict] = None
    coach_style: Optional[str] = None

class CoachSuggestion(BaseModel):
    action: str
    text: str

class CoachResponse(BaseModel):
    text: str
    suggestions: list[CoachSuggestion] = []
    mood: str = "neutral"
    requires_action: Optional[dict] = None
```

### 3. Frontend Implementation

#### `components/CoachChat.tsx`
```typescript
'use client';

import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { coachApi } from '@/lib/api/coach';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: Array<{ action: string; text: string }>;
}

interface CoachChatProps {
  sessionId?: string;
  currentExercise?: string;
  lastSet?: { weight?: number; reps?: number };
}

export function CoachChat({ sessionId, currentExercise, lastSet }: CoachChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hey! Ready for your workout today?',
    },
  ]);
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      coachApi.chat({
        message,
        session_id: sessionId,
        current_exercise: currentExercise,
        last_set: lastSet,
      }),
    onSuccess: (response) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.text,
          suggestions: response.suggestions,
        },
      ]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;

    setMessages((prev) => [...prev, { role: 'user', content: input }]);
    const message = input;
    setInput('');
    chatMutation.mutate(message);
  };

  const handleSuggestion = (action: string, text: string) => {
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    chatMutation.mutate(text);
  };

  return (
    <Card className="flex flex-col h-[500px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <Bot className="w-5 h-5" />
              </div>
            )}
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary'
              }`}
            >
              <p>{msg.content}</p>
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                <User className="w-5 h-5" />
              </div>
            )}
          </div>
        ))}

        {/* Suggestions */}
        {messages[messages.length - 1]?.suggestions && (
          <div className="flex gap-2 flex-wrap ml-11">
            {messages[messages.length - 1].suggestions?.map((s) => (
              <Button
                key={s.action}
                variant="outline"
                size="sm"
                onClick={() => handleSuggestion(s.action, s.text)}
              >
                {s.text}
              </Button>
            ))}
          </div>
        )}

        {chatMutation.isPending && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <Bot className="w-5 h-5" />
            </div>
            <div className="bg-secondary rounded-2xl px-4 py-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-100" />
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type a message..."
            disabled={chatMutation.isPending}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || chatMutation.isPending}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
```

#### `lib/api/coach.ts`
```typescript
import api from '@/lib/api';

export interface CoachMessageRequest {
  message: string;
  session_id?: string;
  current_exercise?: string;
  last_set?: { weight?: number; reps?: number };
  coach_style?: string;
}

export interface CoachSuggestion {
  action: string;
  text: string;
}

export interface CoachResponse {
  text: string;
  suggestions: CoachSuggestion[];
  mood: 'neutral' | 'happy' | 'encouraging' | 'concerned';
  requires_action?: Record<string, unknown>;
}

export interface CoachStyle {
  id: string;
  name: string;
  description: string;
}

export const coachApi = {
  chat: async (request: CoachMessageRequest): Promise<CoachResponse> => {
    const response = await api.post('/api/v1/coach/chat', request);
    return response.data;
  },

  sendGreeting: async (greetingType = 'check_in') => {
    const response = await api.post(`/api/v1/coach/greeting?greeting_type=${greetingType}`);
    return response.data;
  },

  getInquiry: async (): Promise<CoachResponse> => {
    const response = await api.get('/api/v1/coach/inquiry');
    return response.data;
  },

  getStyles: async (): Promise<CoachStyle[]> => {
    const response = await api.get('/api/v1/coach/styles');
    return response.data;
  },

  updateStyle: async (style: string): Promise<{ style: string }> => {
    const response = await api.patch('/api/v1/coach/style', null, {
      params: { style },
    });
    return response.data;
  },
};
```

#### `components/CoachStyleSelector.tsx`
```typescript
'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { coachApi } from '@/lib/api/coach';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Check } from 'lucide-react';

const styleIcons = {
  strict: '💪',
  encouraging: '🤗',
  humorous: '😄',
  professional: '📊',
  balanced: '⚖️',
};

export function CoachStyleSelector() {
  const [selectedStyle, setSelectedStyle] = useState<string>('balanced');

  const { data: styles } = useQuery({
    queryKey: ['coach-styles'],
    queryFn: coachApi.getStyles,
  });

  const styleMutation = useMutation({
    mutationFn: coachApi.updateStyle,
    onSuccess: (data) => {
      setSelectedStyle(data.style);
    },
  });

  if (!styles) return null;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Choose Your Coach Style</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {styles.map((style) => (
          <button
            key={style.id}
            onClick={() => styleMutation.mutate(style.id)}
            className={`p-4 rounded-lg border-2 text-left transition-all hover:shadow-md ${
              selectedStyle === style.id
                ? 'border-primary bg-primary/5'
                : 'border-border'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <span className="text-2xl">{styleIcons[style.id as keyof typeof styleIcons]}</span>
              {selectedStyle === style.id && (
                <Check className="w-5 h-5 text-primary" />
              )}
            </div>
            <h4 className="font-semibold">{style.name}</h4>
            <p className="text-sm text-muted-foreground mt-1">{style.description}</p>
          </button>
        ))}
      </div>
    </Card>
  );
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/coach/chat` | Chat with AI coach |
| POST | `/api/v1/coach/greeting` | Send daily greeting |
| GET | `/api/v1/coach/inquiry` | Get progress inquiry |
| GET | `/api/v1/coach/styles` | Get available styles |
| PATCH | `/api/v1/coach/style` | Update coach style |

## Technical Requirements

- LLM: Qwen-2.5-14B-Instruct
- Style-specific system prompts
- Context-aware responses
- Conversation history tracking

## Acceptance Criteria

- [ ] All 5 coach styles work correctly
- [ ] Daily greetings are personalized
- [ ] Chat responses consider context
- [ ] Suggestions match user intent
- [ ] Style can be changed by user
- [ ] Progress inquiries are timely
- [ ] Tone matches selected style

## Notes

- Coach styles should feel distinct
- Keep responses concise for mobile
- Support voice input integration
- Handle edge cases gracefully
