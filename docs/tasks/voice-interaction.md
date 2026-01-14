# Task: Voice Interaction

## Overview

Implement voice interaction features including ASR (Automatic Speech Recognition) and TTS (Text-to-Speech) for hands-free workout logging and AI coach communication.

## Dependencies

- Requires `workout-execution` to be completed

## Deliverables

### 1. Backend Implementation

#### `services/asr_service.py`
```python
import httpx
from app.config import settings

class ASRService:
    """FunASR service for speech recognition"""

    def __init__(self):
        self.base_url = settings.ASR_URL

    async def transcribe(self, audio_data: bytes, format: str = "wav") -> dict:
        """
        Transcribe audio to text using FunASR

        Args:
            audio_data: Raw audio bytes
            format: Audio format (wav, mp3, etc.)

        Returns:
            {"text": "transcribed text", "segments": [...]}
        """
        import io

        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"audio.{format}"

        files = {"audio": audio_file}
        data = {"language": "zh-CN"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/transcribe",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()

    async def transcribe_stream(self, audio_stream) -> dict:
        """Stream transcription for real-time feedback"""
        # Implementation for streaming transcription
        pass
```

#### `services/tts_service.py`
```python
import httpx
import base64
from app.config import settings

class TTSService:
    """ChatTTS/CosyVoice service for text-to-speech"""

    def __init__(self):
        self.base_url = settings.TTS_URL

    async def synthesize(
        self,
        text: str,
        voice: str = "female_coach",
        speed: float = 1.0,
        emotion: str = "neutral"
    ) -> bytes:
        """
        Convert text to speech audio

        Args:
            text: Text to synthesize
            voice: Voice profile
            speed: Speech speed multiplier
            emotion: Emotional tone

        Returns:
            Audio bytes (MP3 format)
        """
        payload = {
            "text": text,
            "voice": voice,
            "speed": speed,
            "emotion": emotion,
            "format": "mp3"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/synthesize",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            if "audio" in result:
                return base64.b64decode(result["audio"])

        raise Exception("TTS synthesis failed")

    async def get_available_voices(self) -> list:
        """Get available voice profiles"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/voices")
            return response.json()
```

