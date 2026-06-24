FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY src/ src/
COPY public/ public/
COPY scripts/ scripts/
COPY next.config.ts tsconfig.json postcss.config.mjs eslint.config.mjs tokens.css components.json ./

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=$NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID

RUN test -n "$NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID" && \
    test "$NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID" != "pocketagent-local" && \
    test "$NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID" != "your-walletconnect-project-id"

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
