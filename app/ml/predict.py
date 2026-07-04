"""
Single entry point the rest of the app calls for a prediction. Internally
decides model-vs-heuristic per account and caches loaded models in memory.
"""
import joblib
from functools import lru_cache
from sqlalchemy.orm import Session

from ..models import ModelVersion
from .feature_engineering import PostCandidate, extract_features, features_to_vector
from .cold_start import score_candidate


@lru_cache(maxsize=32)
def _load_model(artifact_path: str):
    return joblib.load(artifact_path)


def get_active_model_version(db: Session, social_account_id: int) -> ModelVersion | None:
    return (
        db.query(ModelVersion)
        .filter(
            ModelVersion.social_account_id == social_account_id,
            ModelVersion.promoted == True,  # noqa: E712
        )
        .order_by(ModelVersion.trained_at.desc())
        .first()
    )


def predict_engagement(db: Session, social_account_id: int, post: PostCandidate) -> dict:
    """
    Returns {"score": float, "source": "model"|"heuristic", "model_version_id": int|None}
    Score is on the same 0-100 relative scale in both modes so callers don't
    need to care which one answered.
    """
    version = get_active_model_version(db, social_account_id)

    if version is None:
        return {
            "score": score_candidate(post),
            "source": "heuristic",
            "model_version_id": None,
        }

    model = _load_model(version.artifact_path)
    features = extract_features(post)
    vector = [features_to_vector(features)]
    raw_pred = float(model.predict(vector)[0])

    return {
        "score": round(raw_pred, 2),
        "source": "model",
        "model_version_id": version.id,
    }


def rank_candidate_times(db: Session, social_account_id: int, post: PostCandidate,
                          candidate_times: list) -> list:
    """Given several candidate scheduled_time options for the same content,
    returns them sorted best-to-worst by predicted engagement."""
    results = []
    for t in candidate_times:
        candidate = PostCandidate(
            content=post.content,
            scheduled_time=t,
            media_type=post.media_type,
            hashtags=post.hashtags,
            link_url=post.link_url,
        )
        pred = predict_engagement(db, social_account_id, candidate)
        results.append({"scheduled_time": t, **pred})
    return sorted(results, key=lambda r: r["score"], reverse=True)
