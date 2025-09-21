#!/bin/bash

# AI Web MCP Mode 服务状态检查脚本
# 用于检查前后台服务运行状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
    echo -e "${color}${message}${NC}"
}

# 函数：检查服务状态
check_service_status() {
    local pid_file=$1
    local service_name=$2
    local port=$3
    local url=$4
    
    # 首先检查PID文件
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_message $GREEN "✓ $service_name 服务正在运行 (PID文件管理)"
            print_message $BLUE "  PID: $pid"
            print_message $BLUE "  端口: $port"
            print_message $BLUE "  地址: $url"
            
            # 检查端口是否可访问
            if command -v curl > /dev/null 2>&1; then
                if curl -s "$url" > /dev/null 2>&1; then
                    print_message $GREEN "  ✓ 服务可访问"
                else
                    print_message $YELLOW "  ⚠ 服务可能未完全启动"
                fi
            fi
            return 0
        else
            print_message $YELLOW "⚠ PID文件存在但进程不存在，清理PID文件"
            rm -f "$pid_file"
        fi
    fi
    
    # 如果没有PID文件或PID文件中的进程不存在，尝试通过端口检测
    local port_pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$port_pid" ]; then
        # 检查是否是我们的服务进程
        local process_info=$(ps -p "$port_pid" -o comm= 2>/dev/null || echo "")
        if [[ "$process_info" == *"uvicorn"* ]] || [[ "$process_info" == *"python"* ]]; then
            print_message $GREEN "✓ $service_name 服务正在运行 (端口检测)"
            print_message $BLUE "  PID: $port_pid"
            print_message $BLUE "  端口: $port"
            print_message $BLUE "  地址: $url"
            print_message $YELLOW "  ⚠ 服务未通过脚本管理 (无PID文件)"
            
            # 检查端口是否可访问
            if command -v curl > /dev/null 2>&1; then
                if curl -s "$url" > /dev/null 2>&1; then
                    print_message $GREEN "  ✓ 服务可访问"
                else
                    print_message $YELLOW "  ⚠ 服务可能未完全启动"
                fi
            fi
            return 0
        fi
    fi
    
    # 如果都没有找到，检查是否有相关进程在运行
    local service_pid=""
    if [ "$service_name" = "后端" ]; then
        service_pid=$(pgrep -f "uvicorn main:app" 2>/dev/null | head -1 || true)
    elif [ "$service_name" = "前端" ]; then
        service_pid=$(pgrep -f "python -m http.server 3000" 2>/dev/null | head -1 || true)
    fi
    
    if [ -n "$service_pid" ]; then
        print_message $GREEN "✓ $service_name 服务正在运行 (进程检测)"
        print_message $BLUE "  PID: $service_pid"
        print_message $BLUE "  端口: $port"
        print_message $BLUE "  地址: $url"
        print_message $YELLOW "  ⚠ 服务未通过脚本管理 (无PID文件)"
        
        # 检查端口是否可访问
        if command -v curl > /dev/null 2>&1; then
            if curl -s "$url" > /dev/null 2>&1; then
                print_message $GREEN "  ✓ 服务可访问"
            else
                print_message $YELLOW "  ⚠ 服务可能未完全启动"
            fi
        fi
        return 0
    fi
    
    print_message $RED "✗ $service_name 服务未运行"
    return 1
}

# 函数：检查端口占用
check_port_usage() {
    local port=$1
    local service_name=$2
    
    if command -v lsof > /dev/null 2>&1; then
        local pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            # 检查是否是我们的服务进程
            local is_our_service=false
            for pid in $pids; do
                local process_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
                if [[ "$process_info" == *"uvicorn"* ]] || [[ "$process_info" == *"python"* ]]; then
                    is_our_service=true
                    break
                fi
            done
            
            if [ "$is_our_service" = true ]; then
                print_message $GREEN "✓ 端口 $port 被我们的服务占用"
                for pid in $pids; do
                    local process_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "未知进程")
                    if [[ "$process_info" == *"uvicorn"* ]] || [[ "$process_info" == *"python"* ]]; then
                        print_message $BLUE "  PID: $pid ($process_info)"
                    fi
                done
            else
                print_message $YELLOW "⚠ 端口 $port 被其他进程占用"
                for pid in $pids; do
                    local process_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "未知进程")
                    print_message $YELLOW "  PID: $pid ($process_info)"
                done
            fi
        else
            print_message $BLUE "✓ 端口 $port 可用"
        fi
    fi
}

