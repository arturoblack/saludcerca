# 1) Compila la PWA de React con Vite.
FROM node:20-alpine AS build
WORKDIR /web
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
# Variables de compilación (modo demo por defecto)
ARG VITE_AUTH_MODE=dev
ARG VITE_API_BASE_URL=
ARG VITE_OIDC_AUTHORITY=
ARG VITE_OIDC_TOKEN_URL=
ARG VITE_OIDC_CLIENT_ID=saludcerca-web
ENV VITE_AUTH_MODE=$VITE_AUTH_MODE VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_OIDC_AUTHORITY=$VITE_OIDC_AUTHORITY VITE_OIDC_TOKEN_URL=$VITE_OIDC_TOKEN_URL VITE_OIDC_CLIENT_ID=$VITE_OIDC_CLIENT_ID
RUN npm run build

# 2) Sirve los archivos estáticos con nginx y reenvía /api al contenedor de la API.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 8080
