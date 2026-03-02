from fastapi import FastAPI, File, UploadFile, Depends, Form, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os
import shutil
import redis.asyncio as redis
import json
import asyncio
from typing import Optional, List, Dict

# --- Web Socket & Redis Setup ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

manager = ConnectionManager()

USE_REDIS = False
try:
    # Use sync redis for check
    import redis as sync_redis
    r_check = sync_redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=1)
    if r_check.ping():
        USE_REDIS = True
        print("Redis detected. Using Celery + Redis Pub/Sub.")
except Exception as e:
    print(f"Redis not detected ({e}). Using In-Memory Fallback.")
    USE_REDIS = False

def background_process_wrapper(file_path, thread_id, log_id, client_id, loop):
    """Wrapper to run sync task in thread and notify async websocket on main loop"""
    from backend.tasks import process_voice_upload_internal
    result = process_voice_upload_internal(file_path, thread_id, log_id, client_id)
    
    if client_id:
        async def notify():
            message = {
                "type": "task_completed",
                "log_id": log_id,
                "status": "completed" if "error" not in result else "failed",
                **result
            }
            await manager.send_personal_message(json.dumps(message), client_id)
        
        asyncio.run_coroutine_threadsafe(notify(), loop)

try:
    from backend.database import get_db, engine
    from backend.models import Base, WorkoutLog, User, TrainingPlan
    from backend.ai_service import analyze_workout, transcribe_audio, analyze_image, generate_speech, generate_workout_plan
    from backend.agent.graph import run_agent
    from backend.auth import create_access_token, get_current_user, get_current_user_optional, verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
    from backend.tasks import process_voice_upload_task
except ImportError:
    from database import get_db, engine
    from models import Base, WorkoutLog, User, TrainingPlan
    from ai_service import analyze_workout, transcribe_audio, analyze_image, generate_speech, generate_workout_plan
    from agent.graph import run_agent
    from auth import create_access_token, get_current_user, get_current_user_optional, verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
    from tasks import process_voice_upload_task
from datetime import timedelta
from typing import Optional

# Create tables if not handled by Alembic (optional, but good for quick dev)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bod - Mock Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(ROOT, "..", "frontend")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/register")
def register_user(username: str = Form(...), password: str = Form(...), email: str = Form(None), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}