#### `services/voice_coach_service.py`
```python
from app.services.llm import LLMService
from app.services.asr_service import ASRService
from app.services.tts_service import TTSService
from app.schemas.voice import VoiceInput, VoiceResponse

class VoiceCoachService:
    """Combined voice interaction service for workout coaching"""

    def __init__(self):
        self.llm = LLMService()
        self.asr = ASRService()
        self.tts = TTSService()

    async def process_voice_input(
        self,
        audio_data: bytes,
        context: dict,
        coach_style: str = "balanced"
    ) -> VoiceResponse:
        """
        Process user voice input and return audio response

        Args:
            audio_data: User's voice input
            context: Workout context (current exercise, last set, etc.)
            coach_style: Coach personality style

        Returns:
            VoiceResponse with transcribed text, parsed data, and audio response
        """
        # Step 1: Transcribe audio
        transcription = await self.asr.transcribe(audio_data)
        user_text = transcription["text"]

        # Step 2: Parse workout data from text
        parsed_data = self._parse_workout_log(user_text, context)

        # Step 3: Generate AI response
        ai_response = await self._generate_coach_response(
            user_text, parsed_data, context, coach_style
        )

        # Step 4: Synthesize speech
        response_audio = await self.tts.synthesize(
            ai_response["text"],
            emotion=ai_response.get("emotion", "neutral")
        )

        return VoiceResponse(
            transcript=user_text,
            parsed_data=parsed_data,
            response_text=ai_response["text"],
            response_audio=response_audio,
            suggestions=ai_response.get("suggestions", [])
        )

    def _parse_workout_log(self, text: str, context: dict) -> dict:
        """
        Parse workout data from transcribed text

        Examples:
        - "做了12个，感觉还行" -> {reps: 12, rpe: 7}
        - "60公斤，10个，有点累" -> {weight: 60, reps: 10, rpe: 8}
        - "太重了，减5公斤" -> {suggestion: "decrease_weight", amount: 5}
        """
        import re

        result = {}

        # Extract weight (kg, 公斤)
        weight_match = re.search(r'(\d+)\s*(?:kg|公斤|千克)', text)
        if weight_match:
            result["weight"] = int(weight_match.group(1))

        # Extract reps (个, 次)
        reps_match = re.search(r'(\d+)\s*(?:个|次|下)', text)
        if reps_match:
            result["reps"] = int(reps_match.group(1))

        # Extract RPE from feelings
        rpe_keywords = {
            "很轻松": 4, "还行": 6, "中等": 7, "有点累": 8,
            "很累": 9, "累死了": 10, "太重": 9, "太轻": 3
        }
        for keyword, rpe in rpe_keywords.items():
            if keyword in text:
                result["rpe"] = rpe
                break

        # Extract suggestions
        if "减" in text or "轻点" in text:
            result["suggestion"] = "decrease_weight"
        elif "加" in text or "重点" in text:
            result["suggestion"] = "increase_weight"
        elif "不想练" in text or "休息" in text:
            result["suggestion"] = "rest"
        elif "怎么做" in text or "教我" in text:
            result["suggestion"] = "show_instructions"

        return result

    async def _generate_coach_response(
        self,
        user_text: str,
        parsed_data: dict,
        context: dict,
        coach_style: str
    ) -> dict:
        """Generate AI coach response based on user input"""

        system_prompt = self._get_coach_system_prompt(coach_style)

        # Build context message
        context_info = f"""
Current exercise: {context.get('exercise_name', 'Unknown')}
Last set: {context.get('last_weight', 'N/A')}kg × {context.get('last_reps', 'N/A')} reps
Current set: {context.get('set_number', 1)} of {context.get('total_sets', 3)}
"""

        user_message = f"{context_info}\nUser said: {user_text}\n\nGenerate a brief, encouraging response in Chinese."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response_text = await self.llm.chat(messages, coach_style)

        # Determine emotion based on content
        emotion = "neutral"
        if any(word in response_text for word in ["太棒了", "很好", "优秀"]):
            emotion = "happy"
        elif any(word in response_text for word in ["加油", "坚持"]):
            emotion = "encouraging"

        return {
            "text": response_text,
            "emotion": emotion
        }

    def _get_coach_system_prompt(self, style: str) -> str:
        prompts = {
            "strict": "你是一位严格的健身教练。说话直接、简洁，不废话。要求用户严格执行计划。",
            "encouraging": "你是一位温暖鼓励的健身教练。说话温柔、正向，多用夸奖和鼓励。",
            "humorous": "你是一位幽默风趣的健身教练。说话轻松有趣，用幽默来激励用户。",
            "professional": "你是一位专业科学的健身教练。说话客观、专业，解释训练原理。",
            "balanced": "你是一位平衡的健身教练。根据情况灵活调整风格，既专业又有亲和力。"
        }
        return prompts.get(style, prompts["balanced"])

    async def start_continuous_session(self, user_id: str, session_id: str) -> str:
        """Start a continuous voice conversation session (phone call mode)"""
        # Create a WebSocket session for continuous interaction
        # Returns session ID for WebSocket connection
        pass

    async def process_continuous_audio(
        self,
        session_id: str,
        audio_chunk: bytes,
        is_final: bool = False
    ) -> dict:
        """Process audio chunk in continuous mode"""
        # Implementation for streaming audio processing
        pass
```

#### `api/v1/voice.py`
```python
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.voice import VoiceResponse
from app.services.voice_coach_service import VoiceCoachService

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/process", response_model=VoiceResponse)
async def process_voice(
    audio: UploadFile,
    context: dict,
    coach_style: str = "balanced",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process voice input and return audio response (press-and-hold mode)"""
    service = VoiceCoachService()
    audio_data = await audio.read()
    return await service.process_voice_input(audio_data, context, coach_style)

@router.post("/session/start")
async def start_continuous_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start continuous voice session (phone call mode)"""
    service = VoiceCoachService()
    session_ws_id = await service.start_continuous_session(current_user.id, session_id)
    return {"session_id": session_ws_id, "ws_url": f"ws://localhost:8000/voice/{session_ws_id}"}

@router.get("/voices")
async def get_available_voices():
    """Get available TTS voices"""
    from app.services.tts_service import TTSService
    service = TTSService()
    return await service.get_available_voices()
```

