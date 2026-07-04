"""
Turns a candidate post (content + scheduled time) into a numeric feature
vector used by BOTH the cold-start heuristic and the trained Random Forest.
Keeping one shared feature function means the model, once trained, is
learning corrections on top of the same signals the heuristic already uses.
"""
from datetime import datetime
from dataclasses import dataclass


@dataclass
class PostCandidate:
    content: str
    scheduled_time: datetime
    media_type: str = "none"      # none | image | video | carousel
    hashtags: list = None
    link_url: str | None = None

    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []


MEDIA_TYPE_ENCODING = {"none": 0, "image": 1, "carousel": 2, "video": 3}


def extract_features(post: PostCandidate) -> dict:
    dt = post.scheduled_time
    return {
        "hour_of_day": dt.hour,
        "day_of_week": dt.weekday(),        # 0=Monday
        "is_weekend": int(dt.weekday() >= 5),
        "content_length": len(post.content),
        "hashtag_count": len(post.hashtags),
        "has_link": int(bool(post.link_url)),
        "media_type_encoded": MEDIA_TYPE_ENCODING.get(post.media_type, 0),
        "has_question_mark": int("?" in post.content),
        "has_emoji_heuristic": int(any(ord(c) > 0x2600 for c in post.content)),
    }


FEATURE_ORDER = [
    "hour_of_day", "day_of_week", "is_weekend", "content_length",
    "hashtag_count", "has_link", "media_type_encoded",
    "has_question_mark", "has_emoji_heuristic",
]


def features_to_vector(features: dict) -> list:
    """Deterministic ordering for feeding sklearn."""
    return [features[k] for k in FEATURE_ORDER]
