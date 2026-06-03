# Deployment

How to take Asclepius from local dev to live URL. Two services, two platforms, one DNS hand-off.

## Architecture overview

Asclepius is deployed as two independent services:

| Service | Platform | What runs there |
|---|---|---|
| **Web** (Next.js 14) | Vercel — live at `asclepius-bio.vercel.app` | The `/diligence/[asset]` workbench, the methodology page, the landing page. Static + Edge. |
| **API** (FastAPI) | Fly.io — live at `asclepius-api.fly.dev` | The four module routes (`/api/modules/pos`, `/rnpv`, `/scorecard`, `/comparables`), the manifest endpoint, the data-source registry. Containerized Python service. |

The frontend talks to the API via Next.js [rewrites](../web/next.config.js) configured by the `ASCLEPIUS_API_BASE` env var. **No CORS headers required** — the rewrite rule makes the API appear to be on the same origin as the web app.

Production pairing: **Vercel for web, Fly.io for api.** Vercel is free for personal projects and ships Next.js with zero config; Fly.io runs the containerized Python service with edge-distributed compute and a generous free tier. Railway is documented below as an alternative — it was the original choice but new accounts now require commercial verification before deploys run, which is why the live API is on Fly.

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

## Deploying the API (Fly.io)

Fly runs the API as a containerized service from the [`Dockerfile`](../api/Dockerfile) and [`fly.toml`](../api/fly.toml) at the repo root and `api/` respectively.

### Steps

1. **Install the flyctl CLI** and sign in:
   ```bash
   brew install flyctl   # macOS; see fly.io/docs/hands-on/install-flyctl for other platforms
   fly auth signup       # or: fly auth login if you already have an account
   ```
