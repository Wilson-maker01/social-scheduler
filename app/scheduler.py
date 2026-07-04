"""
Polls for due posts and publishes them. In production, prefer scheduling one
APScheduler job per post at creation time (add_job with a `run_date`) rather
than polling — polling is simpler to reason about for a starter system but
adds up to a minute of latency and doesn't scale past a few workers cleanly.
Swap for Celery + Redis if you need multiple worker processes.
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .models import Post, PostMetric
from .security import decrypt_token
from .platforms.registry import get_connector

logger = logging.getLogger("scheduler")

# How long after publish to check metrics — engagement compounds, so measure
# at multiple offsets rather than once.
METRIC_CHECK_OFFSETS_HOURS = [1, 24, 168]


def publish_due_posts():
    db = SessionLocal()
    try:
        due_posts = (
            db.query(Post)
            .filter(Post.status == "scheduled", Post.scheduled_time <= datetime.utcnow())
            .all()
        )
        for post in due_posts:
            _publish_one(db, post)
    finally:
        db.close()


def _publish_one(db, post: Post):
    post.status = "publishing"
    db.commit()

    account = post.account
    connector = get_connector(account.platform)
    access_token = decrypt_token(account.access_token_encrypted)

    result = connector.publish(
        content=post.content,
        media_urls=post.media_urls or [],
        access_token=access_token,
        account_id=account.platform_account_id,
    )

    if result.success:
        post.status = "published"
        post.platform_post_id = result.platform_post_id
        post.published_at = datetime.utcnow()
        logger.info(f"Published post {post.id} -> {result.platform_post_id}")
    else:
        post.status = "failed"
        post.error_message = result.error_message
        logger.error(f"Failed to publish post {post.id}: {result.error_message}")

    db.commit()


def collect_due_metrics():
    """Checks published posts for metric collection windows that have arrived,
    fetches from the platform, and stores them (this data feeds retraining)."""
    db = SessionLocal()
    try:
        published_posts = db.query(Post).filter(Post.status == "published").all()
        for post in published_posts:
            for offset in METRIC_CHECK_OFFSETS_HOURS:
                already_measured = (
                    db.query(PostMetric)
                    .filter(PostMetric.post_id == post.id,
                            PostMetric.measured_offset_hours == offset)
                    .first()
                )
                due_time = post.published_at + timedelta(hours=offset)
                if not already_measured and datetime.utcnow() >= due_time:
                    _collect_one_metric(db, post, offset)
    finally:
        db.close()


def _collect_one_metric(db, post: Post, offset_hours: int):
    account = post.account
    connector = get_connector(account.platform)
    access_token = decrypt_token(account.access_token_encrypted)

    metrics = connector.fetch_metrics(post.platform_post_id, access_token)

    db.add(PostMetric(
        post_id=post.id,
        measured_offset_hours=offset_hours,
        likes=metrics.likes,
        comments=metrics.comments,
        shares=metrics.shares,
        impressions=metrics.impressions,
        engagement_score=metrics.engagement_score(),
    ))
    db.commit()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(publish_due_posts, "interval", seconds=60, id="publish_due_posts")
    scheduler.add_job(collect_due_metrics, "interval", minutes=15, id="collect_due_metrics")
    scheduler.start()
    return scheduler
