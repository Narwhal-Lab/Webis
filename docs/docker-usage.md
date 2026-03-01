# Webis Docker 使用指南

本指南帮助你在 Docker 容器中运行 Webis v2。

## 🐳 基本要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 内存（推荐 8GB+）
- 网络连接（用于 LLM API 调用和网络爬取）

## 📦 快速启动

### 1. 克隆项目

```bash
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置以下密钥：

```env
# LLM 提供商（至少一个）
DEEPSEEK_API_KEY=your_deepseek_key
# SILICONFLOW_API_KEY=your_siliconflow_key
# OPENAI_API_KEY=your_openai_key

# 搜索 API（至少一个）
TAVILY_API_KEY=your_tavily_key
BOCHA_API_KEY=your_bocha_key
```

### 3. 启动容器

```bash
docker-compose up -d
```

### 4. 检查状态

```bash
docker-compose ps
```

### 5. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| Streamlit 可视化 | http://localhost:8501 | Web 界面 |
| API 服务 | http://localhost:8000 | REST API |

## 📋 Docker Compose 配置

### 开发环境

```yaml
version: '3.8'

services:
  webis-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WEBIS_ENV=development
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

### 生产环境

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
      dockerfile: Dockerfile
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://webis:${DB_PASSWORD}@postgres:5432/webis
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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  webis-worker:
    build: .
    command: celery -A webis.core.celery_app worker --loglevel=info
    environment:
      - WEBIS_ENV=production
      - DATABASE_URL=postgresql://webis:${DB_PASSWORD}@postgres:5432/webis
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=webis
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=webis
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

## 🔧 环境变量详解

### 核心配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `WEBIS_ENV` | 运行环境 | `development` |
| `WEBIS_LLM_MODEL` | 指定 LLM 模型 | 自动选择 |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DEBUG` | 调试模式 | `false` |

### LLM 提供商

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `SILICONFLOW_API_KEY` | SiliconFlow API 密钥 |
| `OPENAI_API_KEY` | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 |
| `CUSTOM_API_KEY` | 自定义 LLM 端点密钥 |
| `CUSTOM_MODEL_NAME` | 自定义模型名称 |
| `CUSTOM_BASE_URL` | 自定义 API 基础 URL |

### 搜索 API

| 变量 | 说明 |
|------|------|
| `TAVILY_API_KEY` | Tavily 搜索 |
| `BOCHA_API_KEY` | Bocha 搜索 |
| `EXA_API_KEY` | Exa 搜索 |
| `SERPER_API_KEY` | Serper Google 搜索 |
| `SERPAPI_API_KEY` | SerpAPI |
| `BRIGHTDATA_API_TOKEN` | Bright Data 抓取 |

### 基础设施

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite:///webis.db` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `VECTOR_STORE_PATH` | 向量存储路径 | `./data/chroma_db` |

## 🚀 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启
docker-compose restart

# 查看状态
docker-compose ps
```

### 日志查看

```bash
# 实时日志
docker-compose logs -f webis-api

# 最近 100 行
docker-compose logs --tail=100 webis-api

# 所有服务日志
docker-compose logs -f
```

### 容器操作

```bash
# 进入容器
docker-compose exec webis-api bash

# 在容器内运行 Webis 命令
docker-compose exec webis-api webis run "AI news" --limit 3

# 生成 HTML 报告
docker-compose exec webis-api webis html-report /app/output/<timestamp>/rag_store.json --query "AI news"
```

### 数据库操作

```bash
# 进入 PostgreSQL
docker-compose exec postgres psql -U webis

# 备份
docker-compose exec postgres pg_dump -U webis webis > backup.sql

# 恢复
docker-compose exec -T postgres psql -U webis webis < backup.sql
```

## 📊 监控

### 资源使用

```bash
docker stats
docker-compose top
```

### 健康检查

```bash
# API 健康
curl http://localhost:8000/health

# Redis 状态
docker-compose exec redis redis-cli ping

# PostgreSQL 状态
docker-compose exec postgres pg_isready
```

## 🔧 故障排除

### 容器启动失败

```bash
# 查看错误日志
docker-compose logs webis-api

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

### API 密钥错误

```bash
# 检查容器内的环境变量
docker-compose exec webis-api env | grep API_KEY

# 确保 .env 文件正确
cat .env | grep -v "^#" | grep -v "^$"
```

### 内存不足

```bash
# 检查内存使用
docker stats --no-stream

# 限制容器内存（在 docker-compose.yml 中）
# deploy:
#   resources:
#     limits:
#       memory: 4G
```

### 网络问题

```bash
# 测试容器间网络
docker-compose exec webis-api ping redis
docker-compose exec webis-api ping postgres

# 重建网络
docker-compose down
docker network prune
docker-compose up -d
```

## 📦 数据持久化

### 重要目录

| 目录 | 说明 |
|------|------|
| `./data/` | 向量数据库、模型缓存 |
| `./output/` | 爬取结果、报告文件 |
| `./logs/` | 应用日志 |

### 备份

```bash
# 备份输出数据
tar -czf webis_output_$(date +%Y%m%d).tar.gz ./output/

# 备份数据库
docker-compose exec postgres pg_dump -U webis webis | gzip > db_$(date +%Y%m%d).sql.gz
```

## 🚀 升级

```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```

## 🔒 安全建议

1. **使用强密码** — 修改默认的 PostgreSQL 和 Redis 密码
2. **限制端口暴露** — 生产环境只暴露 80/443
3. **使用 `.env`** — 不要在 `docker-compose.yml` 中硬编码密钥
4. **定期更新** — 保持基础镜像和依赖最新
5. **备份数据** — 定期备份 `output/` 和数据库

---

更多信息：
- [部署指南](deployment.md) — 生产环境部署
- [用户指南](user-guide.md) — 完整功能说明
- [快速开始](quickstart.md) — 5 分钟上手
