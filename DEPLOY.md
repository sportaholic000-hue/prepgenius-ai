# PrepGenius AI -- Deployment Guide

> Deploy the PrepGenius AI FastAPI backend to Render (primary) or Railway (alternative).
> Estimated time: 10-15 minutes for first deploy.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deploy to Render (Primary)](#deploy-to-render)
3. [Set Environment Variables](#set-environment-variables)
4. [Verify Deployment](#verify-deployment)
5. [Custom Domain Setup](#custom-domain-setup)
6. [Deploy to Railway (Alternative)](#deploy-to-railway)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, make sure you have:

- [x] GitHub repo: `sportaholic000-hue/prepgenius-ai` with the latest code pushed
- [x] An OpenAI API key (from https://platform.openai.com/api-keys)
- [x] These files in the repo root:
  - `render.yaml` (Render Blueprint)
  - `Dockerfile.render` (production Dockerfile)
  - `app.py` (FastAPI application)
  - `requirements.txt` (Python dependencies)

### File Placement

Copy these deployment files to the root of your repo:

```bash
# From the repo root
cp code/prepgenius-deploy/render.yaml ./render.yaml
cp code/prepgenius-deploy/Dockerfile.render ./Dockerfile.render
git add render.yaml Dockerfile.render
git commit -m "Add Render deployment config"
git push origin main
```

---

## Deploy to Render

### Option A: Blueprint Auto-Deploy (Recommended)

1. Go to https://dashboard.render.com
2. Click **"New +"** in the top navigation
3. Select **"Blueprint"**
4. Connect your GitHub account if not already connected
5. Search for and select the repo: **sportaholic000-hue/prepgenius-ai**
6. Render auto-detects the `render.yaml` file
7. Review the service configuration:
   - Name: `prepgenius-api`
   - Region: Oregon
   - Plan: Free
   - Runtime: Docker
8. Click **"Apply"**
9. You will be prompted to set `OPENAI_API_KEY` -- enter your key
10. Click **"Create Resources"**

Render will now build and deploy the Docker image. First deploy takes 3-5 minutes.

### Option B: Manual Web Service Setup

If Blueprint does not work, create the service manually:

1. Go to https://dashboard.render.com
2. Click **"New +"** -> **"Web Service"**
3. Connect your GitHub repo: `sportaholic000-hue/prepgenius-ai`
4. Configure:
   - **Name:** `prepgenius-api`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Runtime:** Docker
   - **Dockerfile Path:** `./Dockerfile.render`
   - **Plan:** Free
5. Click **"Create Web Service"**
6. Add environment variables (see next section)

---

## Set Environment Variables

After deployment, configure these environment variables in the Render dashboard:

### Required

| Variable | Value | Notes |
|----------|-------|-------|
| `OPENAI_API_KEY` | `sk-...` | Your OpenAI API key. **Never commit this to git.** |

### Optional (defaults provided)

| Variable | Default | Notes |
|----------|---------|-------|
| `PORT` | `8000` | Render may override this; the Dockerfile handles it |
| `OPENAI_MODEL` | `gpt-4o-mini` | Change to `gpt-4o` for higher quality (costs more) |

### How to Set Env Vars

1. Go to your service in Render dashboard
2. Click **"Environment"** in the left sidebar
3. Click **"Add Environment Variable"**
4. Enter key: `OPENAI_API_KEY`, value: your OpenAI key
5. Click **"Save Changes"**
6. The service will auto-redeploy with the new variable

---

## Verify Deployment

Once the deploy is complete (green status), verify everything works:

### 1. Health Check

```bash
curl https://prepgenius-api.onrender.com/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "PrepGenius AI",
  "version": "1.0.0"
}
```

### 2. API Docs

Open in your browser:
```
https://prepgenius-api.onrender.com/docs
```

This loads the FastAPI auto-generated Swagger UI where you can test all endpoints.

### 3. Test Meal Plan Generation

```bash
curl -X POST https://prepgenius-api.onrender.com/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "muscle_gain",
    "calories": 2500,
    "diet": "none",
    "allergies": [],
    "budget": "medium",
    "cooking_skill": "intermediate",
    "servings": 2
  }'
```

### Important: Free Tier Cold Starts

Render free tier spins down after 15 minutes of inactivity. The first request after
idle will take 30-60 seconds (cold start). This is normal -- subsequent requests
are fast. Upgrade to the $7/month Starter plan to eliminate cold starts.

---

## Custom Domain Setup

### On Render

1. Go to your service -> **"Settings"** -> scroll to **"Custom Domains"**
2. Click **"Add Custom Domain"**
3. Enter your domain: e.g., `api.prepgenius.ai`
4. Render provides a CNAME record value (e.g., `prepgenius-api.onrender.com`)
5. Go to your DNS provider and add:
   - **Type:** CNAME
   - **Name:** `api` (or your subdomain)
   - **Value:** the CNAME Render gave you
6. Wait for DNS propagation (5 min to 48 hours)
7. Render auto-provisions an SSL certificate via Let's Encrypt

### Recommended Domain Structure

| Domain | Points To | Purpose |
|--------|-----------|---------|
| `prepgenius.ai` | Landing page (Vercel/Netlify) | Marketing site |
| `api.prepgenius.ai` | Render web service | API backend |
| `app.prepgenius.ai` | Frontend app (if separate) | Web app |

---

## Deploy to Railway (Alternative)

Railway is a great alternative with better free-tier performance (no cold starts
on the Hobby plan at $5/month).

### Step 1: Create railway.json

Create this file in your repo root:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "dockerfilePath": "Dockerfile.render"
  },
  "deploy": {
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

### Step 2: Deploy on Railway

1. Go to https://railway.com
2. Click **"New Project"**
3. Select **"Deploy from GitHub Repo"**
4. Connect your GitHub and select: **sportaholic000-hue/prepgenius-ai**
5. Railway auto-detects the Dockerfile
6. Add environment variable:
   - `OPENAI_API_KEY` = your key
   - `PORT` = `8000`
7. Click **"Deploy"**

### Step 3: Get Your URL

1. Go to **Settings** -> **Networking** -> **Generate Domain**
2. Railway gives you a URL like: `prepgenius-ai-production.up.railway.app`
3. Test with: `curl https://your-url.up.railway.app/api/health`

### Step 4: Custom Domain on Railway

1. Go to **Settings** -> **Networking** -> **Custom Domain**
2. Enter `api.prepgenius.ai`
3. Add the CNAME record Railway provides to your DNS
4. SSL is auto-provisioned

### Railway vs Render Comparison

| Feature | Render Free | Railway Hobby ($5/mo) |
|---------|-------------|----------------------|
| Cold starts | Yes (30-60s) | No |
| Build time | ~3-5 min | ~2-3 min |
| Auto-deploy | Yes | Yes |
| Custom domains | Yes (free) | Yes (free) |
| SSL | Auto (Let's Encrypt) | Auto |
| Logs | 7 days | 7 days |
| RAM | 512 MB | 512 MB |
| Bandwidth | 100 GB/mo | Unlimited |

---

## Troubleshooting

### Build Fails

**"ModuleNotFoundError: No module named 'xxx'"**
- Make sure `requirements.txt` is in the repo root and has all dependencies
- Verify the Dockerfile copies requirements.txt correctly

**"docker build failed"**
- Check Render build logs for the exact error
- Test locally first: `docker build -f Dockerfile.render -t prepgenius .`

### Runtime Errors

**"Application failed to respond" / Health check fails**
- Verify the health endpoint exists at `/api/health` in your app
- Check that the app binds to `0.0.0.0` (not `127.0.0.1`)
- Ensure `PORT` env var is set to `8000`
- Check Render logs: Dashboard -> your service -> "Logs" tab

**"OPENAI_API_KEY not set"**
- Go to Environment tab in Render dashboard
- Add `OPENAI_API_KEY` with your `sk-...` key
- Service will auto-redeploy

**502 Bad Gateway**
- App is still starting (cold start on free tier) -- wait 30-60 seconds
- Check logs for Python errors or crash loops

### Local Testing Before Deploy

```bash
# Build the Docker image locally
docker build -f Dockerfile.render -t prepgenius-api .

# Run with your API key
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -e OPENAI_MODEL=gpt-4o-mini \
  prepgenius-api

# Test health endpoint
curl http://localhost:8000/api/health

# Open Swagger docs
open http://localhost:8000/docs
```

### Upgrading from Free Tier

When traffic grows, upgrade to eliminate cold starts and get better performance:

1. **Render Starter ($7/mo):** No cold starts, 0.5 CPU, 512MB RAM
2. **Render Standard ($25/mo):** 1 CPU, 2GB RAM, auto-scaling
3. **Railway Hobby ($5/mo):** No cold starts, usage-based pricing

To upgrade on Render:
1. Go to Dashboard -> your service -> **Settings**
2. Scroll to **"Instance Type"**
3. Select **Starter** or **Standard**
4. Click **Save** -- takes effect immediately, no downtime

---

## Quick Reference

| Item | Value |
|------|-------|
| Repo | `sportaholic000-hue/prepgenius-ai` |
| Runtime | Docker (Python 3.11-slim) |
| Port | 8000 |
| Health check | `/api/health` |
| API docs | `/docs` |
| Render URL | `https://prepgenius-api.onrender.com` |
| Required env | `OPENAI_API_KEY` |
| Optional env | `OPENAI_MODEL` (default: gpt-4o-mini) |
