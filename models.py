from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    post_type = db.Column(db.String(50), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    hashtags = db.Column(db.Integer, default=0)
    mentions = db.Column(db.Integer, default=0)
    has_image = db.Column(db.Boolean, default=False)
    has_video = db.Column(db.Boolean, default=False)
    word_count = db.Column(db.Integer, default=0)
    predicted_likes = db.Column(db.Float, default=0)
    predicted_shares = db.Column(db.Float, default=0)
    predicted_comments = db.Column(db.Float, default=0)
    predicted_engagement = db.Column(db.Float, default=0)
    actual_likes = db.Column(db.Float, default=0)
    actual_shares = db.Column(db.Float, default=0)
    actual_comments = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