# 函数：显示系统信息
show_system_info() {
    print_message $CYAN "=== 系统信息 ==="
    
    # 操作系统
    if [ -f /etc/os-release ]; then
        local os_name=$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)
        print_message $BLUE "操作系统: $os_name"
    elif command -v uname > /dev/null 2>&1; then
        print_message $BLUE "操作系统: $(uname -s)"
    fi
    
    # Python版本
    if command -v python3 > /dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1)
        print_message $BLUE "Python: $python_version"
    fi
    
    # Conda环境
    if command -v conda > /dev/null 2>&1; then
        local conda_env=$(conda info --envs | grep '*' | awk '{print $1}' 2>/dev/null || echo "未激活")
        print_message $BLUE "Conda环境: $conda_env"
    fi
    
    # 内存使用
    if command -v free > /dev/null 2>&1; then
        local memory_info=$(free -h | grep Mem | awk '{print "已用: " $3 " / " $2}')
        print_message $BLUE "内存: $memory_info"
    fi
    
    # 磁盘使用
    if command -v df > /dev/null 2>&1; then
        local disk_info=$(df -h . | tail -1 | awk '{print "已用: " $3 " / " $2 " (" $5 ")"}')
        print_message $BLUE "磁盘: $disk_info"
    fi
}

# 函数：显示日志信息
show_log_info() {
    print_message $CYAN "=== 日志信息 ==="
    
    local backend_log="$PROJECT_ROOT/logs/backend.log"
    local frontend_log="$PROJECT_ROOT/logs/frontend.log"
    
    if [ -f "$backend_log" ]; then
        local backend_size=$(du -h "$backend_log" | cut -f1)
        print_message $BLUE "后端日志: $backend_log ($backend_size)"
        if [ -s "$backend_log" ]; then
            print_message $YELLOW "最近5行后端日志:"
            tail -5 "$backend_log" | sed 's/^/  /'
        fi
    else
        print_message $YELLOW "后端日志文件不存在"
    fi
    
    echo ""
    
    if [ -f "$frontend_log" ]; then
        local frontend_size=$(du -h "$frontend_log" | cut -f1)
        print_message $BLUE "前端日志: $frontend_log ($frontend_size)"
        if [ -s "$frontend_log" ]; then
            print_message $YELLOW "最近5行前端日志:"
            tail -5 "$frontend_log" | sed 's/^/  /'
        fi
    else
        print_message $YELLOW "前端日志文件不存在"
    fi
}

# 函数：显示使用帮助
show_help() {
    echo "AI Web MCP Mode 服务状态检查脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  status    检查所有服务状态 (默认)"
    echo "  backend   仅检查后端服务状态"
    echo "  frontend  仅检查前端服务状态"
    echo "  ports     检查端口占用情况"
    echo "  logs      显示日志信息"
    echo "  system    显示系统信息"
    echo "  all       显示所有信息"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                # 检查所有服务状态"
    echo "  $0 status         # 检查所有服务状态"
    echo "  $0 backend        # 仅检查后端状态"
    echo "  $0 ports          # 检查端口占用"
    echo "  $0 logs           # 显示日志信息"
    echo "  $0 all            # 显示所有信息"
}

# 主函数
main() {
    local action=${1:-status}
    
    case $action in
        "status")
            print_message $GREEN "=== AI Web MCP Mode 服务状态 ==="
            check_service_status "$BACKEND_PID_FILE" "后端" "8003" "http://localhost:8003"
            echo ""
            check_service_status "$FRONTEND_PID_FILE" "前端" "3000" "http://localhost:3000"
            ;;
        "backend")
            print_message $GREEN "=== 后端服务状态 ==="
            check_service_status "$BACKEND_PID_FILE" "后端" "8003" "http://localhost:8003"
            ;;
        "frontend")
            print_message $GREEN "=== 前端服务状态 ==="
            check_service_status "$FRONTEND_PID_FILE" "前端" "3000" "http://localhost:3000"
            ;;
        "ports")
            print_message $GREEN "=== 端口占用检查 ==="
            check_port_usage "8003" "后端"
            check_port_usage "3000" "前端"
            ;;
        "logs")
            show_log_info
            ;;
        "system")
            show_system_info
            ;;
        "all")
            print_message $GREEN "=== AI Web MCP Mode 完整状态报告 ==="
            echo ""
            show_system_info
            echo ""
            print_message $GREEN "=== 服务状态 ==="
            check_service_status "$BACKEND_PID_FILE" "后端" "8003" "http://localhost:8003"
            echo ""
            check_service_status "$FRONTEND_PID_FILE" "前端" "3000" "http://localhost:3000"
            echo ""
            print_message $GREEN "=== 端口占用 ==="
            check_port_usage "8003" "后端"
            check_port_usage "3000" "前端"
            echo ""
            show_log_info
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
