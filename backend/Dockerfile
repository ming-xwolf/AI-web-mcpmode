# 后端Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# 设置pip使用国内镜像源加速下载
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_EXTRA_INDEX_URL=https://pypi.org/simple
# 禁用pip缓存以减小镜像大小
ENV PIP_NO_CACHE_DIR=1
# 设置pip超时时间
ENV PIP_TIMEOUT=100
ENV PIP_DEFAULT_TIMEOUT=100

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 升级pip到最新版本
RUN pip install --upgrade pip

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖 - 使用国内镜像源加速
RUN pip install --no-cache-dir --timeout=100 \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://pypi.org/simple \
    -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8003

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/api/status || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
