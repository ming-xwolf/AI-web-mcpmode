#!/bin/bash

# AI Web MCP Mode 服务重启脚本
# 用于重启前后台服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 函数：打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# 函数：显示使用帮助
show_help() {
    echo "AI Web MCP Mode 服务重启脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  restart   重启所有服务 (默认)"
    echo "  backend   仅重启后端服务"
    echo "  frontend  仅重启前端服务"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                # 重启所有服务"
    echo "  $0 restart        # 重启所有服务"
    echo "  $0 backend        # 仅重启后端"
    echo "  $0 frontend       # 仅重启前端"
}

# 主函数
main() {
    local action=${1:-restart}
    
    case $action in
        "restart")
            print_message $GREEN "=== AI Web MCP Mode 服务重启 ==="
            print_message $BLUE "步骤 1/4: 停止所有服务..."
            "$PROJECT_ROOT/stop.sh" all
            sleep 2
            print_message $BLUE "步骤 2/4: 等待服务完全停止..."
            sleep 3
            print_message $BLUE "步骤 3/4: 启动所有服务..."
            "$PROJECT_ROOT/start.sh" start
            print_message $BLUE "步骤 4/4: 检查服务状态..."
            sleep 2
            "$PROJECT_ROOT/status.sh"
            print_message $GREEN "=== 服务重启完成 ==="
            ;;
        "backend")
            print_message $GREEN "=== 重启后端服务 ==="
            print_message $BLUE "停止后端服务..."
            "$PROJECT_ROOT/stop.sh" backend
            sleep 2
            print_message $BLUE "启动后端服务..."
            "$PROJECT_ROOT/start.sh" backend
            print_message $GREEN "=== 后端服务重启完成 ==="
            ;;
        "frontend")
            print_message $GREEN "=== 重启前端服务 ==="
            print_message $BLUE "停止前端服务..."
            "$PROJECT_ROOT/stop.sh" frontend
            sleep 2
            print_message $BLUE "启动前端服务..."
            "$PROJECT_ROOT/start.sh" frontend
            print_message $GREEN "=== 前端服务重启完成 ==="
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
