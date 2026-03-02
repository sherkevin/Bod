import os
import shutil
try:
    from .celery_app import celery_app
    from .ai_service import transcribe_audio, analyze_workout, analyze_image, generate_speech
    from .agent.graph import run_agent
except ImportError:
    from celery_app import celery_app
    from ai_service import transcribe_audio, analyze_workout, analyze_image, generate_speech
    from agent.graph import run_agent
import asyncio
import redis
import json
import os

# Note: Celery tasks are synchronous by default.
# For async functions (like run_agent), we need to run them in an event loop or use a sync wrapper.

@celery_app.task(name="process_voice_upload")
def process_voice_upload_task(file_path: str, thread_id: str, log_id: int, client_id: str = None):
    """
    Celery wrapper for the internal processing logic.
    """
    return process_voice_upload_internal(file_path, thread_id, log_id, client_id)

def process_voice_upload_internal(file_path: str, thread_id: str, log_id: int, client_id: str = None):
    """
    Background task to process voice upload:
    1. Transcribe
    2. Analyze/Agent Run
    3. Update Database Log
    4. Notify Client via Redis Pub/Sub (if client_id provided)
    """
    # Import here to avoid circular imports
    try:
        from .database import SessionLocal
        from .models import WorkoutLog
    except ImportError:
        from database import SessionLocal
        from models import WorkoutLog
    
    db = SessionLocal()
    status = "failed"
    result_data = {}

    try:
        log = db.query(WorkoutLog).filter(WorkoutLog.id == log_id).first()
        if not log:
            return # Should not happen

        # 1. Transcribe
        transcript = transcribe_audio(file_path)
        
        # 2. Agent Run (Async wrapper)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        analysis_result = loop.run_until_complete(run_agent(transcript, thread_id=thread_id))
        
        # 3. Update DB
        log.transcript = transcript
        log.raw_log = transcript
        log.feedback = analysis_result.get("feedback")
        log.exercise = analysis_result.get("exercise")
        log.weight = analysis_result.get("weight")
        log.sets = analysis_result.get("sets")
        log.reps = analysis_result.get("reps")
        log.status = "completed"
        
        db.commit()
        status = "completed"
        result_data = {
            "transcript": transcript,
            "feedback": log.feedback,
            "exercise": log.exercise,
            "weight": log.weight,
            "sets": log.sets,
            "reps": log.reps
        }
        
    except Exception as e:
        print(f"Task Error: {e}")
        if log:
            log.status = "failed"
            log.feedback = f"Processing Error: {str(e)}"
            db.commit()
            status = "failed"
            result_data = {"error": str(e)}
    finally:
        db.close()
        
        # 4. Notify Client (Redis)
        # Only try Redis if we are in Celery context (implied by this function being called normally)
        # But if called from main.py in no-redis mode, this might fail or be redundant.
        # We will keep it here but catch connection errors silently.
        if client_id:
            try:
                r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=1)
                message = {
                    "type": "task_completed",
                    "log_id": log_id,
                    "status": status,
                    **result_data
                }
                r.publish(f"task_updates:{client_id}", json.dumps(message))
                print(f"Published update to task_updates:{client_id}")
            except Exception as e:
                print(f"Redis Publish Skipped: {e}")
    
    return result_data

@celery_app.task(name="process_voice_upload_sync")
def process_voice_upload_sync(file_path: str, thread_id: str):
    """
    Synchronous-like wrapper for the logic, but executed in worker.
    Returns the result dictionary.
    """
    transcript = transcribe_audio(file_path)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    analysis_result = loop.run_until_complete(run_agent(transcript, thread_id=thread_id))
    loop.close()
    
    return {
        "transcript": transcript,
        "analysis": analysis_result
    }
