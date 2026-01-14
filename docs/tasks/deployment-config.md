# Task: Deployment Configuration

## Overview

Set up deployment infrastructure including Docker Compose for development, Kubernetes manifests for production, CI/CD pipelines, and environment configuration.

## Dependencies

- All other tasks should be completed

## Deliverables

### 1. Docker Compose Development Environment

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  # Frontend (Next.js)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
      - NODE_ENV=development
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - backend

  # Backend (FastAPI)
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://bod:bodpassword@postgres:5432/bod
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production
      - VLLM_URL=http://vllm:8000
      - VLM_URL=http://vllm:8000
      - ASR_URL=http://funasr:8001
      - TTS_URL=http://chattts:8002
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - VAPID_PUBLIC_KEY=your-vapid-public-key
      - VAPID_PRIVATE_KEY=your-vapid-private-key
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis
      - minio

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=bod
      - POSTGRES_PASSWORD=bodpassword
      - POSTGRES_DB=bod
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # MinIO (S3-compatible storage)
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data

  # vLLM (LLM Serving)
  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8001:8000"
    environment:
      - MODEL_NAME=Qwen/Qwen2.5-14B-Instruct
    volumes:
      - model_cache:/root/.cache
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # FunASR (ASR)
  funasr:
    image: registry.cn-hangzhou.aliyuncs.com/funasr/funasr-runtime-sdk:latest
    ports:
      - "8002:8001"
    volumes:
      - model_cache:/models

  # ChatTTS (TTS)
  chattts:
    image: modelscope/chattts:latest
    ports:
      - "8003:8002"
    volumes:
      - model_cache:/models

  # Celery Worker (async tasks)
  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://bod:bodpassword@postgres:5432/bod
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - postgres

volumes:
  postgres_data:
  redis_data:
  minio_data:
  model_cache:

networks:
  default:
    name: bod-network
```

### 2. Production Kubernetes Manifests

#### `k8s/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bod-prod
```

#### `k8s/configmap.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bod-config
  namespace: bod-prod
data:
  NODE_ENV: "production"
  DATABASE_URL: "postgresql://bod:$(DB_PASSWORD)@postgres-service:5432/bod"
  REDIS_URL: "redis://redis-service:6379/0"
  MINIO_ENDPOINT: "minio-service:9000"
  VLLM_URL: "http://vllm-service:8000"
```

#### `k8s/secret.yaml`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bod-secret
  namespace: bod-prod
type: Opaque
stringData:
  DB_PASSWORD: "change-this-in-production"
  SECRET_KEY: "change-this-in-production"
  MINIO_ACCESS_KEY: "minioadmin"
  MINIO_SECRET_KEY: "change-this-in-production"
  VAPID_PUBLIC_KEY: "your-vapid-public-key"
  VAPID_PRIVATE_KEY: "your-vapid-private-key"
```

#### `k8s/frontend/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: bod-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: ghcr.io/sherkevin/bod-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.bod.fit"
        - name: NODE_ENV
          valueFrom:
            configMapKeyRef:
              name: bod-config
              key: NODE_ENV
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: bod-prod
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP
```

#### `k8s/backend/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: bod-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/sherkevin/bod-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: bod-config
              key: DATABASE_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: bod-secret
              key: SECRET_KEY
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: bod-prod
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### `k8s/vllm/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm
  namespace: bod-prod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_NAME
          value: "Qwen/Qwen2.5-14B-Instruct"
        - name: TENSOR_PARALLEL_SIZE
          value: "1"
        resources:
          requests:
            memory: "32Gi"
            cpu: "8000m"
            nvidia.com/gpu: "1"
          limits:
            memory: "32Gi"
            cpu: "8000m"
            nvidia.com/gpu: "1"
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
      nodeSelector:
        gpu: "true"
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
  namespace: bod-prod
spec:
  selector:
    app: vllm
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### `k8s/ingress.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bod-ingress
  namespace: bod-prod
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/websocket-services: "backend-service"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - bod.fit
    - api.bod.fit
    secretName: bod-tls
  rules:
  - host: bod.fit
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
  - host: api.bod.fit
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
```

### 3. CI/CD Pipeline

#### `.github/workflows/deploy.yml`
```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  FRONTEND_IMAGE: ghcr.io/sherkevin/bod-frontend
  BACKEND_IMAGE: ghcr.io/sherkevin/bod-backend

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install backend dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run backend tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'

    - name: Install frontend dependencies
      run: |
        cd frontend
        npm ci

    - name: Run frontend tests
      run: |
        cd frontend
        npm test

  build-frontend:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    permissions:
      contents: read
      packages: write
    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.FRONTEND_IMAGE }}
        tags: |
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: ./frontend
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  build-backend:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    permissions:
      contents: read
      packages: write
    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.BACKEND_IMAGE }}
        tags: |
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: ./backend
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: [build-frontend, build-backend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v4

    - name: Configure kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.28.0'

    - name: Set up kubeconfig
      run: |
        mkdir -p ~/.kube
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > ~/.kube/config

    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f k8s/namespace.yaml
        kubectl apply -f k8s/configmap.yaml
        kubectl apply -f k8s/secret.yaml
        kubectl apply -f k8s/postgres/
        kubectl apply -f k8s/redis/
        kubectl apply -f k8s/minio/
        kubectl apply -f k8s/backend/
        kubectl apply -f k8s/frontend/
        kubectl apply -f k8s/vllm/
        kubectl apply -f k8s/ingress.yaml

    - name: Rollout restart
      run: |
        kubectl rollout restart deployment/backend -n bod-prod
        kubectl rollout restart deployment/frontend -n bod-prod
```

### 4. Docker Files

#### `frontend/Dockerfile`
```dockerfile
# Development stage
FROM node:18-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Production stage
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production runtime
FROM node:18-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

#### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 boduser && chown -R boduser:boduser /app
USER boduser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5. Environment Configuration

#### `.env.example`
```bash
# Database
DATABASE_URL=postgresql://bod:password@localhost:5432/bod

# Redis
REDIS_URL=redis://localhost:6379/0

# API
SECRET_KEY=your-secret-key-here
API_HOST=0.0.0.0
API_PORT=8000

# AI Services
VLLM_URL=http://localhost:8001
VLM_URL=http://localhost:8001
ASR_URL=http://localhost:8002
TTS_URL=http://localhost:8003

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_USE_SSL=false

# Push Notifications
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_PRIVATE_KEY=your-vapid-private-key

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### 6. Monitoring Stack

#### `docker-compose.monitoring.yml`
```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  prometheus_data:
  grafana_data:
```

#### `monitoring/prometheus.yml`
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']
```

## Technical Requirements

- Docker Compose for local development
- Kubernetes for production
- CI/CD with GitHub Actions
- Environment-specific configurations
- Health checks and probes
- Rolling updates

## Acceptance Criteria

- [ ] Docker Compose starts all services
- [ ] All services are healthy
- [ ] Kubernetes manifests are valid
- [ ] CI/CD pipeline builds images
- [ ] Deployment to K8s works
- [ ] Ingress routes traffic correctly
- [ ] SSL certificates are provisioned

## Notes

- Use secrets management in production
- Set up database backups
- Configure log aggregation
- Monitor resource usage
- Plan for scaling
