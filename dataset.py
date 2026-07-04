import numpy as np
import pandas as pd

def generate_dataset():
    np.random.seed(42)
    n_samples = 1000

    # Platforms
    platforms = ['instagram', 'twitter', 'facebook', 'linkedin', 'tiktok']
    post_types = ['image', 'video', 'text', 'story', 'reel']

    data = []

    for _ in range(n_samples):
        platform = np.random.choice(platforms)
        post_type = np.random.choice(post_types)
        hour = np.random.randint(0, 24)
        day_of_week = np.random.randint(0, 7)
        hashtags = np.random.randint(0, 30)
        mentions = np.random.randint(0, 10)
        has_image = np.random.choice([0, 1])
        has_video = np.random.choice([0, 1])
        word_count = np.random.randint(10, 500)
        followers = np.random.randint(100, 10000)

        # Platform engagement multipliers
        platform_mult = {
            'instagram': 1.5,
            'tiktok': 2.0,
            'twitter': 0.8,
            'facebook': 1.0,
            'linkedin': 0.9
        }

        # Post type multipliers
        type_mult = {
            'video': 2.0,
            'reel': 2.5,
            'image': 1.5,
            'story': 1.2,
            'text': 0.8
        }

        # Time of day multiplier
        if hour in [8, 9, 12, 17, 18, 19, 20]:
            time_mult = 1.5
        elif hour in [6, 7, 10, 11, 13, 14, 15, 16]:
            time_mult = 1.2
        else:
            time_mult = 0.7

        # Day of week multiplier
        if day_of_week in [5, 6]:  # Weekend
            day_mult = 1.3
        elif day_of_week in [1, 2, 3]:  # Midweek
            day_mult = 1.1
        else:
            day_mult = 1.0

        # Base engagement
        base = followers * 0.05

        # Calculate engagement
        mult = (platform_mult[platform] * type_mult[post_type] *
                time_mult * day_mult)

        hashtag_boost = min(hashtags * 0.02, 0.3)
        image_boost = 0.2 if has_image else 0
        video_boost = 0.3 if has_video else 0

        likes = max(0, int(base * mult * (1 + hashtag_boost + image_boost + video_boost) +
                           np.random.normal(0, base * 0.1)))
        shares = max(0, int(likes * 0.15 + np.random.normal(0, likes * 0.05)))
        comments = max(0, int(likes * 0.08 + np.random.normal(0, likes * 0.03)))
        engagement = likes + shares + comments

        data.append({
            'platform': platform,
            'post_type': post_type,
            'hour': hour,
            'day_of_week': day_of_week,
            'hashtags': hashtags,
            'mentions': mentions,
            'has_image': has_image,
            'has_video': has_video,
            'word_count': word_count,
            'followers': followers,
            'likes': likes,
            'shares': shares,
            'comments': comments,
            'engagement': engagement
        })

    return pd.DataFrame(data) 
