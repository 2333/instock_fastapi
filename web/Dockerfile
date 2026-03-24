FROM node:20-alpine AS builder

ARG APP_VERSION=dev
ARG APP_GIT_SHA=local

WORKDIR /app

ENV VITE_APP_VERSION=${APP_VERSION}
ENV VITE_APP_GIT_SHA=${APP_GIT_SHA}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

ARG APP_VERSION=dev
ARG APP_GIT_SHA=local

LABEL org.opencontainers.image.title="instock-web"
LABEL org.opencontainers.image.version="${APP_VERSION}"
LABEL org.opencontainers.image.revision="${APP_GIT_SHA}"
LABEL org.opencontainers.image.source="https://github.com/2333/instock_fastapi"

ENV APP_VERSION=${APP_VERSION}
ENV APP_GIT_SHA=${APP_GIT_SHA}

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
