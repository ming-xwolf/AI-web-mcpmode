# Docker 部署指南

本项目支持使用 Docker 和 Docker Compose 进行容器化部署。

## 文件结构

```
├── docker-compose.yml          # Docker Compose 配置文件
├── env.example                 # 环境变量示例文件
├── .dockerignore              # Docker 忽略文件
├── backend/
│   ├── Dockerfile             # 后端 Docker 镜像构建文件
│   ├── .dockerignore          # 后端 Docker 忽略文件
│   └── ...
├── frontend/
│   ├── Dockerfile             # 前端 Docker 镜像构建文件
│   ├── nginx.conf             # Nginx 配置文件
│   ├── .dockerignore          # 前端 Docker 忽略文件
│   └── ...
```

## 快速开始

### 1. 环境准备

确保已安装：
- Docker (版本 20.10+)
- Docker Compose (版本 2.0+)

### 2. 配置环境变量

复制环境变量示例文件：
```bash
cp env.example .env
```

编辑 `.env` 文件，配置必要的环境变量：
```bash
# 必须配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 可选配置
BACKEND_PORT=8003
POSTGRES_DB=ai_web_mcpmode
POSTGRES_USER=ai_web_user
POSTGRES_PASSWORD=ai_web_password
```

### 3. 启动服务

启动所有服务：
```bash
docker-compose up -d
```

查看服务状态：
```bash
docker-compose ps
```

查看日志：
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend
```

### 4. 访问应用

- 前端：http://localhost
- 后端API：http://localhost:8003
- 后端健康检查：http://localhost:8003/api/status

## 服务说明

### 后端服务 (backend)
- **端口**: 8003
- **镜像**: 基于 Python 3.11-slim
- **功能**: FastAPI 应用，提供 WebSocket 和 REST API
- **数据卷**: 
  - `./backend/data:/app/data` - 数据目录
  - `./backend/chat_history.db:/app/chat_history.db` - 数据库文件
  - `./backend/mcp.json:/app/mcp.json` - MCP 配置文件

### 前端服务 (frontend)
- **端口**: 80
- **镜像**: 基于 Nginx Alpine
- **功能**: 静态文件服务和 API 代理
- **特性**: 
  - Gzip 压缩
  - 静态资源缓存
  - API 代理到后端
  - WebSocket 代理

### 数据库服务 (db) - 可选
- **端口**: 5432 (内部)
- **镜像**: PostgreSQL 15 Alpine
- **功能**: 关系型数据库存储
- **数据卷**: `postgres_data` - 持久化数据

### Redis 服务 (redis) - 可选
- **端口**: 6379
- **镜像**: Redis 7 Alpine
- **功能**: 缓存和会话存储
- **数据卷**: `redis_data` - 持久化数据

## 常用命令

### 服务管理
```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 重启特定服务
docker-compose restart backend

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f backend
```

### 构建和更新
```bash
# 重新构建镜像
docker-compose build

# 强制重新构建
docker-compose build --no-cache

# 更新并启动
docker-compose up -d --build
```

### 数据管理
```bash
# 备份数据库
docker-compose exec db pg_dump -U ai_web_user ai_web_mcpmode > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U ai_web_user ai_web_mcpmode < backup.sql

# 清理数据卷
docker-compose down -v
```

### 调试和监控
```bash
# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh

# 查看资源使用情况
docker-compose top

# 查看网络
docker network ls
docker network inspect ai-web-mcpmode_ai-web-network
```

## 生产环境部署

### 1. 安全配置

更新 `.env` 文件中的安全配置：
```bash
# 生成强密码
JWT_SECRET_KEY=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
```

### 2. 网络配置

在生产环境中，建议：
- 使用反向代理 (如 Nginx)
- 配置 SSL/TLS 证书
- 限制端口暴露
- 使用 Docker Secrets 管理敏感信息

### 3. 监控和日志

建议配置：
- 日志收集 (如 ELK Stack)
- 监控系统 (如 Prometheus + Grafana)
- 健康检查端点
- 自动重启策略

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :8003
   netstat -tulpn | grep :80
   
   # 修改端口
   # 编辑 docker-compose.yml 中的 ports 配置
   ```

2. **权限问题**
   ```bash
   # 修复文件权限
   sudo chown -R $USER:$USER ./backend/data
   ```

3. **数据库连接问题**
   ```bash
   # 检查数据库状态
   docker-compose exec db pg_isready -U ai_web_user
   
   # 查看数据库日志
   docker-compose logs db
   ```

4. **内存不足**
   ```bash
   # 查看容器资源使用
   docker stats
   
   # 增加 Docker 内存限制
   # 编辑 docker-compose.yml 添加 resources 配置
   ```

### 日志分析

```bash
# 查看错误日志
docker-compose logs --tail=100 backend | grep ERROR

# 实时监控日志
docker-compose logs -f --tail=50

# 导出日志
docker-compose logs > app.log
```

## 开发环境

### 热重载开发

对于开发环境，可以使用以下配置：

```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

启动开发环境：
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 性能优化

### 1. 镜像优化
- 使用多阶段构建
- 减少镜像层数
- 使用 .dockerignore 排除不必要文件

### 2. 网络优化
- 使用自定义网络
- 配置 DNS 解析
- 优化容器间通信

### 3. 存储优化
- 使用命名卷
- 配置适当的挂载选项
- 定期清理无用数据

## 备份和恢复

### 数据备份
```bash
# 创建备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec db pg_dump -U ai_web_user ai_web_mcpmode > "backup_${DATE}.sql"
```

### 数据恢复
```bash
# 恢复数据库
docker-compose exec -T db psql -U ai_web_user ai_web_mcpmode < backup_20240101_120000.sql
```

## 更新和维护

### 定期维护
```bash
# 清理无用镜像
docker image prune -f

# 清理无用容器
docker container prune -f

# 清理无用卷
docker volume prune -f

# 清理无用网络
docker network prune -f
```

### 应用更新
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 验证更新
curl http://localhost/api/status
```
