#!/bin/bash

# AI Web MCP Mode 服务启动脚本
# 用于启动前后台服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# PID文件路径
BACKEND_PID_FILE="$PROJECT_ROOT/backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/frontend.pid"

# 日志文件路径
BACKEND_LOG_FILE="$PROJECT_ROOT/logs/backend.log"
FRONTEND_LOG_FILE="$PROJECT_ROOT/logs/frontend.log"

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

# 函数：打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# 函数：检查服务是否运行
is_service_running() {
    local pid_file=$1
    local service_name=$2
    local port=$3
    
    # 首先检查PID文件
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    
    # 检查端口是否被占用
    if [ -n "$port" ]; then
        local port_pid=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$port_pid" ]; then
            # 检查是否是我们的服务进程
            local process_info=$(ps -p "$port_pid" -o comm= 2>/dev/null || echo "")
            if [[ "$process_info" == *"uvicorn"* ]] || [[ "$process_info" == *"python"* ]]; then
                return 0
            fi
        fi
    fi
    
    # 检查进程名称
    if [ "$service_name" = "后端" ]; then
        local service_pid=$(pgrep -f "uvicorn main:app" 2>/dev/null | head -1 || true)
        if [ -n "$service_pid" ]; then
            return 0
        fi
    elif [ "$service_name" = "前端" ]; then
        local service_pid=$(pgrep -f "python -m http.server 3000" 2>/dev/null | head -1 || true)
        if [ -n "$service_pid" ]; then
            return 0
        fi
    fi
    
    return 1
}

# 函数：启动后端服务
start_backend() {
    print_message $BLUE "正在启动后端服务..."
    
    # 调用专门的后端启动脚本
    if "$PROJECT_ROOT/start_backend.sh"; then
        print_message $GREEN "后端服务启动完成"
        return 0
    else
        print_message $RED "后端服务启动失败"
        return 1
    fi
}

# 函数：启动前端服务
start_frontend() {
    print_message $BLUE "正在启动前端服务..."
    
    # 调用专门的前端启动脚本
    if "$PROJECT_ROOT/start_frontend.sh"; then
        print_message $GREEN "前端服务启动完成"
        return 0
    else
        print_message $RED "前端服务启动失败"
        return 1
    fi
}

# 函数：显示使用帮助
show_help() {
    echo "AI Web MCP Mode 服务启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start     启动所有服务 (默认)"
    echo "  backend   仅启动后端服务"
    echo "  frontend  仅启动前端服务"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                # 启动所有服务"
    echo "  $0 start          # 启动所有服务"
    echo "  $0 backend        # 仅启动后端"
    echo "  $0 frontend       # 仅启动前端"
}

# 主函数
main() {
    local action=${1:-start}
    
    case $action in
        "start")
            print_message $GREEN "=== AI Web MCP Mode 服务启动 ==="
            start_backend
            start_frontend
            print_message $GREEN "=== 所有服务启动完成 ==="
            print_message $BLUE "访问地址: http://localhost:3000"
            exit 0
            ;;
        "backend")
            print_message $GREEN "=== 启动后端服务 ==="
            start_backend
            exit 0
            ;;
        "frontend")
            print_message $GREEN "=== 启动前端服务 ==="
            start_frontend
            exit 0
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_message $RED "错误: 未知选项 '$action'"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
