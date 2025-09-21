#!/bin/bash

# AI Web MCP Mode 服务停止脚本
# 用于停止前后台服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# PID文件路径
BACKEND_PID_FILE="$PROJECT_ROOT/backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/frontend.pid"

# 函数：打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# 函数：停止服务
stop_service() {
    local pid_file=$1
    local service_name=$2
    local port=$3
    
    local service_pid=""
    local found_via_pid_file=false
    
    # 首先检查PID文件
    if [ -f "$pid_file" ]; then
        service_pid=$(cat "$pid_file")
        if ps -p "$service_pid" > /dev/null 2>&1; then
            found_via_pid_file=true
        else
            rm -f "$pid_file"
        fi
    fi
    
    # 如果没有通过PID文件找到，尝试其他方式
    if [ -z "$service_pid" ]; then
        # 检查端口占用
        if [ -n "$port" ]; then
            local port_pid=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$port_pid" ]; then
                local process_info=$(ps -p "$port_pid" -o comm= 2>/dev/null || echo "")
                if [[ "$process_info" == *"uvicorn"* ]] || [[ "$process_info" == *"python"* ]]; then
                    service_pid="$port_pid"
                fi
            fi
        fi
        
        # 检查进程名称
        if [ -z "$service_pid" ]; then
            if [ "$service_name" = "后端" ]; then
                service_pid=$(pgrep -f "uvicorn main:app" 2>/dev/null | head -1 || true)
            elif [ "$service_name" = "前端" ]; then
                service_pid=$(pgrep -f "python -m http.server 3000" 2>/dev/null | head -1 || true)
            fi
        fi
    fi
    
    if [ -n "$service_pid" ]; then
        print_message $BLUE "正在停止 $service_name 服务 (PID: $service_pid)..."
        if [ "$found_via_pid_file" = true ]; then
            print_message $BLUE "  (通过PID文件管理)"
        else
            print_message $YELLOW "  (检测到手动启动的服务)"
        fi
        
        kill "$service_pid" 2>/dev/null || true
        
        # 等待进程结束
        local count=0
        while ps -p "$service_pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if ps -p "$service_pid" > /dev/null 2>&1; then
            print_message $YELLOW "强制停止 $service_name 服务..."
            kill -9 "$service_pid" 2>/dev/null || true
            sleep 1
        fi
        
        if ps -p "$service_pid" > /dev/null 2>&1; then
            print_message $RED "$service_name 服务停止失败"
            return 1
        else
            print_message $GREEN "$service_name 服务已停止"
            if [ "$found_via_pid_file" = true ]; then
                rm -f "$pid_file"
            fi
            return 0
        fi
    else
        print_message $YELLOW "$service_name 服务未运行"
        return 0
    fi
}

# 函数：停止所有相关进程
stop_all_processes() {
    print_message $BLUE "检查并停止所有相关进程..."
    
    # 停止uvicorn进程
    local uvicorn_pids=$(pgrep -f "uvicorn main:app" 2>/dev/null || true)
    if [ -n "$uvicorn_pids" ]; then
        print_message $BLUE "发现uvicorn进程，正在停止..."
        echo "$uvicorn_pids" | xargs kill 2>/dev/null || true
    fi
    
    # 停止Python HTTP服务器进程
    local http_pids=$(pgrep -f "python -m http.server 3000" 2>/dev/null || true)
    if [ -n "$http_pids" ]; then
        print_message $BLUE "发现HTTP服务器进程，正在停止..."
        echo "$http_pids" | xargs kill 2>/dev/null || true
    fi
    
    # 停止端口占用的进程
    local port_8003_pid=$(lsof -ti:8003 2>/dev/null || true)
    if [ -n "$port_8003_pid" ]; then
        print_message $BLUE "发现端口8003占用进程，正在停止..."
        kill "$port_8003_pid" 2>/dev/null || true
    fi
    
    local port_3000_pid=$(lsof -ti:3000 2>/dev/null || true)
    if [ -n "$port_3000_pid" ]; then
        print_message $BLUE "发现端口3000占用进程，正在停止..."
        kill "$port_3000_pid" 2>/dev/null || true
    fi
}

# 函数：显示使用帮助
show_help() {
    echo "AI Web MCP Mode 服务停止脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  stop      停止所有服务 (默认)"
    echo "  backend   仅停止后端服务"
    echo "  frontend  仅停止前端服务"
    echo "  all       停止所有相关进程 (包括非PID文件管理的进程)"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                # 停止所有服务"
    echo "  $0 stop           # 停止所有服务"
    echo "  $0 backend        # 仅停止后端"
    echo "  $0 frontend       # 仅停止前端"
    echo "  $0 all            # 停止所有相关进程"
}

# 主函数
main() {
    local action=${1:-stop}
    
    case $action in
        "stop")
            print_message $GREEN "=== AI Web MCP Mode 服务停止 ==="
            stop_service "$BACKEND_PID_FILE" "后端" "8003"
            stop_service "$FRONTEND_PID_FILE" "前端" "3000"
            print_message $GREEN "=== 所有服务停止完成 ==="
            ;;
        "backend")
            print_message $GREEN "=== 停止后端服务 ==="
            stop_service "$BACKEND_PID_FILE" "后端" "8003"
            ;;
        "frontend")
            print_message $GREEN "=== 停止前端服务 ==="
            stop_service "$FRONTEND_PID_FILE" "前端" "3000"
            ;;
        "all")
            print_message $GREEN "=== 停止所有相关进程 ==="
            stop_service "$BACKEND_PID_FILE" "后端"
            stop_service "$FRONTEND_PID_FILE" "前端"
            stop_all_processes
            print_message $GREEN "=== 所有进程停止完成 ==="
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
