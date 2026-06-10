# phoenix-audit-web — the real Next.js app (standalone output).
# Build context is the REPO ROOT (pnpm workspace): staging-deploy.yaml passes
# context: . and this file via matrix.dockerfile.

FROM node:20-alpine AS deps
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/phoenix-audit-web/package.json apps/phoenix-audit-web/
RUN pnpm install --frozen-lockfile --filter phoenix-audit-web...

FROM node:20-alpine AS build
RUN corepack enable
WORKDIR /repo
COPY --from=deps /repo ./
COPY apps/phoenix-audit-web apps/phoenix-audit-web
# Telemetry off in CI builds; standalone output is configured in next.config.ts.
ENV NEXT_TELEMETRY_DISABLED=1
# Firebase client config (story-9.4) — inlined into the client bundle at
# build time. Public identifiers, not secrets: security lives in token
# verification, not in hiding the apiKey.
ARG NEXT_PUBLIC_FIREBASE_API_KEY
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID
ENV NEXT_PUBLIC_FIREBASE_API_KEY=$NEXT_PUBLIC_FIREBASE_API_KEY \
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=$NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN \
    NEXT_PUBLIC_FIREBASE_PROJECT_ID=$NEXT_PUBLIC_FIREBASE_PROJECT_ID
RUN pnpm --filter phoenix-audit-web build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# Server-side code (proxy.ts, route handlers) reads these from RUNTIME env —
# build-time inlining only covers the client bundle. Same values as build.
ARG NEXT_PUBLIC_FIREBASE_API_KEY
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID
ENV NEXT_PUBLIC_FIREBASE_API_KEY=$NEXT_PUBLIC_FIREBASE_API_KEY \
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=$NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN \
    NEXT_PUBLIC_FIREBASE_PROJECT_ID=$NEXT_PUBLIC_FIREBASE_PROJECT_ID
# Cloud Run injects PORT; Next standalone reads PORT + HOSTNAME.
ENV HOSTNAME=0.0.0.0
ENV PORT=8080

RUN addgroup -S app && adduser -S -G app app

# Monorepo standalone layout: server.js lives under apps/phoenix-audit-web/.
COPY --from=build --chown=app:app /repo/apps/phoenix-audit-web/.next/standalone ./
COPY --from=build --chown=app:app /repo/apps/phoenix-audit-web/.next/static ./apps/phoenix-audit-web/.next/static
COPY --from=build --chown=app:app /repo/apps/phoenix-audit-web/public ./apps/phoenix-audit-web/public

USER app
EXPOSE 8080

CMD ["node", "apps/phoenix-audit-web/server.js"]