### 2. WebSocket for Continuous Mode

#### `api/websocket/voice.py`
```python
from fastapi import WebSocket, WebSocketDisconnect
from app.services.voice_coach_service import VoiceCoachService
import json

async def websocket_voice_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    service = VoiceCoachService()

    try:
        while True:
            # Receive audio chunk
            data = await websocket.receive_json()
            audio_data = base64.b64decode(data.get("audio", ""))
            is_final = data.get("final", False)

            # Process audio
            result = await service.process_continuous_audio(
                session_id, audio_data, is_final
            )

            # Send response
            await websocket.send_json(result)

    except WebSocketDisconnect:
        print(f"Voice session {session_id} disconnected")
```

### 3. Frontend Implementation

#### `components/VoiceButton.tsx`
```typescript
'use client';

import { useState, useRef } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { voiceApi } from '@/lib/api/voice';
import { useWorkoutStore } from '@/stores/workout';

interface VoiceButtonProps {
  context: {
    exercise_name: string;
    last_weight?: number;
    last_reps?: number;
    set_number: number;
    total_sets: number;
  };
  onResult?: (data: { weight?: number; reps?: number; rpe?: number }) => void;
}

export function VoiceButton({ context, onResult }: VoiceButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to access microphone:', err);
    }
  };

  const stopRecording = async () => {
    if (!mediaRecorderRef.current) return;

    mediaRecorderRef.current.stop();
    setIsRecording(false);
    setIsProcessing(true);

    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const audioFile = new File([audioBlob], 'voice.webm', { type: 'audio/webm' });

    try {
      const result = await voiceApi.processVoice(audioFile, context);

      setTranscript(result.transcript);
      onResult?.(result.parsed_data);

      // Play audio response
      if (result.response_audio) {
        await playAudioResponse(result.response_audio);
      }
    } catch (err) {
      console.error('Voice processing failed:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const playAudioResponse = async (audioBase64: string) => {
    const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
    await audio.play();
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <Button
        size="lg"
        className={`w-24 h-24 rounded-full ${
          isRecording ? 'bg-destructive' : 'bg-primary'
        }`}
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        disabled={isProcessing}
      >
        {isProcessing ? (
          <Loader2 className="w-10 h-10 animate-spin" />
        ) : isRecording ? (
          <MicOff className="w-10 h-10" />
        ) : (
          <Mic className="w-10 h-10" />
        )}
      </Button>
      <p className="text-sm text-muted-foreground">
        {isRecording ? 'Recording...' : isProcessing ? 'Processing...' : 'Hold to speak'}
      </p>
      {transcript && (
        <p className="text-sm text-center mt-2">"{transcript}"</p>
      )}
    </div>
  );
}
```

