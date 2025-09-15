FROM nginx:stable-alpine

WORKDIR /usr/share/nginx/html

# Remove default nginx content
RUN rm -rf ./*

# Copy frontend static files
COPY frontend/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
