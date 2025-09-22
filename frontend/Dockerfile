# 前端Dockerfile
FROM nginx:alpine

# 复制前端文件到nginx目录
COPY . /usr/share/nginx/html/

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]
