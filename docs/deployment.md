# Deployment Guide

Deploy Webis v2 in development, Docker, and production environments.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Monitoring & Logging](#monitoring--logging)
6. [Scaling](#scaling)

## Development Setup

### Prerequisites

- Python 3.9+ (3.10 recommended)
- conda or pip
- At least one LLM API key (DeepSeek, OpenAI, or SiliconFlow)
- At least one search API key (Tavily, Bocha, Serper, etc.)

### Local Development

```bash
# Clone repository
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis

# Option A: Conda setup (recommended)
bash setup/conda_setup.sh
conda activate webis

# Option B: Manual
python -m venv venv
source venv/bin/activate
pip install -e .
```

### Environment Configuration

```bash
cp .env.example .env
```

**Required variables:**

```env
# LLM Provider (at least one)
DEEPSEEK_API_KEY=your_key
# OPENAI_API_KEY=your_key
# SILICONFLOW_API_KEY=your_key
# ANTHROPIC_API_KEY=your_key

# Search APIs (at least one)
TAVILY_API_KEY=your_key
BOCHA_API_KEY=your_key
# EXA_API_KEY=your_key
```

**Optional variables:**

```env
# Core
WEBIS_ENV=development
WEBIS_LLM_MODEL=deepseek-v3.2    # Override model selection
LOG_LEVEL=INFO

# Custom LLM endpoint
CUSTOM_API_KEY=your_key
CUSTOM_MODEL_NAME=your-model
CUSTOM_BASE_URL=https://your-endpoint/v1

# Database (optional)
DATABASE_URL=sqlite:///webis.db

# Redis (optional, for background tasks)
REDIS_URL=redis://localhost:6379/0

# Vector store
VECTOR_STORE_PATH=./data/chroma_db

# Embedding model (offline mode)
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1

# Additional search APIs
SERPAPI_API_KEY=your_key
SERPER_API_KEY=your_key
BRIGHTDATA_API_TOKEN=your_token
```

### Verify Installation

```bash
# Test CLI
webis --help

# Test a quick pipeline
webis run "test query" --limit 2

# Test report generation
webis html-report ./output/<timestamp>/rag_store.json --query "test"

# Launch visualizer
webis visualizer
```

## Docker Deployment

### Quick Start

```bash
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
cp .env.example .env
# Edit .env with your API keys

docker-compose up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `webis-api` | 8000 | Main API server |
| `webis-worker` | — | Celery background worker |
| `webis-beat` | — | Celery scheduler |
| `redis` | 6379 | Cache & message broker |
| `postgres` | 5432 | Persistent storage |
| `neo4j` | 7474/7687 | Graph database (optional) |

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  webis-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://webis:password@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./logs:/app/logs
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

volumes:
  redis_data:
  postgres_data:
```

### Docker Operations

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f webis-api

# Enter container
docker-compose exec webis-api bash

# Rebuild after code changes
docker-compose build && docker-compose up -d

# Stop
docker-compose down
```

See [Docker Usage Guide](docker-usage.md) for detailed instructions.

## Production Deployment

### Server Prerequisites

- Linux server (Ubuntu 20.04+)
- 4 GB RAM minimum (8 GB+ recommended)
- PostgreSQL 15+
- Redis 7+
- nginx (reverse proxy)
- SSL certificate

### Application Setup

```bash
# Create system user
sudo useradd -m -s /bin/bash webis
sudo su - webis

# Clone and install
git clone https://github.com/Narwhal-Lab/Webis.git /opt/webis
cd /opt/webis
bash setup/conda_setup.sh
conda activate webis

# Configure
cp .env.example .env
# Edit .env with production values
```

### systemd Service

```ini
# /etc/systemd/system/webis.service
[Unit]
Description=Webis Pipeline Service
After=network.target postgresql.service redis.service

[Service]
User=webis
Group=webis
WorkingDirectory=/opt/webis
Environment=PATH=/home/webis/miniconda3/envs/webis/bin
ExecStart=/home/webis/miniconda3/envs/webis/bin/python -m webis.cli run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable webis
sudo systemctl start webis
```

### nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;  # Streamlit visualizer
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }
}
```

### SSL with Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Cloud Deployment

### AWS (Elastic Beanstalk)

```bash
pip install awsebcli
eb init -p python-3.10 webis
eb create webis-prod
eb deploy
```

### GCP (Cloud Run)

```bash
gcloud builds submit --tag gcr.io/PROJECT/webis
gcloud run deploy webis \
  --image gcr.io/PROJECT/webis \
  --platform managed \
  --set-env-vars WEBIS_ENV=production
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webis
spec:
  replicas: 2
  selector:
    matchLabels:
      app: webis
  template:
    metadata:
      labels:
        app: webis
    spec:
      containers:
      - name: webis
        image: webis/webis:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: webis-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

See `k8s/hpa.yaml` for auto-scaling configuration.

## Monitoring & Logging

### Logging

Webis uses Python's `logging` module. Configure via environment:

```env
LOG_LEVEL=INFO    # DEBUG, INFO, WARNING, ERROR
DEBUG=false       # Enable debug mode
```

Log output goes to stderr by default. For file logging, configure in your
deployment:

```bash
webis run "task" 2>&1 | tee -a /var/log/webis/pipeline.log
```

### LLM Usage Tracking

The `LLMRouter` automatically tracks:
- Total tokens consumed
- Cost per model (USD)
- Cache hit rate

Access programmatically:

```python
from webis.core.llm.base import get_default_router

router = get_default_router()
stats = router.get_stats()
print(f"Total tokens: {stats['total_tokens']}")
print(f"Total cost: ${stats['total_cost_usd']:.4f}")
```

### Health Checks

```bash
# Verify CLI works
webis --help

# Verify search plugins
python -c "from webis.core.plugin import get_default_registry; r = get_default_registry(); print(r.list_sources())"

# Verify LLM connectivity
python -c "
from webis.core.llm.base import get_default_router
r = get_default_router()
resp = r.chat([{'role': 'user', 'content': 'Say hello'}], max_tokens=10)
print(resp.content)
"
```

## Scaling

### Key Bottlenecks

| Component | Bottleneck | Mitigation |
|-----------|-----------|------------|
| LLM API calls | Rate limits, latency | Use fallback chain, caching |
| Web crawling | Network I/O | Parallel source plugins |
| Embedding generation | CPU/GPU | Pre-cache models, batch processing |
| Report generation | LLM token limits | Hybrid rendering approach |

### Performance Tips

1. **Pre-download embedding model** to avoid first-run latency:
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
   ```

2. **Use `WEBIS_LLM_MODEL`** to select a fast model for development:
   ```env
   WEBIS_LLM_MODEL=qwen-coder-32b
   ```

3. **Set offline mode** for air-gapped environments:
   ```env
   HF_HUB_OFFLINE=1
   TRANSFORMERS_OFFLINE=1
   ```

4. **Lower `--limit`** for faster iteration during development.

---

For more information:
- [Docker Usage](docker-usage.md) — Detailed Docker guide
- [API Reference](api.md) — Core classes and CLI reference
- [Quick Start](quickstart.md) — Get started in 5 minutes
