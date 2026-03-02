# Start Bod Application (MVP)

# 1. Activate Virtual Environment
$venvPath = ".\venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Host "Virtual environment not found. Please create one."
    exit
}

# 2. Start Redis (Optional - if using Docker)
# docker-compose up -d redis

# 3. Start Celery Worker (in new window)
# Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$venvPath'; celery -A backend.celery_app worker --loglevel=info -P solo"

# 4. Start FastAPI Server
Write-Host "Starting FastAPI Server..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
