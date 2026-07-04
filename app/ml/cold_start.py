"""
Rule-based engagement scorer used before enough real data exists to train
a Random Forest. Produces a 0-100 relative score, not an absolute engagement
count — it's meant to RANK candidate times/content, not predict exact numbers.

The specific weights below are reasonable industry-commonplace defaults
(e.g. weekday lunch/evening peaks, diminishing returns on hashtag count).
Treat them as a starting point to tune per your audience, not gospel.
"""
from .feature_engineering import PostCandidate, extract_features

# Relative multiplier by hour of day (24-hour), generic "office hours + evening" curve
HOUR_WEIGHTS = {
    0: 0.3, 1: 0.2, 2: 0.15, 3: 0.15, 4: 0.15, 5: 0.2,
    6: 0.4, 7: 0.6, 8: 0.75, 9: 0.85, 10: 0.8, 11: 0.85,
    12: 0.95, 13: 0.9, 14: 0.75, 15: 0.7, 16: 0.75, 17: 0.85,
    18: 0.9, 19: 1.0, 20: 1.0, 21: 0.9, 22: 0.6, 23: 0.4,
}

DAY_WEIGHTS = {0: 0.85, 1: 0.9, 2: 0.95, 3: 0.95, 4: 0.85, 5: 0.7, 6: 0.75}

MEDIA_WEIGHTS = {"none": 0.6, "image": 0.85, "carousel": 0.95, "video": 1.0}


def score_candidate(post: PostCandidate) -> float:
    f = extract_features(post)

    hour_score = HOUR_WEIGHTS.get(f["hour_of_day"], 0.5)
    day_score = DAY_WEIGHTS.get(f["day_of_week"], 0.7)
    media_score = MEDIA_WEIGHTS.get(post.media_type, 0.6)

    # Sweet spot around 3-5 hashtags; too many reads as spammy
    hc = f["hashtag_count"]
    hashtag_score = max(0.4, 1.0 - abs(hc - 4) * 0.08)

    # Sweet spot around 80-150 chars for short-form platforms
    length = f["content_length"]
    if 80 <= length <= 150:
        length_score = 1.0
    else:
        length_score = max(0.4, 1.0 - abs(length - 115) / 300)

    link_penalty = 0.9 if f["has_link"] else 1.0  # links often suppress reach
    question_bonus = 1.05 if f["has_question_mark"] else 1.0

    raw = (
        hour_score * 0.25
        + day_score * 0.15
        + media_score * 0.25
        + hashtag_score * 0.15
        + length_score * 0.20
    ) * link_penalty * question_bonus

    return round(raw * 100, 2)
