# Deploying OpsPilot

OpsPilot is a single Docker container that listens on `$PORT` (default 8050), so
it deploys cleanly on any container host. It works **key-free** as a SQL console
+ profiler; set `OPSPILOT_LLM_API_KEY` (+ `OPSPILOT_LLM_PROVIDER`) to enable the
plain-English → SQL feature. Free LLM keys: NVIDIA (build.nvidia.com), Groq
(console.groq.com), Google AI Studio (aistudio.google.com).

> Note: free tiers use **ephemeral** storage — uploaded data resets on restart.
> That's fine for a demo; for persistence, attach a disk/volume and point
> `OPSPILOT_DB_PATH` at it.

---

## Option A — Render (recommended, free, one-click)

1. Go to **https://render.com** → sign up with GitHub.
2. **New → Blueprint** → pick the `opspilot` repo. Render reads `render.yaml`.
3. After it creates the service, open **Environment** and set
   `OPSPILOT_LLM_API_KEY` (and change `OPSPILOT_LLM_PROVIDER` if not NVIDIA).
4. Deploy. You get a public URL like `https://opspilot.onrender.com`.

Free web services sleep after ~15 min idle and wake on the next request.

---

## Option B — Hugging Face Spaces (free, always-on-ish, Docker)

1. **https://huggingface.co/new-space** → SDK: **Docker** → blank.
2. Push this repo to the Space, or set the Space to build from this Dockerfile.
3. In **Settings → Variables and secrets**, add `OPSPILOT_LLM_API_KEY` and
   `OPSPILOT_LLM_PROVIDER`. Spaces inject `PORT=7860`, which the container honors.

---

## Option C — Fly.io (free allowance, needs flyctl + card on file)

```bash
fly launch --no-deploy            # detects the Dockerfile, writes fly.toml
fly secrets set OPSPILOT_LLM_PROVIDER=nvidia OPSPILOT_LLM_API_KEY=nvapi-...
fly deploy
```

---

## Option D — Google Cloud Run (generous free tier, scales to zero)

```bash
gcloud run deploy opspilot --source . \
  --allow-unauthenticated --region us-central1 \
  --set-env-vars OPSPILOT_LLM_PROVIDER=nvidia,OPSPILOT_LLM_API_KEY=nvapi-...
```

Cloud Run sets `$PORT`; the container binds it automatically.

---

## Run the container locally

```bash
docker build -t opspilot .
docker run -p 8050:8050 \
  -e OPSPILOT_LLM_PROVIDER=nvidia \
  -e OPSPILOT_LLM_API_KEY=nvapi-... \
  opspilot
# → http://localhost:8050
```
