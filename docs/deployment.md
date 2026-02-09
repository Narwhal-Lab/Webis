# Deployment Guide

Learn how to deploy Webis in various environments.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Monitoring and Logging](#monitoring-and-logging)
6. [Scaling and Performance](#scaling-and-performance)

## Development Setup

### Prerequisites

- Python 3.10+
- pip or uv
- Docker (optional)

### Local Development

```bash
# Clone repository
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env
```

### Environment Variables

Create `.env` file:

```env
# Core Configuration
WEBIS_ENV=development
WEBIS_PORT=8000
WEBIS_HOST=localhost

# Database
DATABASE_URL=sqlite:///webis.db

# Redis (for background tasks)
REDIS_URL=redis://localhost:6379/0

# LLM Providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
DEEPSEEK_API_KEY=your_deepseek_key

# Search APIs
SERPAPI_API_KEY=your_serpapi_key
TAVILY_API_KEY=your_tavily_key
EXA_API_KEY=your_exa_key
FIRECRAWL_API_KEY=your_firecrawl_key

# Security
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=http://localhost:8501
```

## Docker Deployment

### Quick Start

```bash
# Clone repository
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis

# Start services
docker-compose up -d

# View logs
docker-compose logs -f webis-api
```

### Docker Compose Configuration

File: `docker-compose.yml`

```yaml
version: '3.8'

services:
  webis-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  webis-worker:
    build: .
    command: celery -A webis.core.celery_app worker --loglevel=info
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  webis-beat:
    build: .
    command: celery -A webis.core.celery_app beat --loglevel=info
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=webis
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=webis
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  neo4j:
    image: neo4j:5-community
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=apoc
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
  neo4j_data:
```

### Production Docker Compose

File: `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  webis-api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
      - GUNICORN_WORKERS=4
      - GUNICORN_WORKER_CLASS=sync
      - GUNICORN_WORKER_CONNECTIONS=1000
    ports:
      - "80:8000"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ... (other services similar to development)

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - webis-api
    restart: unless-stopped
```

## Production Deployment

### Prerequisites

- Linux server (Ubuntu 20.04+)
- PostgreSQL database
- Redis server
- Reverse proxy (nginx, Apache)
- SSL certificate
- Monitoring setup

### Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip nginx postgresql redis-server

# Create user
sudo useradd -m -s /bin/bash webis

# Set permissions
sudo chown -R webis:webis /opt/webis
```

### Database Setup

```bash
# Connect to PostgreSQL
sudo -u postgres psql

-- Create database
CREATE DATABASE webis;

-- Create user
CREATE USER webis_user WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE webis TO webis_user;

-- Exit
\q
```

### Application Deployment

```bash
# Deploy application
sudo -u webis git clone https://github.com/Narwhal-Lab/Webis.git /opt/webis
cd /opt/webis

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example /opt/webis/.env
# Edit .env file with production values

# Run migrations
python -c "from webis.core.db import init_db; init_db()"

# Create systemd service
sudo tee /etc/systemd/system/webis.service > /dev/null <<EOF
[Unit]
Description=Webis API Service
After=network.target

[Service]
User=webis
Group=webis
WorkingDirectory=/opt/webis
Environment=PATH=/opt/webis/venv/bin
ExecStart=/opt/webis/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 webis.server:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable webis
sudo systemctl start webis
```

### Reverse Proxy Setup

```nginx
# /etc/nginx/sites-available/webis
server {
    listen 80;
    server_name your-domain.com;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options "nosniff";
    add_header Referrer-Policy "no-referrer";
    add_header Content-Security-Policy "default-src 'self'";

    # Gunicorn proxy
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # Static files
    location /static/ {
        alias /opt/webis/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

### SSL Configuration

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Renewal script
sudo tee /etc/cron.monthly/certbot > /dev/null <<EOF
#!/bin/bash
certbot renew --quiet
EOF
sudo chmod +x /etc/cron.monthly/certbot
```

## Cloud Deployment

### AWS Deployment

#### Using Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB
eb init -p python-3.10 webis-platform

# Create environment
eb create webis-prod -c webis-prod

# Deploy
eb deploy
```

#### Using EKS

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webis-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webis-api
  template:
    metadata:
      labels:
        app: webis-api
    spec:
      containers:
      - name: webis-api
        image: webis/webis:latest
        ports:
        - containerPort: 8000
        env:
        - name: WEBIS_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: webis-db-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: webis-service
spec:
  selector:
    app: webis-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### GCP Deployment

#### Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/webis
gcloud run deploy webis \
  --image gcr.io/PROJECT-ID/webis \
  --platform managed \
  --region us-central1 \
  --set-env-vars=WEBIS_ENV=production
```

#### GKE

```bash
# Create cluster
gcloud container clusters create webis-cluster \
  --num-nodes=3 \
  --zone us-central1-a

# Apply manifests
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

## Monitoring and Logging

### Application Monitoring

```python
# src/webis/core/monitoring.py
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# Metrics
REQUEST_COUNT = Counter(
    'webis_requests_total',
    'Total number of requests',
    ['method', 'endpoint']
)

REQUEST_DURATION = Histogram(
    'webis_request_duration_seconds',
    'Request duration'
)

ACTIVE_JOBS = Gauge(
    'webis_active_jobs',
    'Number of active background jobs'
)

class MonitoringMiddleware:
    def __init__(self, app):
        self.app = app
        prometheus_client.start_http_server(8001)

    def __call__(self, environ, start_response):
        REQUEST_COUNT.inc(environ['REQUEST_METHOD'], environ['PATH_INFO'])

        with REQUEST_DURATION.time():
            return self.app(environ, start_response)
```

### Logging Configuration

```python
# src/webis/core/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create logger
    logger = logging.getLogger('webis')
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # File handler
    file_handler = RotatingFileHandler(
        'logs/webis.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
```

### Health Checks

```python
# src/webis/core/health.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
async def health_check():
    return JSONResponse(
        content={
            "status": "healthy",
            "version": "2.0.0-alpha.1",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.get("/health/detailed")
async def detailed_health_check():
    # Check database
    db_ok = await check_database()

    # Check Redis
    redis_ok = await check_redis()

    # Check external APIs
    api_ok = await check_external_apis()

    overall = db_ok and redis_ok and api_ok

    return JSONResponse(
        content={
            "status": "healthy" if overall else "unhealthy",
            "checks": {
                "database": db_ok,
                "redis": redis_ok,
                "external_apis": api_ok
            }
        }
    )
```

## Scaling and Performance

### Horizontal Scaling

```python
# Scale with Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webis-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webis-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Caching Strategy

```python
# Redis caching
import redis
from functools import wraps

redis_client = redis.Redis(host='redis', port=6379, db=0)

def cache_result(expire=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try to get from cache
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            redis_client.setex(key, expire, json.dumps(result))

            return result
        return wrapper
    return decorator
```

### Database Optimization

```python
# Database indexes
async def create_indexes():
    # Create indexes for performance
    await create_index("documents", "source_plugin")
    await create_index("documents", "created_at")
    await create_index("documents", "url")
    await create_index("documents", "content_hash")

    # Vector search indexes
    await create_vector_index("embeddings", "vector")
```

---

For more information:
- [API Reference](api.md) - Complete API documentation
- [User Guide](user-guide.md) - Complete feature walkthrough
- [Quick Start](quickstart.md) - Get started in 5 minutes