2. **Push the repo to GitHub** (see [Pushing to GitHub](#pushing-to-github) below).
3. **Launch the app** from the repo root:
   ```bash
   cd ~/Desktop/Claude\ Playground/Asclepius
   fly launch --no-deploy --copy-config --name asclepius-api
   ```
   This reads the existing `api/fly.toml`. Pick a region close to your Vercel edge — `iad` (Ashburn) pairs well with most US deploys.
4. **Set environment variables**:
   ```bash
   fly secrets set ASCLEPIUS_CORS_ORIGINS="https://asclepius-bio.vercel.app,https://*.vercel.app"
   ```
   The wildcard handles Vercel preview deploys.
5. **Deploy**:
   ```bash
   fly deploy
   ```
   Fly gives you a public URL like `https://asclepius-api.fly.dev`.
6. **Verify**:
   ```bash
   curl https://asclepius-api.fly.dev/health
   # {"status":"ok","version":"0.1.0"}
   curl https://asclepius-api.fly.dev/api/modules
   # {"modules":[...four entries...]}
   ```

The Dockerfile is minimal — Python 3.11 slim, `pip install -e ".[dev]"`, expose 8080, run uvicorn. `fly.toml` declares the HTTPS service, autoscale settings, and a `/health` healthcheck under `[[http_service.checks]]`.

### Alternative: Railway

Railway auto-detects Python projects with a `pyproject.toml`. No Dockerfile required. New Railway accounts require commercial verification before deploys run as of 2026, which is why the live deploy is on Fly — but if your account is in good standing, the path is:

1. Sign up at [railway.app](https://railway.app) and connect your GitHub account.
2. **New Project** → **Deploy from GitHub repo** → select Asclepius → set root directory to `api`.
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (Railway provides `$PORT`).
4. Variables: `ASCLEPIUS_CORS_ORIGINS=https://your-web-domain.vercel.app,https://*.vercel.app`.
5. Deploy; Railway gives you a URL like `https://asclepius-api-production.up.railway.app`.
6. Verify with the same `curl /health` and `curl /api/modules` calls as the Fly path.

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
   ASCLEPIUS_API_BASE=https://asclepius-api.fly.dev
   ```
   Use the Fly URL from the API deploy step.
5. **Deploy.** Vercel gives you a public URL like `https://asclepius-bio.vercel.app`.
6. **Update Fly's CORS** to allow the Vercel URL:
   ```bash
   fly secrets set ASCLEPIUS_CORS_ORIGINS="https://asclepius-bio.vercel.app"
   ```

### Custom domains

Both Vercel and Fly support custom domains. For Asclepius, the recommended setup is:

- `asclepius.example.com` → Vercel (web)
- `api.asclepius.example.com` → Fly (api) via `fly certs add api.asclepius.example.com`

Update the `ASCLEPIUS_API_BASE` env var on Vercel and the `ASCLEPIUS_CORS_ORIGINS` Fly secret to match the new domains. DNS configuration is provider-standard: an A record (or CNAME) pointing to the platform's edge.

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

### API (`api/.env` for local; `fly secrets` for prod)

| Variable | Purpose | Local default | Prod value |
|---|---|---|---|
| `ASCLEPIUS_CORS_ORIGINS` | Comma-separated list of allowed origins | `http://localhost:3000` | The Vercel URL(s) |
| `ASCLEPIUS_API_HOST` | Bind address | `127.0.0.1` | `0.0.0.0` (Dockerfile sets this) |
| `ASCLEPIUS_API_PORT` | Bind port | `8000` | `8080` on Fly (set in `fly.toml`) |

v1.1 additions (for the runtime agents):
| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API access for the agents |
| `ASCLEPIUS_SKILLS_DIR` | Filesystem path to the Claude skill library |

### Web (`web/.env.local` for local; Vercel dashboard for prod)

| Variable | Purpose | Local default | Prod value |
|---|---|---|---|
| `ASCLEPIUS_API_BASE` | URL the `/api/*` rewrite proxies to | `http://127.0.0.1:8000` | The Fly URL (`https://asclepius-api.fly.dev`) |

No client-side env vars currently. If you add any, prefix them with `NEXT_PUBLIC_` per Next.js convention.

## Verifying the production deploy

After both services are live:

```bash
# 1. API health
curl https://asclepius-api.fly.dev/health
# Expected: {"status":"ok","version":"0.1.0"}

# 2. Module manifest
curl https://asclepius-api.fly.dev/api/modules | python -m json.tool
# Expected: four modules (comparables, pos, rnpv, scorecard) with manifests

# 3. End-to-end PoS calculation
curl -X POST https://asclepius-api.fly.dev/api/modules/pos \
  -H "Content-Type: application/json" \
  -d '{"asset":{"asset_name":"test","phase":"phase_2","therapeutic_area":"oncology","modality":"small_molecule","capital_position":"adequate"}}'
# Expected: PoS result with audit trail

# 4. Web → API proxy
curl https://asclepius-bio.vercel.app/api/modules
# Should return the same response as step 2 (proxied through Next.js rewrites)

# 5. Browser test
# Open https://asclepius-bio.vercel.app/diligence/adagrasib
# Verify: page loads, all four panels render, reflexivity slider responds, no console errors
```

## Monitoring (minimal for v1)

The v1 deploy uses platform-default monitoring. No additional setup required.

- **Vercel** provides per-deployment analytics (page views, route latency, build status) and runtime logs.
- **Fly** provides container logs via `fly logs`, CPU/memory metrics in the dashboard, and uptime tracking via the `[[http_service.checks]]` block in `fly.toml`.

For v1.1+, consider adding:

- **Sentry** (or similar) for error tracking on both services
- **Plausible** (or similar) for privacy-respecting analytics on the web app
- **Honeycomb** (or similar) for structured logging on the API once agent traces become valuable

None of these are required for v1.

## Cost expectations

For a personal portfolio project at typical scale (a few hundred recruiter visits per month):

- **Vercel** — free tier covers this comfortably
- **Fly.io** — free allowances cover a single small shared-CPU instance and outbound traffic at this scale; expect $0–$5/month at portfolio-traffic levels
- **Domain** — $10-15/year if you bring a custom domain

Total: **~$5-15/month** if you want a custom domain, **near-free** otherwise.

The v1.1 runtime agents will add Anthropic API costs (~$0.05-0.30 per agent invocation). At typical recruiter-traffic scale, this remains under $10/month.

## Troubleshooting

### "CORS error" in browser console

Check `ASCLEPIUS_CORS_ORIGINS` on Fly (`fly secrets list`). The value must include the exact origin (including https://) that the web app is served from. Multiple origins are comma-separated. Wildcards work for `*.vercel.app` preview deploys but should be replaced with the production domain once you have one.

### "Failed to fetch /api/modules" on the web app

Check `ASCLEPIUS_API_BASE` on Vercel. The value should be the API's full HTTPS URL with no trailing slash. After changing the env var, redeploy the web service (Vercel doesn't pick up env changes without a redeploy).

### Fly build fails on `pip install`

Check that the Dockerfile copies `pyproject.toml` before running `pip install -e ".[dev]"`. The build context is the `api/` directory; relative paths are resolved from there. Run `fly logs` after a failed deploy to see the build output.

### Vercel build fails on `pnpm install`

Confirm the root directory is set to `web`, not the repo root. Vercel expects a `package.json` and `pnpm-lock.yaml` at the configured root. The lockfile must be committed.

### The adagrasib backtest test fails in CI

This is the load-bearing test. If it fails after a code change, the framework's calibration has shifted. Either revert the change or update the expected ranges in `adagrasib.json` and the test deliberately.

## See also

- [`docs/architecture.md`](architecture.md) — the design contract for adding extensions
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — the CI pipeline
- [`next.config.js`](../web/next.config.js) — the `/api/*` proxy configuration
- [`api/app/main.py`](../api/app/main.py) — the FastAPI entry point and CORS configuration
