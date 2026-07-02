# syntax=docker/dockerfile:1

# SentinelAI frontend — the Presentation deployment unit (deployment-architecture §5).
# Multi-stage: build the static SPA with Vite, then serve it with nginx, which also
# reverse-proxies the API to the backend so the browser stays same-origin.

# ---- build ----
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite embeds the API base URL at build time. It is set to the published frontend
# origin so the SPA calls same-origin `/api/...`, which nginx proxies to the backend.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---- runtime ----
FROM nginx:alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
