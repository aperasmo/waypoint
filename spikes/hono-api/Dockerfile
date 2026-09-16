# syntax=docker/dockerfile:1

FROM node:24-alpine AS builder

WORKDIR /app/spikes/hono-api

COPY spikes/hono-api/package.json spikes/hono-api/package-lock.json ./
RUN npm ci

COPY spikes/hono-api/tsconfig.json ./
COPY spikes/hono-api/src ./src

RUN npm run build


FROM node:24-alpine AS runtime

WORKDIR /app/spikes/hono-api

ENV NODE_ENV=production

COPY spikes/hono-api/package.json spikes/hono-api/package-lock.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/spikes/hono-api/dist ./dist

# The browse taxonomy remains authored once at data/categories.json.
# The image receives a runtime copy from that canonical repository file.
COPY data/categories.json /app/data/categories.json

EXPOSE 8200

USER node

CMD ["npm", "start"]