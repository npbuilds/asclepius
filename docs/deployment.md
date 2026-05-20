# Deployment

How to take Asclepius from local dev to live URL. Two services, two platforms, one DNS hand-off.

## Architecture overview

Asclepius is deployed as two independent services:

| Service | Platform | What runs there |
|---|---|---|
| **Web** (Next.js 14) | Vercel | The `/diligence/[asset]` workbench, the methodology page, the landing page. Static + Edge. |
| **API** (FastAPI) | Railway or Fly.io | The four module routes (`/api/modules/pos`, `/rnpv`, `/scorecard`, `/comparables`), the manifest endpoint, the data-source registry. Containerized Python service. |

The frontend talks to the API via Next.js [rewrites](../web/next.config.js) configured by the `ASCLEPIUS_API_BASE` env var. **No CORS headers required** — the rewrite rule makes the API appear to be on the same origin as the web app.

Recommended pairing: **Vercel for web, Railway for api.** Vercel is free for personal projects and ships Next.js with zero config; Railway has a generous free tier for Python services and supports Docker-style deploys without writing a Dockerfile. Fly.io is a fine alternative to Railway if you prefer edge-distributed compute.

## Local development setup

Before deploying, confirm everything works locally.

### Prerequisites

- **Python 3.11+** (3.14 also works)
- **Node 20+**
- **pnpm 10+** (`brew install pnpm` on macOS, or `npm install -g pnpm`)

### First-time setup

```bash
# Clone or cd into the repo
cd ~/Desktop/Claude\ Playground/Asclepius

# API: venv + deps
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Web: deps
cd ../web
pnpm install
```

### Run both services

```bash
# Terminal 1 — API
cd api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Web
cd web
pnpm dev
```

Open <http://localhost:3000/diligence/adagrasib> in a browser. You should see the worked-example workbench with PoS waterfall, rNPV panel, scorecard, and comparables table all populated.

### Smoke tests

Before deploying, run the full test suite:

```bash
cd api && source .venv/bin/activate && python -m ruff check app tests && python -m pytest -q
cd ../web && pnpm typecheck && pnpm build
```

All four commands should exit zero. The adagrasib snapshot test (`tests/test_adagrasib_backtest.py`) is the load-bearing assertion that the framework reproduces the BMS deal calibration.

## Deploying the API (Railway)

Railway auto-detects Python projects with a `pyproject.toml`. No Dockerfile required.

### Steps

