# --- Giai đoạn 1: build giao diện React ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

# --- Giai đoạn 2: Nginx không đặc quyền (chạy bằng người dùng uid 101, nghe cổng 8080/8443) ---
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