#### `components/VoiceCallModal.tsx`
```typescript
'use client';

import { useState, useEffect, useRef } from 'react';
import { Phone, PhoneOff, Volume2, Mic, MicOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent } from '@/components/ui/dialog';

export function VoiceCallModal({
  open,
  onClose,
  sessionId,
}: {
  open: boolean;
  onClose: () => void;
  sessionId: string;
}) {
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isConnected) {
      interval = setInterval(() => {
        setCallDuration((d) => d + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isConnected]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const startCall = async () => {
    try {
      // Start voice session
      const response = await fetch(`/api/v1/voice/session/start?session_id=${sessionId}`, {
        method: 'POST',
      });
      const { ws_url } = await response.json();

      // Connect WebSocket
      const ws = new WebSocket(ws_url);
      wsRef.current = ws;

      ws.onopen = () => setIsConnected(true);

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.audio) {
          setAiSpeaking(true);
          const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);
          audio.onended = () => setAiSpeaking(false);
          await audio.play();
        }
        if (data.transcript) {
          // Display AI transcript
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
      };

      // Start audio capture
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event) => {
        if (ws.readyState === WebSocket.OPEN && !isMuted) {
          const audioBase64 = await blobToBase64(event.data);
          ws.send(JSON.stringify({ audio: audioBase64 }));
        }
      };

      mediaRecorder.start(1000); // Send chunks every second
    } catch (err) {
      console.error('Failed to start call:', err);
    }
  };

  const endCall = () => {
    wsRef.current?.close();
    mediaRecorderRef.current?.stop();
    onClose();
  };

  useEffect(() => {
    if (open && !isConnected) {
      startCall();
    }
    return () => {
      wsRef.current?.close();
      mediaRecorderRef.current?.stop();
    };
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <div className="flex flex-col items-center py-8">
          {/* AI Avatar */}
          <div className={`w-32 h-32 rounded-full bg-primary/10 flex items-center justify-center mb-6 ${aiSpeaking ? 'animate-pulse' : ''}`}>
            <span className="text-4xl">🏋️</span>
          </div>

          {/* Status */}
          <h2 className="text-xl font-semibold mb-2">
            {isConnected ? 'Connected to Coach' : 'Connecting...'}
          </h2>
          <p className="text-muted-foreground mb-6">{formatTime(callDuration)}</p>

          {/* Transcript Display */}
          {aiSpeaking && (
            <div className="w-full p-4 bg-secondary rounded-lg mb-6">
              <p className="text-center text-sm">Coach is speaking...</p>
            </div>
          )}

          {/* Controls */}
          <div className="flex gap-4">
            <Button
              variant="outline"
              size="lg"
              className="rounded-full w-16 h-16"
              onClick={() => setIsMuted(!isMuted)}
            >
              {isMuted ? <MicOff /> : <Mic />}
            </Button>
            <Button
              variant="destructive"
              size="lg"
              className="rounded-full w-20 h-20"
              onClick={endCall}
            >
              <PhoneOff />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
```

#### `lib/api/voice.ts`
```typescript
import api from '@/lib/api';

export interface VoiceProcessResult {
  transcript: string;
  parsed_data: {
    weight?: number;
    reps?: number;
    rpe?: number;
    suggestion?: string;
  };
  response_text: string;
  response_audio: string; // base64 encoded mp3
  suggestions: string[];
}

export const voiceApi = {
  processVoice: async (
    audioFile: File,
    context: {
      exercise_name: string;
      last_weight?: number;
      last_reps?: number;
      set_number: number;
      total_sets: number;
    }
  ): Promise<VoiceProcessResult> => {
    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('context', JSON.stringify(context));

    const response = await api.post('/api/v1/voice/process', formData);
    return response.data;
  },

  startSession: async (sessionId: string): Promise<{ session_id: string; ws_url: string }> => {
    const response = await api.post(`/api/v1/voice/session/start?session_id=${sessionId}`);
    return response.data;
  },

  getVoices: async (): Promise<Array<{ id: string; name: string; language: string }>> => {
    const response = await api.get('/api/v1/voice/voices');
    return response.data;
  },
};
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/voice/process` | Process voice input (press-and-hold) |
| POST | `/api/v1/voice/session/start` | Start continuous session |
| WS | `/voice/{session_id}` | WebSocket for continuous audio |
| GET | `/api/v1/voice/voices` | Get available TTS voices |

## Technical Requirements

- FunASR for ASR (Paraformer model)
- ChatTTS or CosyVoice for TTS
- WebSocket for continuous mode
- Web Audio API for playback
- MediaRecorder API for capture

## Acceptance Criteria

- [ ] Press-and-hold button records and transcribes
- [ ] Weight/reps/RPE extracted from speech
- [ ] AI responds with voice output
- [ ] Continuous call mode works
- [ ] Microphone permissions handled
- [ ] Audio plays automatically
- [ ] Mute button works in call mode

## Notes

- Handle different audio formats across browsers
- Add visual feedback for recording state
- Consider offline mode with local recognition
- Test on mobile devices primarily
