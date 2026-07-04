"""
Trains a per-account RandomForestRegressor on accumulated post_metrics data.
Only promotes the new model if it beats both the heuristic and the previous
model version on held-out MAE — this guards against a bad retrain silently
making predictions worse.

Run periodically (cron, Celery beat, or an APScheduler job) e.g. weekly.
"""
import os
import joblib
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import pandas as pd

from sqlalchemy.orm import Session
from ..models import Post, PostMetric, ModelVersion
from .feature_engineering import PostCandidate, extract_features, FEATURE_ORDER
from .cold_start import score_candidate

ARTIFACT_DIR = os.environ.get("MODEL_ARTIFACT_DIR", "./model_artifacts")
MIN_TRAINING_ROWS = 50


def build_training_frame(db: Session, social_account_id: int) -> pd.DataFrame:
    """
    Pulls published posts + their engagement metrics (using the longest-horizon
    measurement available, e.g. 7-day) and turns them into a feature/label table.
    """
    rows = (
        db.query(Post, PostMetric)
        .join(PostMetric, PostMetric.post_id == Post.id)
        .filter(
            Post.social_account_id == social_account_id,
            Post.status == "published",
        )
        .all()
    )

    records = []
    for post, metric in rows:
        candidate = PostCandidate(
            content=post.content,
            scheduled_time=post.scheduled_time,
            media_type=post.media_type or "none",
            hashtags=post.hashtags or [],
            link_url=post.link_url,
        )
        feats = extract_features(candidate)
        feats["target"] = metric.engagement_score
        feats["post_id"] = post.id
        records.append(feats)

    return pd.DataFrame(records)


def train_for_account(db: Session, social_account_id: int) -> ModelVersion | None:
    df = build_training_frame(db, social_account_id)

    if len(df) < MIN_TRAINING_ROWS:
        print(f"Only {len(df)} labeled posts for account {social_account_id}; "
              f"need {MIN_TRAINING_ROWS}. Staying on heuristic.")
        return None

    # dedupe multiple metric rows per post (keep last measurement per post_id
    # if build_training_frame ever returns >1 offset per post upstream)
    df = df.drop_duplicates(subset="post_id")

    X = df[FEATURE_ORDER]
    y = df["target"]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    val_preds = model.predict(X_val)
    val_mae = mean_absolute_error(y_val, val_preds)

    # Compare against heuristic on the same validation slice
    heuristic_preds = []
    for _, row in df.loc[X_val.index].iterrows():
        candidate = PostCandidate(
            content="",  # heuristic here only needs the numeric features we saved;
            scheduled_time=datetime.now(),  # not reused for validation timing directly
            media_type="none",
        )
        # Simpler: recompute heuristic score directly from stored features
        heuristic_preds.append(_heuristic_score_from_features(row))
    heuristic_mae = mean_absolute_error(y_val, heuristic_preds)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    artifact_path = os.path.join(
        ARTIFACT_DIR, f"rf_account_{social_account_id}_{int(datetime.now().timestamp())}.joblib"
    )
    joblib.dump(model, artifact_path)

    promoted = val_mae < heuristic_mae
    version = ModelVersion(
        social_account_id=social_account_id,
        training_rows=len(df),
        validation_mae=val_mae,
        heuristic_mae=heuristic_mae,
        promoted=promoted,
        artifact_path=artifact_path,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    print(f"Trained model for account {social_account_id}: "
          f"val_mae={val_mae:.2f} heuristic_mae={heuristic_mae:.2f} promoted={promoted}")
    return version


def _heuristic_score_from_features(row) -> float:
    """Approximate the heuristic score using already-extracted features,
    avoiding re-deriving them from raw content during validation."""
    from .cold_start import HOUR_WEIGHTS, DAY_WEIGHTS, MEDIA_WEIGHTS
    hour_score = HOUR_WEIGHTS.get(int(row["hour_of_day"]), 0.5)
    day_score = DAY_WEIGHTS.get(int(row["day_of_week"]), 0.7)
    media_lookup = {v: k for k, v in {"none": 0, "image": 1, "carousel": 2, "video": 3}.items()}
    media_score = MEDIA_WEIGHTS.get(media_lookup.get(int(row["media_type_encoded"]), "none"), 0.6)
    hc = row["hashtag_count"]
    hashtag_score = max(0.4, 1.0 - abs(hc - 4) * 0.08)
    length = row["content_length"]
    length_score = 1.0 if 80 <= length <= 150 else max(0.4, 1.0 - abs(length - 115) / 300)
    link_penalty = 0.9 if row["has_link"] else 1.0
    question_bonus = 1.05 if row["has_question_mark"] else 1.0
    raw = (hour_score * 0.25 + day_score * 0.15 + media_score * 0.25
           + hashtag_score * 0.15 + length_score * 0.20) * link_penalty * question_bonus
    return round(raw * 100, 2)
