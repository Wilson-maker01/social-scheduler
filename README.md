# Social Media Content Scheduler with Engagement Prediction

A production-oriented starter system that schedules posts to real social platforms
and predicts engagement using a Random Forest, with a cold-start strategy since
you're starting with zero historical data.

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Frontend    │─────▶│  FastAPI Backend  │─────▶│  PostgreSQL      │
│ (React, not  │      │  (app/main.py)    │      │  (posts, metrics,│
│  scaffolded  │      │                   │      │   accounts)      │
│  here)       │      └────────┬──────────┘      └─────────────────┘
└─────────────┘               │
                               │ predict()
                       ┌───────▼────────┐
                       │  ML Engine      │
                       │ cold_start.py   │  (used until enough data)
                       │ train.py        │  (retrains RF periodically)
                       │ predict.py      │  (serves predictions)
                       └────────┬────────┘
                               │
                       ┌───────▼────────┐
                       │  Scheduler      │
                       │ (APScheduler)   │
                       └───────┬────────┘
                               │ at scheduled time
                  ┌────────────┼────────────┐
                  ▼            ▼             ▼
             Twitter/X       Meta          LinkedIn
             connector    (IG/FB) conn.    connector
                  │            │             │
                  └──── pulls metrics back into DB (feeds retraining) ──┘
```

## Why this shape

- **The API server never talks to social platforms directly on the request path.**
  Publishing is decoupled into scheduled jobs so a slow/rate-limited platform call
  can't hang a user-facing request.
- **Platform connectors share one interface** (`app/platforms/base.py`) so adding
  TikTok or Threads later means writing one new class, not touching the scheduler
  or the ML code.
- **The ML engine has two modes** behind a single `predict()` call, so the rest of
  the system never needs to know whether a heuristic or a trained model answered.

## Cold-start strategy (no historical data)

This is the core problem with "use ML from day one, with zero data." The fix is a
graduation path:

1. **Bootstrap (heuristic)** — `app/ml/cold_start.py` scores a candidate post using
   published best-practice signals: hour-of-day/day-of-week curves, caption length,
   hashtag count, media type, link presence. No training required, works immediately.
2. **Data collection** — every real post you publish gets its actual metrics
   (likes, comments, shares, impressions) pulled back from the platform API on a
   schedule (e.g. 1h, 24h, 7d after publish — engagement compounds over time) and
   stored in `post_metrics`. This is your training set, accumulating for free.
3. **Retraining** — `app/ml/train.py` runs periodically (e.g. weekly cron/job).
   Once you have enough labeled rows per account (a reasonable floor is ~50–100),
   it trains a `RandomForestRegressor`, validates against a heuldout split, and
   only promotes the new model if it beats both the heuristic baseline and the
   previous model version on held-out MAE.
4. **Serving** — `app/ml/predict.py` picks trained-model-if-available, heuristic
   otherwise, per account (a brand-new account added later starts back at step 1
   for itself, transfer learning optional — see below).

**Optional acceleration**: instead of starting every new account from scratch, you
can pre-train an initial "global" Random Forest on aggregate, anonymized patterns
across all your accounts once you have enough total data, then fine-tune per
account. This is a reasonable v2, not needed for launch.

## Data model

See `schema.sql`. Key tables:
- `social_accounts` — OAuth tokens per connected platform account (encrypt tokens at rest)
- `posts` — content, scheduled_time, status, platform, predicted_engagement
- `post_metrics` — actual engagement pulled back post-publish, at multiple time offsets
- `model_versions` — tracks trained model artifacts + validation scores, for safe rollback

## Setup

```bash
pip install -r requirements.txt
# create DB and run schema.sql
psql -U youruser -d social_scheduler -f schema.sql
uvicorn app.main:app --reload
```

You'll need developer app credentials from each platform:
- **Twitter/X**: developer.twitter.com — API v2, OAuth 2.0 with PKCE for user-context posting
- **Meta (Instagram/Facebook)**: developers.facebook.com — Graph API, requires a Business/Creator IG account linked to a FB Page
- **LinkedIn**: developer.linkedin.com — Marketing/Share API, org or member auth depending on use case

Store credentials in environment variables / a secrets manager — never in code or DB in plaintext.

## What's included vs. what you still need to build

**Included (working skeletons, real logic):**
- DB schema
- Feature engineering
- Cold-start heuristic scorer
- RF training + prediction pipeline
- APScheduler-based publish scheduler
- Twitter and Meta connector implementations (real API calls, need your credentials)
- FastAPI endpoints tying it together

**You still need to add:**
- OAuth flow endpoints for connecting user accounts (each platform's OAuth dance)
- Frontend UI
- Token refresh/expiry handling per platform
- Production hardening: retries with backoff, dead-letter queue for failed publishes,
  rate-limit-aware queuing, monitoring/alerting on the scheduler
