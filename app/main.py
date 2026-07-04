from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import Post, SocialAccount
from .ml.feature_engineering import PostCandidate
from .ml.predict import predict_engagement, rank_candidate_times
from .ml.train import train_for_account
from .scheduler import start_scheduler

app = FastAPI(title="Social Scheduler API")


@app.on_event("startup")
def on_startup():
    app.state.scheduler = start_scheduler()


class PostCreateRequest(BaseModel):
    social_account_id: int
    content: str
    media_type: str = "none"
    media_urls: list[str] = []
    hashtags: list[str] = []
    link_url: str | None = None
    scheduled_time: datetime


class PredictRequest(BaseModel):
    social_account_id: int
    content: str
    media_type: str = "none"
    hashtags: list[str] = []
    link_url: str | None = None
    candidate_times: list[datetime]  # e.g. next 7 days x 4 times/day, generated client-side


@app.post("/predict")
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    """Ranks candidate posting times for a piece of content before scheduling."""
    base_candidate = PostCandidate(
        content=req.content,
        scheduled_time=req.candidate_times[0],
        media_type=req.media_type,
        hashtags=req.hashtags,
        link_url=req.link_url,
    )
    ranked = rank_candidate_times(
        db, req.social_account_id, base_candidate, req.candidate_times
    )
    return {"ranked_times": ranked}


@app.post("/posts")
def create_post(req: PostCreateRequest, db: Session = Depends(get_db)):
    account = db.query(SocialAccount).get(req.social_account_id)
    if not account:
        raise HTTPException(404, "Social account not found")

    candidate = PostCandidate(
        content=req.content,
        scheduled_time=req.scheduled_time,
        media_type=req.media_type,
        hashtags=req.hashtags,
        link_url=req.link_url,
    )
    prediction = predict_engagement(db, req.social_account_id, candidate)

    post = Post(
        social_account_id=req.social_account_id,
        content=req.content,
        media_type=req.media_type,
        media_urls=req.media_urls,
        hashtags=req.hashtags,
        link_url=req.link_url,
        scheduled_time=req.scheduled_time,
        predicted_engagement=prediction["score"],
        prediction_source=prediction["source"],
        model_version_id=prediction["model_version_id"],
        status="scheduled",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "prediction": prediction}


@app.get("/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    return post


@app.post("/accounts/{social_account_id}/retrain")
def retrain(social_account_id: int, db: Session = Depends(get_db)):
    """Manually trigger a retrain; also wire this to a weekly scheduled job."""
    version = train_for_account(db, social_account_id)
    if version is None:
        return {"status": "not enough data yet, still on heuristic"}
    return {
        "status": "trained",
        "promoted": version.promoted,
        "validation_mae": version.validation_mae,
        "heuristic_mae": version.heuristic_mae,
        "training_rows": version.training_rows,
    }