1. **Sign up at [railway.app](https://railway.app)** and connect your GitHub account.
2. **Push the repo to GitHub** (see [Pushing to GitHub](#pushing-to-github) below).
3. **Create a new Railway project**:
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your Asclepius repo
   - Railway will detect the Python project; specify the root directory as `api`.
4. **Configure the start command** in Railway's settings:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   Railway provides `$PORT` automatically.
5. **Set environment variables** (Railway dashboard → Variables):
   ```
   ASCLEPIUS_CORS_ORIGINS=https://your-web-domain.vercel.app,https://*.vercel.app
   ```
   The wildcard handles Vercel preview deploys. Update once you have a custom domain.
6. **Deploy.** Railway gives you a public URL like `https://asclepius-api-production.up.railway.app`.
7. **Verify**:
   ```bash
   curl https://asclepius-api-production.up.railway.app/health
   # {"status":"ok","version":"0.1.0"}
   curl https://asclepius-api-production.up.railway.app/api/modules
   # {"modules":[...four entries...]}
   ```

### Optional: Fly.io instead of Railway

Fly is a reasonable alternative if you prefer edge-distributed compute.

```bash
cd api
fly launch --no-deploy
# Edit fly.toml: app name, primary region
fly deploy
```

You'll need a minimal `Dockerfile` in `api/`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[dev]"
COPY app ./app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Deploying the Web (Vercel)

Vercel auto-detects Next.js. The only configuration needed is the API base URL.

### Steps

1. **Sign up at [vercel.com](https://vercel.com)** and connect your GitHub account.
2. **Push the repo to GitHub** (next section).
3. **Import the project**:
   - Click "Add New Project"
   - Select your Asclepius repo
   - **Root directory: `web`** (important — Vercel needs to point at the Next.js project, not the repo root).
   - Framework preset: Next.js (auto-detected).
4. **Set environment variables** (Vercel dashboard → Settings → Environment Variables):
   ```
   ASCLEPIUS_API_BASE=https://asclepius-api-production.up.railway.app
   ```
   Use the Railway URL from the API deploy step.
5. **Deploy.** Vercel gives you a public URL like `https://asclepius.vercel.app`.
6. **Update Railway's CORS** to allow the Vercel URL (Railway dashboard → Variables):
   ```
   ASCLEPIUS_CORS_ORIGINS=https://asclepius.vercel.app
   ```

### Custom domains

Both Vercel and Railway support custom domains. For Asclepius, the recommended setup is:

- `asclepius.example.com` → Vercel (web)
- `api.asclepius.example.com` → Railway (api)

Update the `ASCLEPIUS_API_BASE` env var on Vercel and the `ASCLEPIUS_CORS_ORIGINS` env var on Railway to match the new domains. DNS configuration is provider-standard: an A record (or CNAME) pointing to the platform's edge.

## Pushing to GitHub

Asclepius is a new project. If you haven't pushed it to GitHub yet:

```bash
cd ~/Desktop/Claude\ Playground/Asclepius
git init
git add .
git commit -m "Initial commit"
gh repo create asclepius --public --source=. --remote=origin
git push -u origin main
```

The [CI workflow](../.github/workflows/ci.yml) will start running on the first push:

- **API job**: `ruff check` + `pytest -q` on the `api/` directory
- **Web job**: `pnpm typecheck` + `pnpm build` on the `web/` directory

Both should pass green if local checks passed.

## Environment variables — full reference

### API (`api/.env` for local; Railway dashboard for prod)

| Variable | Purpose | Local default | Prod value |
|---|---|---|---|
| `ASCLEPIUS_CORS_ORIGINS` | Comma-separated list of allowed origins | `http://localhost:3000` | The Vercel URL(s) |
| `ASCLEPIUS_API_HOST` | Bind address | `127.0.0.1` | `0.0.0.0` (Railway sets this) |
| `ASCLEPIUS_API_PORT` | Bind port | `8000` | `$PORT` (Railway sets this) |

v1.1 additions (for the runtime agents):
| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API access for the agents |
| `ASCLEPIUS_SKILLS_DIR` | Filesystem path to the Claude skill library |

### Web (`web/.env.local` for local; Vercel dashboard for prod)

| Variable | Purpose | Local default | Prod value |
|---|---|---|---|
| `ASCLEPIUS_API_BASE` | URL the `/api/*` rewrite proxies to | `http://127.0.0.1:8000` | The Railway URL |

No client-side env vars currently. If you add any, prefix them with `NEXT_PUBLIC_` per Next.js convention.

## Verifying the production deploy

After both services are live:

```bash
# 1. API health
curl https://api.asclepius.example.com/health
# Expected: {"status":"ok","version":"0.1.0"}

# 2. Module manifest
curl https://api.asclepius.example.com/api/modules | python -m json.tool
# Expected: four modules (comparables, pos, rnpv, scorecard) with manifests

# 3. End-to-end PoS calculation
curl -X POST https://api.asclepius.example.com/api/modules/pos \
  -H "Content-Type: application/json" \
  -d '{"asset":{"asset_name":"test","phase":"phase_2","therapeutic_area":"oncology","modality":"small_molecule","capital_position":"adequate"}}'
# Expected: PoS result with audit trail

# 4. Web → API proxy
curl https://asclepius.example.com/api/modules
# Should return the same response as step 2 (proxied through Next.js rewrites)

# 5. Browser test
# Open https://asclepius.example.com/diligence/adagrasib
# Verify: page loads, all four panels render, reflexivity slider responds, no console errors
```

## Monitoring (minimal for v1)

The v1 deploy uses platform-default monitoring. No additional setup required.

- **Vercel** provides per-deployment analytics (page views, route latency, build status) and runtime logs.
- **Railway** provides container logs, CPU/memory metrics, and uptime alerts.

For v1.1+, consider adding:

- **Sentry** (or similar) for error tracking on both services
- **Plausible** (or similar) for privacy-respecting analytics on the web app
- **Honeycomb** (or similar) for structured logging on the API once agent traces become valuable

None of these are required for v1.

## Cost expectations

For a personal portfolio project at typical scale (a few hundred recruiter visits per month):

- **Vercel** — free tier covers this comfortably
- **Railway** — free tier provides $5/month of credits, which covers the API at idle plus light traffic. Custom domains require the Hobby plan ($5/month).
- **Domain** — $10-15/year if you bring a custom domain

Total: **~$5-10/month** if you want a custom domain, **free** otherwise.

The v1.1 runtime agents will add Anthropic API costs (~$0.05-0.30 per agent invocation). At typical recruiter-traffic scale, this remains under $10/month.

## Troubleshooting

### "CORS error" in browser console

Check `ASCLEPIUS_CORS_ORIGINS` on Railway. The value must include the exact origin (including https://) that the web app is served from. Multiple origins are comma-separated. Wildcards work for `*.vercel.app` preview deploys but should be replaced with the production domain once you have one.

### "Failed to fetch /api/modules" on the web app

Check `ASCLEPIUS_API_BASE` on Vercel. The value should be the API's full HTTPS URL with no trailing slash. After changing the env var, redeploy the web service (Vercel doesn't pick up env changes without a redeploy).

### Railway build fails on `pip install`

Confirm the root directory is set to `api`, not the repo root. Railway expects a `pyproject.toml` at the configured root.

### Vercel build fails on `pnpm install`

Confirm the root directory is set to `web`, not the repo root. Vercel expects a `package.json` and `pnpm-lock.yaml` at the configured root. The lockfile must be committed.

### The adagrasib backtest test fails in CI

This is the load-bearing test. If it fails after a code change, the framework's calibration has shifted. Either revert the change or update the expected ranges in `adagrasib.json` and the test deliberately.

## See also

- [`docs/architecture.md`](architecture.md) — the design contract for adding extensions
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — the CI pipeline
- [`next.config.js`](../web/next.config.js) — the `/api/*` proxy configuration
- [`api/app/main.py`](../api/app/main.py) — the FastAPI entry point and CORS configuration
