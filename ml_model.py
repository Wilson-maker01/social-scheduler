import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (mean_squared_error, mean_absolute_error, r2_score)
from dataset import generate_dataset

FEATURE_COLUMNS = ['platform_encoded', 'post_type_encoded', 'hour',
                   'day_of_week', 'hashtags', 'mentions', 'has_image',
                   'has_video', 'word_count', 'followers']

def train():
    print("Generating dataset...")
    df = generate_dataset()

    le_platform = LabelEncoder()
    le_post_type = LabelEncoder()

    df['platform_encoded'] = le_platform.fit_transform(df['platform'])
    df['post_type_encoded'] = le_post_type.fit_transform(df['post_type'])

    X = df[FEATURE_COLUMNS]
    y_likes = df['likes']
    y_shares = df['shares']
    y_comments = df['comments']
    y_engagement = df['engagement']

    X_train, X_test, y_likes_train, y_likes_test = train_test_split(
        X, y_likes, test_size=0.2, random_state=42)
    _, _, y_shares_train, y_shares_test = train_test_split(
        X, y_shares, test_size=0.2, random_state=42)
    _, _, y_comments_train, y_comments_test = train_test_split(
        X, y_comments, test_size=0.2, random_state=42)
    _, _, y_engagement_train, y_engagement_test = train_test_split(
        X, y_engagement, test_size=0.2, random_state=42)

    print("Training models...")
    model_likes = RandomForestRegressor(n_estimators=100, random_state=42)
    model_shares = RandomForestRegressor(n_estimators=100, random_state=42)
    model_comments = RandomForestRegressor(n_estimators=100, random_state=42)
    model_engagement = RandomForestRegressor(n_estimators=100, random_state=42)

    model_likes.fit(X_train, y_likes_train)
    model_shares.fit(X_train, y_shares_train)
    model_comments.fit(X_train, y_comments_train)
    model_engagement.fit(X_train, y_engagement_train)

    likes_pred = model_likes.predict(X_test)
    shares_pred = model_shares.predict(X_test)
    comments_pred = model_comments.predict(X_test)
    engagement_pred = model_engagement.predict(X_test)

    metrics = {
        'likes': {
            'r2': round(r2_score(y_likes_test, likes_pred), 4),
            'mae': round(mean_absolute_error(y_likes_test, likes_pred), 2),
            'mse': round(mean_squared_error(y_likes_test, likes_pred), 2),
            'rmse': round(np.sqrt(mean_squared_error(y_likes_test, likes_pred)), 2)
        },
        'shares': {
            'r2': round(r2_score(y_shares_test, shares_pred), 4),
            'mae': round(mean_absolute_error(y_shares_test, shares_pred), 2),
            'mse': round(mean_squared_error(y_shares_test, shares_pred), 2),
            'rmse': round(np.sqrt(mean_squared_error(y_shares_test, shares_pred)), 2)
        },
        'comments': {
            'r2': round(r2_score(y_comments_test, comments_pred), 4),
            'mae': round(mean_absolute_error(y_comments_test, comments_pred), 2),
            'mse': round(mean_squared_error(y_comments_test, comments_pred), 2),
            'rmse': round(np.sqrt(mean_squared_error(y_comments_test, comments_pred)), 2)
        },
        'engagement': {
            'r2': round(r2_score(y_engagement_test, engagement_pred), 4),
            'mae': round(mean_absolute_error(y_engagement_test, engagement_pred), 2),
            'mse': round(mean_squared_error(y_engagement_test, engagement_pred), 2),
            'rmse': round(np.sqrt(mean_squared_error(y_engagement_test, engagement_pred)), 2)
        }
    }

    print("\n=============================")
    print("      MODEL EVALUATION")
    print("=============================")
    for target, m in metrics.items():
        print(f"\n{target.upper()}:")
        print(f"  R² Score:  {m['r2']}")
        print(f"  MAE:       {m['mae']}")
        print(f"  RMSE:      {m['rmse']}")
    print("=============================")

    feature_names = ['Platform', 'Post Type', 'Hour', 'Day of Week',
                    'Hashtags', 'Mentions', 'Has Image', 'Has Video',
                    'Word Count', 'Followers']

    plt.figure(figsize=(10, 6))
    importance = model_engagement.feature_importances_
    indices = np.argsort(importance)[::-1]
    plt.bar(range(len(FEATURE_COLUMNS)), importance[indices],
            color='#6c63ff', alpha=0.8)
    plt.xticks(range(len(FEATURE_COLUMNS)),
               [feature_names[i] for i in indices],
               rotation=45, ha='right')
    plt.title('Feature Importance - Engagement Prediction',
              fontsize=14, fontweight='bold')
    plt.ylabel('Importance Score')
    plt.tight_layout()
    plt.savefig('static/feature_importance.png', dpi=150, bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.scatter(y_engagement_test[:200], engagement_pred[:200],
                alpha=0.5, color='#6c63ff', s=30)
    plt.plot([y_engagement_test.min(), y_engagement_test.max()],
             [y_engagement_test.min(), y_engagement_test.max()],
             'r--', lw=2, label='Perfect Prediction')
    plt.xlabel('Actual Engagement')
    plt.ylabel('Predicted Engagement')
    plt.title('Actual vs Predicted Engagement',
              fontsize=14, fontweight='bold')
    plt.legend()
    plt.tight_layout()
    plt.savefig('static/actual_vs_predicted.png', dpi=150, bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(10, 6))
    platform_engagement = df.groupby('platform')['engagement'].mean().sort_values(ascending=False)
    plt.bar(platform_engagement.index, platform_engagement.values,
            color=['#6c63ff', '#ff6584', '#43e97b', '#fda085', '#38f9d7'])
    plt.title('Average Engagement by Platform',
              fontsize=14, fontweight='bold')
    plt.ylabel('Average Engagement')
    plt.xlabel('Platform')
    plt.tight_layout()
    plt.savefig('static/platform_engagement.png', dpi=150, bbox_inches='tight')
    plt.close()

    print("Plots saved!")

    with open('model_likes.pkl', 'wb') as f:
        pickle.dump(model_likes, f)
    with open('model_shares.pkl', 'wb') as f:
        pickle.dump(model_shares, f)
    with open('model_comments.pkl', 'wb') as f:
        pickle.dump(model_comments, f)
    with open('model_engagement.pkl', 'wb') as f:
        pickle.dump(model_engagement, f)
    with open('encoders.pkl', 'wb') as f:
        pickle.dump({'platform': le_platform, 'post_type': le_post_type}, f)
    with open('ml_metrics.pkl', 'wb') as f:
        pickle.dump(metrics, f)

    print("Models saved!")
    return metrics

def predict(platform, post_type, hour, day_of_week, hashtags,
            mentions, has_image, has_video, word_count, followers=10000):

    with open('model_likes.pkl', 'rb') as f:
        model_likes = pickle.load(f)
    with open('model_shares.pkl', 'rb') as f:
        model_shares = pickle.load(f)
    with open('model_comments.pkl', 'rb') as f:
        model_comments = pickle.load(f)
    with open('model_engagement.pkl', 'rb') as f:
        model_engagement = pickle.load(f)
    with open('encoders.pkl', 'rb') as f:
        encoders = pickle.load(f)

    platform_encoded = encoders['platform'].transform([platform])[0]
    post_type_encoded = encoders['post_type'].transform([post_type])[0]

    features = pd.DataFrame([[platform_encoded, post_type_encoded, hour,
                             day_of_week, hashtags, mentions, has_image,
                             has_video, word_count, followers]],
                            columns=FEATURE_COLUMNS)

    likes = max(0, model_likes.predict(features)[0])
    shares = max(0, model_shares.predict(features)[0])
    comments = max(0, model_comments.predict(features)[0])
    engagement = max(0, model_engagement.predict(features)[0])

    return {
        'likes': round(likes),
        'shares': round(shares),
        'comments': round(comments),
        'engagement': round(engagement)
    }

if __name__ == '__main__':
    train()