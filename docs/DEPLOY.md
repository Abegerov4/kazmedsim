# Deploy: Vercel (frontend) + Railway (backend)

Costs at hobby scale: **Vercel free**, **Railway ~$3–4/month** for one
always-on backend service. The $5 Railway trial covers the first ~30
days. The Anthropic + OpenAI API spend depends on usage (a single
text session runs ≈ $0.02; a full eval run ≈ $0.10).

The seed database (`db/kazmedsim.db`, 21 MB) is committed to git, so
Railway has 49 scenarios + 2 586 RAG chunks the moment the service
boots — no migrations, no ingest step, no Postgres.

## 1) Railway — backend

1. Sign in at [railway.com](https://railway.com), click **New Project →
   Deploy from GitHub repo**, select this repository.
2. Railway auto-detects the Python service from `runtime.txt`,
   `railway.json`, and `Procfile`. Build command runs
   `pip install -r backend/requirements.txt`.
3. Open the service → **Variables** → add:
   - `ANTHROPIC_API_KEY` — required
   - `OPENAI_API_KEY` — required
   - `ALLOWED_ORIGINS` — comma-separated Vercel URL(s), e.g.
     `https://kazmedsim.vercel.app,https://*.vercel.app`
4. Service → **Settings → Networking → Generate Domain**. Note the URL
   (e.g. `kazmedsim-backend.up.railway.app`). Health check hits
   `/api/scenarios?lang=ru`.

## 2) Vercel — frontend

1. Sign in at [vercel.com](https://vercel.com), **Add New → Project**,
   import the same GitHub repo. Vercel auto-detects Next.js.
2. **Environment Variables** → add:
   - `NEXT_PUBLIC_API_URL` = `https://<your-railway-domain>` (no trailing slash)
3. Deploy. The first build is ~2 min.
4. Open the production URL, switch language, start an appointment.

## 3) Wire CORS

Once Vercel gives the final URL, set Railway's `ALLOWED_ORIGINS` to
include it and redeploy the backend service (Vercel preview URLs also
need to be there if you want to test PRs against prod backend).

## What stays local / not deployed

- `docs/protocols/*.pdf` — gitignored, used only by the local ingest
  pipeline. The seed DB already contains the embeddings.
- `db/events.jsonl` — local telemetry log; Railway's ephemeral disk
  will lose writes on every redeploy, which is fine for telemetry that
  is meant to be inspected locally during dev.
- `.env.local` — never commit; only goes into Railway / Vercel UI.

## Troubleshooting

- **CORS error in browser** — the Vercel origin isn't in
  `ALLOWED_ORIGINS` on Railway. Add it and redeploy.
- **`PORT` not bound** — Railway injects `$PORT`; the Procfile and
  `railway.json` both reference it. Don't override with a literal `8000`.
- **`db/kazmedsim.db: no such file`** — confirm the file is tracked in
  git (`git ls-files db/`). The `.gitignore` exception keeps this one
  file committed.
- **Eviction / OOM** — Railway hobby tier has 8 GB RAM, well above what
  this app uses (~150 MB with the RAG index loaded).
