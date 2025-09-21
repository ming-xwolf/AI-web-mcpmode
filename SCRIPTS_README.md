# AI Web MCP Mode 服务管理脚本

本项目提供了完整的服务管理脚本，用于启动、停止、重启和监控前后台服务。

## 脚本文件

### Linux/macOS 脚本
- `start.sh` - 启动服务脚本
- `stop.sh` - 停止服务脚本  
- `restart.sh` - 重启服务脚本
- `status.sh` - 状态检查脚本


## 使用方法

### 启动服务

#### Linux/macOS
```bash
# 启动所有服务
./start.sh
# 或者
./start.sh start

# 仅启动后端服务
./start.sh backend

# 仅启动前端服务
./start.sh frontend

# 显示帮助
./start.sh help
```


### 停止服务

#### Linux/macOS
```bash
# 停止所有服务
./stop.sh
# 或者
./stop.sh stop

# 仅停止后端服务
./stop.sh backend

# 仅停止前端服务
./stop.sh frontend

# 停止所有相关进程（包括非PID文件管理的进程）
./stop.sh all

# 显示帮助
./stop.sh help
```


### 重启服务

#### Linux/macOS
```bash
# 重启所有服务
./restart.sh
# 或者
./restart.sh restart

# 仅重启后端服务
./restart.sh backend

# 仅重启前端服务
./restart.sh frontend

# 显示帮助
./restart.sh help
```


### 检查服务状态

#### Linux/macOS
```bash
# 检查所有服务状态
./status.sh
# 或者
./status.sh status

# 仅检查后端服务状态
./status.sh backend

# 仅检查前端服务状态
./status.sh frontend

# 检查端口占用情况
./status.sh ports

# 显示日志信息
./status.sh logs

# 显示系统信息
./status.sh system

# 显示所有信息
./status.sh all

# 显示帮助
./status.sh help
```


## 服务配置

### 后端服务
- **端口**: 8003
- **地址**: http://localhost:8003
- **环境**: conda环境 `ai-web-mcpmode`
- **启动命令**: `uvicorn main:app --reload --host 0.0.0.0 --port 8003`

### 前端服务
- **端口**: 3000
- **地址**: http://localhost:3000
- **启动命令**: `python -m http.server 3000`

## 文件结构

```
项目根目录/
├── start.sh          # 启动脚本
├── stop.sh           # 停止脚本
├── restart.sh        # 重启脚本
├── status.sh         # 状态检查脚本
├── backend.pid       # 后端服务PID文件
├── frontend.pid      # 前端服务PID文件
└── logs/             # 日志目录
    ├── backend.log   # 后端服务日志
    └── frontend.log  # 前端服务日志
```

## 环境要求

- Bash shell
- Python 3.11
- Conda环境 `ai-web-mcpmode`
- 必要的Python依赖包

## 注意事项

1. **环境变量**: 确保已创建 `.env` 文件并配置必要的环境变量
2. **Conda环境**: 脚本会自动激活 `ai-web-mcpmode` conda环境
3. **端口占用**: 确保端口8003和3000未被其他程序占用
4. **权限**: 脚本需要执行权限
5. **日志**: 所有服务日志都保存在 `logs/` 目录中
6. **PID文件**: 脚本使用PID文件来跟踪服务状态

## 故障排除

### 常见问题

1. **服务启动失败**
   - 检查conda环境是否正确安装
   - 检查端口是否被占用
   - 查看日志文件获取详细错误信息

2. **服务无法停止**
   - 使用 `stop.sh all` 强制停止所有相关进程
   - 手动删除PID文件

3. **端口占用**
   - 使用 `status.sh ports` 检查端口占用情况
   - 使用 `stop.sh all` 停止所有相关进程

4. **权限问题**
   - 确保脚本有执行权限: `chmod +x *.sh`

### 日志查看

```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log

# 查看所有日志
tail -f logs/*.log
```

## 开发建议

1. 在开发过程中，建议使用 `./start.sh` 启动服务
2. 使用 `./status.sh` 定期检查服务状态
3. 遇到问题时，先查看日志文件
4. 使用 `./restart.sh` 重启服务以应用更改
5. 开发完成后，使用 `./stop.sh` 停止服务
