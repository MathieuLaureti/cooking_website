FROM node:20-alpine AS console-build

WORKDIR /app

COPY console/package.json console/package-lock.json ./
RUN npm ci

COPY console/ ./
RUN npm run build

FROM nginx:1.29.3-alpine

COPY --from=console-build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
