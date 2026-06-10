# Stub Dockerfile for phoenix-audit-web. Real Next.js scaffold lands with S7.1
# (Tailwind 4 + visx + Framer Motion 12 — see PRD §"Demo moment").
# For now this image just runs a tiny health server on :8080 so the
# staging-deploy workflow can exercise the WIF → Cloud Run path
# end-to-end without waiting on the frontend stack.

FROM node:20-alpine AS runtime

WORKDIR /app

# Minimal health-only Node server. Replaced by Next.js standalone output
# from `pnpm build` in S7.1.
RUN <<'EOF' cat > /app/server.mjs
import { createServer } from 'node:http';

const PORT = process.env.PORT || 8080;
createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'phoenix-audit-web', stub: true }));
    return;
  }
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('phoenix-audit-web stub — real frontend lands in S7.1\n');
}).listen(PORT, () => console.log(`stub server listening on :${PORT}`));
EOF

EXPOSE 8080

# Run as non-root.
RUN addgroup -S app && adduser -S -G app app
USER app

CMD ["node", "/app/server.mjs"]
