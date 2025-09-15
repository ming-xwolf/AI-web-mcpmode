# 在 Docker 中部署 AI-web-mcpmode

下面是通过 Docker Compose 将当前项目前后端一起运行的最小说明。

准备步骤：

1. 复制并编辑后端环境文件：

   - 进入项目 `backend` 目录，复制 `.env.example` 为 `.env` 并填入 `OPENAI_API_KEY` 等必要字段。

2. 构建并启动服务（在仓库根目录运行）：

   docker-compose up --build -d

3. 访问服务：

   - 前端 (通过 nginx 代理): http://localhost
   - 后端 API (可直接访问): http://localhost:8003

持久化与注意事项：

- SQLite 数据库 `backend/chat_history.db` 已在 `docker-compose.yml` 中映射为主机文件，确保该文件存在并有合适的权限。
- 如果你使用自定义 MCP 服务或 OpenAI 替代品，请编辑 `backend/mcp.json` 和 `backend/.env`。
- WebSocket 路径为 `/ws/chat`，nginx 已配置代理保证 websocket 可用。

问题排查：

- 查看容器日志：

  docker-compose logs -f backend

- 如果端口冲突或需要将 nginx 暴露到其他端口，请修改 `docker-compose.yml` 中的 `ports` 配置。
