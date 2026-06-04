# Self-hosted Phoenix (local + VPS)

Why this exists: **Phoenix Cloud free tier is 25,000 spans/month.** RAT-2 measured ~41 spans per A2A round-trip, so a full Phoenix Audit run with 47 tests emits ~1,927 spans. Free tier supports ~13 audits/month, which dev iteration burns through in a day.

Self-hosting Phoenix runs on a single Docker container with a persistent volume. Free, unlimited, identical UI to Phoenix Cloud. We use this for development + the VPS-hosted dev environment. We use Phoenix Cloud only for the final demo recording + judging-window deployment.

## Local quickstart (laptop)

Prereq: Colima running OR Docker Desktop installed.

```bash
cd infra/phoenix-self-host
docker compose up -d
```

Wait ~15 seconds for the healthcheck to pass, then:

```bash
curl http://localhost:6006/healthz    # → "ok"
open http://localhost:6006            # → Phoenix UI in browser
```

To point Phoenix Audit's smoke scripts at local Phoenix instead of Phoenix Cloud, set in your shell or in `~/.config/phoenix-rat/.env`:

```
PHOENIX_API_KEY=local-dev-key-unused
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
```

Then re-run any RAT-2 smoke script — traces land in the local Phoenix UI, not Phoenix Cloud.

## Stop

```bash
docker compose down           # stops + removes containers, KEEPS data
docker compose down -v        # also destroys the persistent volume (data gone)
```

## VPS deployment (later)

When you're ready to host Phoenix on your VPS:

```bash
# On the VPS (SSH'd in):
mkdir -p /srv/phoenix
# Copy these files over
scp -r infra/phoenix-self-host abu@<vps-ip>:/srv/phoenix/

ssh abu@<vps-ip>
cd /srv/phoenix
# IMPORTANT for VPS: turn on auth + set a strong secret BEFORE bringing up
export PHOENIX_ENABLE_AUTH=true
export PHOENIX_SECRET="$(openssl rand -base64 32)"
export PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD="<choose-a-strong-password>"
docker compose up -d
```

Then put nginx (or Caddy) in front of port 6006 with TLS for `phoenix.your-vps.com`. Do NOT expose port 4317 (OTLP gRPC) publicly — only 6006 (the OTLP-HTTP path is on 6006/v1/traces).

## Switching between Cloud and self-host

We use both:
- **Cloud** (`https://app.phoenix.arize.com/...`) — for the final demo recording + judging window (Jun 22 - Jul 6). Phoenix Audit's deployed Cloud Run service points here.
- **Self-host** (local Docker or VPS) — for everything else: development, RAT smoke runs, regression tests, daily build iteration.

Switch by changing `PHOENIX_COLLECTOR_ENDPOINT` env var. No code changes needed.

## References

- Phoenix self-host docs: https://arize.com/docs/phoenix/deployment/deploying-phoenix
- Docker image: https://hub.docker.com/r/arizephoenix/phoenix