@app.post("/api/v1/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/voice")
async def voice_upload(
    file: UploadFile = File(...),
    thread_id: str = Form("default"),
    client_id: str = Form(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # 1. Save uploaded file
    tmp_path = os.path.join(ROOT, "uploads")
    os.makedirs(tmp_path, exist_ok=True)
    file_path = os.path.join(tmp_path, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Determine User
    if current_user:
        user = current_user
    else:
        # Create a Guest User if not exists (fallback)
        user = db.query(User).filter(User.username == "guest").first()
        if not user:
            user = User(username="guest", email="guest@example.com")
            db.add(user)
            db.commit()
            db.refresh(user)

    # 4. Create Initial Log Entry (Processing)
    new_log = WorkoutLog(
        user_id=user.id,
        audio_path=file_path,
        status="processing",
        raw_log="Processing audio...",
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    # 5. Dispatch Task (Async)
    if USE_REDIS:
        try:
            process_voice_upload_task.delay(file_path, thread_id, new_log.id, client_id)
        except Exception as e:
            print(f"Celery Dispatch Error: {e}")
            # Fallback if dispatch fails
            loop = asyncio.get_running_loop()
            background_tasks.add_task(background_process_wrapper, file_path, thread_id, new_log.id, client_id, loop)
    else:
        # Fallback: Run in background thread and notify via memory manager
        loop = asyncio.get_running_loop()
        background_tasks.add_task(background_process_wrapper, file_path, thread_id, new_log.id, client_id, loop)

    return JSONResponse({
        "id": new_log.id,
        "filename": file.filename,
        "status": "processing",
        "message": "Upload successful, processing started."
    })

@app.get("/api/v1/logs")
async def get_logs(current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    if current_user:
        logs = db.query(WorkoutLog).filter(WorkoutLog.user_id == current_user.id).order_by(WorkoutLog.created_at.desc()).all()
    else:
        # Fallback to guest logs or all logs? 
        # Better to return guest logs to avoid leaking user data
        guest_user = db.query(User).filter(User.username == "guest").first()
        if guest_user:
            logs = db.query(WorkoutLog).filter(WorkoutLog.user_id == guest_user.id).order_by(WorkoutLog.created_at.desc()).all()
        else:
            logs = []
    return logs

@app.post("/api/v1/image")
async def image_upload(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    # 1. Save uploaded file
    tmp_path = os.path.join(ROOT, "uploads")
    os.makedirs(tmp_path, exist_ok=True)
    file_path = os.path.join(tmp_path, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Analyze Image
    analysis_result = analyze_image(file_path)
    
    # 3. Determine User
    if current_user:
        user = current_user
    else:
        user = db.query(User).filter(User.username == "guest").first()
        if not user:
            user = User(username="guest", email="guest@example.com")
            db.add(user)
            db.commit()
            db.refresh(user)
        
    # 4. Save to DB (Store as a log entry)
    new_log = WorkoutLog(
        user_id=user.id,
        image_path=file_path, # Store image path
        transcript=None,
        raw_log=f"[Image Upload] {file.filename}",
        feedback=analysis_result.get("usage_tips") or analysis_result.get("feedback"),
        exercise=analysis_result.get("exercise"),
        # Other fields might be null for image
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return JSONResponse({
        "id": new_log.id,
        "filename": file.filename,
        "equipment": analysis_result.get("equipment"),
        "exercise": new_log.exercise,
        "feedback": new_log.feedback
    })

@app.get("/api/v1/stats/progress")
async def get_progress_stats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get progress statistics (weight/reps over time) grouped by exercise.
    """
    if current_user:
        user = current_user
    else:
        # Fallback to guest
        user = db.query(User).filter(User.username == "guest").first()
        if not user:
            return {}

    # Query all completed logs for the user with exercise data
    logs = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == user.id,
        WorkoutLog.status == "completed",
        WorkoutLog.exercise.isnot(None)
    ).order_by(WorkoutLog.created_at.asc()).all()

    # Group by exercise
    stats = {}
    for log in logs:
        exercise = log.exercise.strip() # Normalize
        if not exercise:
            continue
        
        if exercise not in stats:
            stats[exercise] = []
        
        stats[exercise].append({
            "date": log.created_at.isoformat(),
            "weight": log.weight,
            "reps": log.reps,
            "sets": log.sets
        })
    
    return stats

@app.post("/api/v1/plan/generate")
async def generate_plan(
    goal: str = Form(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Generate a workout plan based on user goal and history.
    """
    if current_user:
        user = current_user
    else:
        # Fallback to guest
        user = db.query(User).filter(User.username == "guest").first()
        if not user:
            # Create if needed
             user = User(username="guest", email="guest@example.com")
             db.add(user)
             db.commit()
             db.refresh(user)

    # 1. Get History (Last 10 logs)
    logs = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == user.id,
        WorkoutLog.status == "completed"
    ).order_by(WorkoutLog.created_at.desc()).limit(10).all()

    # Convert logs to list of dicts
    history = []
    for log in logs:
        history.append({
            "date": log.created_at.strftime("%Y-%m-%d"),
            "exercise": log.exercise,
            "weight": log.weight,
            "sets": log.sets,
            "reps": log.reps
        })

    # 2. Call AI Service
    plan_data = generate_workout_plan(history, goal)
    
    # 3. Save Plan to DB
    # We store the JSON content as a string
    import json
    new_plan = TrainingPlan(
        user_id=user.id,
        goal=goal,
        content=json.dumps(plan_data, ensure_ascii=False)
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)

    return plan_data

@app.post("/api/v1/tts")
async def text_to_speech(
    text: str = Form(...),
):
    """
    Generate speech from text.
    """
    # Create static/audio directory if not exists
    audio_dir = os.path.join(ROOT, "static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"tts_{hash(text)}.mp3"
    output_path = os.path.join(audio_dir, filename)
    
    # Generate speech
    if not os.path.exists(output_path):
        result_path = generate_speech(text, output_path)
        if not result_path:
            return JSONResponse({"error": "TTS generation failed"}, status_code=500)
            
    # Return URL to access audio
    # Assuming static files are served at /static
    return JSONResponse({
        "audio_url": f"/static/audio/{filename}"
    })

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    if USE_REDIS:
        await websocket.accept()
        
        # Use redis.asyncio
        # Note: Create a new Redis connection for each WebSocket might be expensive at scale.
        # A global pool is better, but for MVP this is fine.
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        pubsub = r.pubsub()
        channel = f"task_updates:{client_id}"
        await pubsub.subscribe(channel)
        
        try:
            # Loop to listen for Redis messages
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    await websocket.send_text(data)
        except WebSocketDisconnect:
            # print(f"Client {client_id} disconnected")
            pass
        except Exception as e:
            print(f"WS Error: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await r.close()
    else:
        # In-Memory Mode
        await manager.connect(client_id, websocket)
        try:
            while True:
                await websocket.receive_text() # Keep connection open
        except WebSocketDisconnect:
            manager.disconnect(client_id)
        except Exception as e:
            print(f"WS Error: {e}")
            manager.disconnect(client_id)

# Mount frontend AFTER all APIs to avoid catching API routes
# Also mount static directory for audio files
app.mount("/static", StaticFiles(directory=os.path.join(ROOT, "static")), name="static")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
