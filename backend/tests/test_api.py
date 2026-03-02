
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.main import app
from backend.database import get_db
from backend.models import Base

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@patch("backend.tasks.process_voice_upload_task.delay")
def test_upload_voice_and_get_logs(mock_task_delay):
    # Mock task delay to do nothing (we test async behavior)
    mock_task_delay.return_value = None
    
    # 3. Test Health
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # 4. Test Voice Upload
    files = {"file": ("test_audio.webm", b"dummy audio content", "audio/webm")}
    data_form = {"thread_id": "test_thread_123"}
    response = client.post("/api/v1/voice", files=files, data=data_form)
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "processing"
    
    # Verify task was called
    mock_task_delay.assert_called_once()
    
    # Manually simulate task execution?
    # Or just verify API response.
    # We can check DB state to see if log is created
    # Since we are using in-memory DB and shared session, we can query it.
    
    # 5. Test Get Logs
    response = client.get("/api/v1/logs")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) > 0
    assert logs[0]["status"] == "processing"

    # 6. Test Image Upload (Not Async Yet)
    with patch("backend.main.analyze_image") as mock_analyze_image:
        mock_analyze_image.return_value = {
            "equipment": "Dumbbell Rack",
            "exercise": "Dumbbell Curls",
            "usage_tips": "Keep your back straight."
        }
        files = {"file": ("test_image.jpg", b"dummy image content", "image/jpeg")}
        response = client.post("/api/v1/image", files=files)
        assert response.status_code == 200
        assert response.json()["equipment"] == "Dumbbell Rack"

    # 7. Test TTS
    with patch("backend.main.generate_speech") as mock_generate_speech:
        mock_generate_speech.return_value = "static/audio/test_audio.mp3"
        response = client.post("/api/v1/tts", data={"text": "Hello world"})
        assert response.status_code == 200
        assert "audio_url" in response.json()

@patch("backend.main.generate_speech")
@patch("backend.main.analyze_image")
@patch("backend.ai_service.get_asr_model")
@patch("backend.main.run_agent", new_callable=AsyncMock)
@patch("backend.tasks.process_voice_upload_task.delay")
def test_auth_flow(mock_task_delay, mock_run_agent, mock_get_asr_model, mock_analyze_image, mock_generate_speech):
    mock_task_delay.return_value = None
    # Mock setups
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Auth User Workout"
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    mock_get_asr_model.return_value = mock_model
    mock_run_agent.return_value = {
        "exercise": "Squat",
        "weight": 120,
        "sets": 3,
        "reps": 8,
        "feedback": "Good depth!"
    }
    mock_generate_speech.return_value = "static/audio/auth_test.mp3"

    # 1. Register
    reg_response = client.post("/api/v1/register", data={"username": "testuser", "password": "password123", "email": "test@example.com"})
    assert reg_response.status_code == 200
    assert reg_response.json()["username"] == "testuser"

    # 2. Login
    login_response = client.post("/api/v1/token", data={"username": "testuser", "password": "password123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Upload Voice with Token
    files = {"file": ("auth_audio.webm", b"auth audio content", "audio/webm")}
    response = client.post("/api/v1/voice", files=files, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

    # 4. Get Logs with Token
    logs_response = client.get("/api/v1/logs", headers=headers)
    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert len(logs) == 1
    assert logs[0]["status"] == "processing"

    # 5. Get Logs without Token (Guest) -> Should NOT see Auth User's log
    # Note: Guest might see guest logs, but not "testuser" logs
    guest_logs_response = client.get("/api/v1/logs")
    assert guest_logs_response.status_code == 200
    guest_logs = guest_logs_response.json()
    # Since we are using in-memory DB and this test function runs in isolation (or shared DB depending on fixture scope), 
    # wait, setup_db fixture has autouse=True and yields. It drops all tables after yield.
    # So each test function starts with clean DB.
    # But in step 5, we are in the same test function, same DB session context?
    # Yes, client uses app which uses override_get_db which creates new session but engine is shared.
    # StaticPool means connection is shared.
    # So DB state persists within the test function.
    
    # Guest logs should be empty or only contain guest logs.
    # "testuser" logs should NOT be returned for guest.
    # Guest logs should be empty because we only created one log for "testuser".
    assert len(guest_logs) == 0

def test_progress_stats():
    # 1. Register and Login
    client.post("/api/v1/register", data={"username": "stats_user", "password": "password", "email": "stats@example.com"})
    login_res = client.post("/api/v1/token", data={"username": "stats_user", "password": "password"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Insert mock logs directly
    from backend.models import WorkoutLog, User
    
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "stats_user").first()
    
    log1 = WorkoutLog(user_id=user.id, exercise="Bench Press", weight=100.0, sets=3, reps=10, status="completed")
    log2 = WorkoutLog(user_id=user.id, exercise="Bench Press", weight=105.0, sets=3, reps=8, status="completed")
    log3 = WorkoutLog(user_id=user.id, exercise="Squat", weight=140.0, sets=5, reps=5, status="completed")
    
    db.add_all([log1, log2, log3])
    db.commit()
    db.close()
    
    # 3. Call Stats API
    response = client.get("/api/v1/stats/progress", headers=headers)
    assert response.status_code == 200
    stats = response.json()
    
    assert "Bench Press" in stats
    assert len(stats["Bench Press"]) == 2
    assert stats["Bench Press"][0]["weight"] == 100.0
    assert stats["Bench Press"][1]["weight"] == 105.0
    
    assert "Squat" in stats
    assert len(stats["Squat"]) == 1

@patch("backend.main.generate_workout_plan")
def test_plan_generation(mock_generate_workout_plan):
    # Mock AI response
    mock_plan = {
        "plan_name": "Test Plan",
        "overview": "A test plan",
        "schedule": []
    }
    mock_generate_workout_plan.return_value = mock_plan

    # 1. Register and Login
    client.post("/api/v1/register", data={"username": "plan_user", "password": "password", "email": "plan@example.com"})
    login_res = client.post("/api/v1/token", data={"username": "plan_user", "password": "password"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Call Plan API
    response = client.post("/api/v1/plan/generate", data={"goal": "Hypertrophy"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["plan_name"] == "Test Plan"

    # 3. Verify DB persistence
    from backend.models import TrainingPlan, User
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "plan_user").first()
    plan = db.query(TrainingPlan).filter(TrainingPlan.user_id == user.id).first()
    assert plan is not None
    assert plan.goal == "Hypertrophy"
    db.close()

@patch("backend.main.redis.from_url")
def test_websocket(mock_redis_from_url):
    import json
    
    # Mock Redis PubSub
    mock_redis = MagicMock()
    mock_redis.close = AsyncMock()
    
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    
    async def mock_listen_gen():
        yield {
            'type': 'message',
            'data': json.dumps({"status": "completed", "transcript": "test"}).encode('utf-8')
        }
        
    mock_pubsub.listen.side_effect = mock_listen_gen
    mock_redis.pubsub.return_value = mock_pubsub
    mock_redis_from_url.return_value = mock_redis
    
    with client.websocket_connect("/ws/test-client-id") as websocket:
        data = websocket.receive_json()
        assert data["status"] == "completed"
        assert data["transcript"] == "test"
        websocket.close()

