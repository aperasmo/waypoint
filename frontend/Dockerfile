# syntax=docker/dockerfile:1

# Build the React application with the dependency versions locked by
# package-lock.json. Node and npm do not exist in the final runtime image.
FROM node:24-alpine AS builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

ARG VITE_API_BASE_URL

# Vite embeds this value into the browser bundle during the build. Fail early
# rather than accidentally publishing a frontend that calls localhost.
RUN test -n "$VITE_API_BASE_URL" && \
    VITE_API_BASE_URL="$VITE_API_BASE_URL" npm run build


# Serve only the compiled static application using NGINX's non-root image.
FROM nginxinc/nginx-unprivileged:1.30.4-alpine AS runtime

# The entrypoint substitutes API_ORIGIN into the NGINX template at startup.
# Production must supply the actual public backend origin.
ENV API_ORIGIN=""

COPY frontend/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

EXPOSE 8080
