#!/bin/bash

# 后端服务启动脚本
# 专门用于启动后端服务

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
BACKEND_PID_FILE="$PROJECT_ROOT/backend.pid"
BACKEND_LOG_FILE="$PROJECT_ROOT/logs/backend.log"

# 函数：打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# 函数：检查服务是否运行
is_service_running() {
    local pid_file=$1
    local port=$2
    
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
    local service_pid=$(pgrep -f "uvicorn main:app" 2>/dev/null | head -1 || true)
    if [ -n "$service_pid" ]; then
        return 0
    fi
    
    return 1
}

# 主函数
main() {
    print_message $BLUE "启动后端服务..."
    
    # 检查服务是否已运行
    if is_service_running "$BACKEND_PID_FILE" "8003"; then
        print_message $YELLOW "后端服务已在运行中"
        local backend_pid=""
        if [ -f "$BACKEND_PID_FILE" ]; then
            backend_pid=$(cat "$BACKEND_PID_FILE")
        else
            backend_pid=$(pgrep -f "uvicorn main:app" 2>/dev/null | head -1 || true)
        fi
        if [ -n "$backend_pid" ]; then
            print_message $BLUE "  PID: $backend_pid"
        fi
        exit 0
    fi
    
    # 检查环境变量文件
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_message $YELLOW "警告: 未找到 .env 文件，请复制 env.example 并配置"
        if [ -f "$PROJECT_ROOT/env.example" ]; then
            cp "$PROJECT_ROOT/env.example" "$PROJECT_ROOT/.env"
            print_message $YELLOW "已创建 .env 文件，请编辑配置"
        fi
    fi
    
    # 启动后端服务
    print_message $BLUE "启动后端服务 (端口: 8003)..."
    cd "$BACKEND_DIR"
    
    # 激活conda环境并启动服务
    source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null || {
        print_message $RED "错误: 无法找到conda，请确保已安装Anaconda或Miniconda"
        exit 1
    }
    
    # 检查并创建conda环境
    if ! conda activate ai-web-mcpmode 2>/dev/null; then
        print_message $YELLOW "conda环境 ai-web-mcpmode 不存在，正在创建..."
        conda create -n ai-web-mcpmode python=3.11 -y || {
            print_message $RED "错误: 无法创建conda环境 ai-web-mcpmode"
            exit 1
        }
        print_message $GREEN "conda环境 ai-web-mcpmode 创建成功"
        
        # 重新激活新创建的环境
        conda activate ai-web-mcpmode || {
            print_message $RED "错误: 无法激活新创建的conda环境 ai-web-mcpmode"
            exit 1
        }
        print_message $GREEN "conda环境 ai-web-mcpmode 激活成功"
    else
        print_message $GREEN "conda环境 ai-web-mcpmode 已存在并激活成功"
    fi
    
    # 检查并安装依赖
    print_message $BLUE "检查Python依赖..."
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        print_message $BLUE "安装/更新Python依赖包..."
        pip install -r "$BACKEND_DIR/requirements.txt" --quiet || {
            print_message $YELLOW "警告: 部分依赖安装可能失败，但继续启动服务"
        }
        print_message $GREEN "依赖检查完成"
    else
        print_message $YELLOW "警告: 未找到 requirements.txt 文件"
    fi
    
    # 使用nohup和bash -c来启动服务，确保环境正确激活
    nohup bash -c "source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null; conda activate ai-web-mcpmode && uvicorn main:app --reload --host 0.0.0.0 --port 8003" > "$BACKEND_LOG_FILE" 2>&1 &
    local backend_pid=$!
    echo $backend_pid > "$BACKEND_PID_FILE"
    
    # 立即分离进程，避免脚本等待
    disown $backend_pid 2>/dev/null || true
    
    # 简单等待服务启动
    print_message $BLUE "等待服务启动..."
    sleep 2
    
    # 检查服务是否启动成功
    if is_service_running "$BACKEND_PID_FILE" "8003"; then
        print_message $GREEN "后端服务启动成功 (PID: $backend_pid)"
        print_message $BLUE "后端日志: $BACKEND_LOG_FILE"
        print_message $BLUE "后端地址: http://localhost:8003"
        exit 0
    else
        print_message $YELLOW "后端服务可能还在启动中，请稍后检查状态"
        print_message $BLUE "后端日志: $BACKEND_LOG_FILE"
        print_message $BLUE "后端地址: http://localhost:8003"
        exit 0
    fi
}

# 执行主函数
main "$@"
