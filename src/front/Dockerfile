# 확인용 프런트. ⑦ I-6 모바일 앱은 앱 스토어 배포라 컨테이너 대상이 아니며,
# 이 이미지는 로컬 동작 확인 목적임(배포 단위 표에 없는 추가물).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
