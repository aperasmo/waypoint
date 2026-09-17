# syntax=docker/dockerfile:1

# Build the React application with the dependency versions locked by
# package-lock.json. Node and npm do not exist in the final runtime image.
FROM node:24-alpine AS builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

ARG VITE_API_BASE_URL
ARG VITE_BROWSE_API_BASE_URL

# Vite embeds these values into the browser bundle during the build.
# Fail early rather than publishing a frontend with missing API routing.
RUN test -n "$VITE_API_BASE_URL" && \
    test -n "$VITE_BROWSE_API_BASE_URL" && \
    VITE_API_BASE_URL="$VITE_API_BASE_URL" \
    VITE_BROWSE_API_BASE_URL="$VITE_BROWSE_API_BASE_URL" \
    npm run build


# Serve only the compiled static application using NGINX's non-root image.
FROM nginxinc/nginx-unprivileged:1.30.4-alpine AS runtime


COPY frontend/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

EXPOSE 8080
