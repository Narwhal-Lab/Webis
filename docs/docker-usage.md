# Webis Docker 使用指南

本指南将帮助您在 Docker 容器中运行 Webis 项目。

## 🐳 基本要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 内存（推荐 8GB+）
- 网络连接

## 📦 快速启动

### 1. 克隆项目
```bash
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
```

### 2. 复制环境变量文件
```bash
cp .env.example .env
```

### 3. 编辑 .env 文件
根据您的环境配置 API 密钥：
```bash
# 编辑 .env 文件
nano .env
```

### 4. 启动 Docker 容器
```bash
docker-compose up -d
```

### 5. 检查服务状态
```bash
docker-compose ps
```

### 6. 访问 Web 界面
- Web 界面: http://localhost:8501
- API 服务器: http://localhost:8000
- Prometheus (可选): http://localhost:9090

## 📋 详细配置

### Docker Compose 配置

```yaml
version: '3.8'

services:
  webis-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SERPAPI_API_KEY=${SERPAPI_API_KEY}
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
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/webis
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
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
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

### 生产环境配置

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - webis-api
    restart: unless-stopped

  webis-api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
      - GUNICORN_WORKERS=4
      - GUNICORN_WORKER_CLASS=sync
      - GUNICORN_WORKER_CONNECTIONS=1000
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  # ... 其他服务配置相同 ...
```

## 🔧 环境变量配置

### .env 文件示例
```bash
# 核心配置
WEBIS_ENV=production
WEBIS_PORT=8000
WEBIS_HOST=localhost

# 数据库配置
DATABASE_URL=postgresql://postgres:password@postgres:5432/webis

# Redis 配置
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# LLM 提供商
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# 搜索 API
SERPAPI_API_KEY=your_serpapi_key
TAVILY_API_KEY=your_tavily_key
EXA_API_KEY=your_exa_key
FIRECRAWL_API_KEY=your_firecrawl_key

# 向量存储
VECTOR_STORE_PATH=./data/chroma_db

# 安全配置
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=http://localhost:8501,http://localhost:3000

# 日志配置
LOG_LEVEL=INFO
```

## 🚀 常用命令

### 启动所有服务
```bash
docker-compose up -d
```

### 停止所有服务
```bash
docker-compose down
```

### 查看日志
```bash
# 查看 API 服务日志
docker-compose logs webis-api

# 查看 Redis 日志
docker-compose logs redis

# 实时查看日志
docker-compose logs -f webis-api
```

### 进入容器
```bash
# 进入 API 容器
docker-compose exec webis-api bash

# 进入 Redis 容器
docker-compose exec redis bash
```

### 数据库管理
```bash
# 进入 PostgreSQL 容器
docker-compose exec postgres psql -U postgres

# 备份数据库
docker-compose exec postgres pg_dump -U postgres webis > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U postgres webis < backup.sql
```

## 📊 监控和诊断

### 查看容器状态
```bash
docker-compose ps
docker-compose top
```

### 检查资源使用
```bash
docker stats
```

### 健康检查
```bash
# 检查 API 服务健康状态
curl http://localhost:8000/health

# 检查 Web 界面
curl http://localhost:8501
```

## 🔧 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 查看详细错误
docker-compose logs webis-api

# 重新构建镜像
docker-compose build webis-api
docker-compose up -d
```

#### 2. 数据库连接问题
```bash
# 检查 PostgreSQL 状态
docker-compose exec postgres pg_isready

# 重置数据库
docker-compose down
docker-compose up -d
```

#### 3. Redis 连接问题
```bash
# 检查 Redis 状态
docker-compose exec redis redis-cli ping
```

#### 4. API 密钥错误
```bash
# 检查环境变量
docker-compose exec webis-api env | grep API_KEY

# 确保在 .env 文件中正确设置
```

### 调试模式

```bash
# 启动调试模式
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up -d

# debug.yml 示例
version: '3.8'
services:
  webis-api:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
```

## 📦 数据持久化

### 重要目录
- `./data/` - 存储 ChromaDB 向量数据
- `./logs/` - 应用日志
- `./output/` - 爬取结果

### 备份策略
```bash
# 备份 RAG 数据
docker-compose exec webis-api cp -r /app/data /backup/webis_data_$(date +%Y%m%d)

# 定期备份
0 2 * * * docker-compose exec webis-api tar -czf /backup/webis_data_$(date +%Y%m%d).tar.gz /app/data
```

## 🚀 升级 Webis

```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```

## 🔒 安全建议

1. **使用强密码**
2. **限制容器权限**
3. **定期更新镜像**
4. **监控异常活动**
5. **备份重要数据**

## 📞 获取帮助

如果遇到问题，可以：

1. 查看 Docker 日志：`docker-compose logs`
2. 检查 Webis 日志：`docker-compose exec webis-api tail -f /app/logs/webis.log`
3. 访问 GitHub Issues：https://github.com/Narwhal-Lab/Webis/issues
4. 联系支持：contact@webis.dev

---

现在您已经了解了如何在 Docker 中运行 Webis！开始探索 AI 驱动的知识管道吧！ 🚀