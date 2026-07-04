from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, TIMESTAMP,
    ARRAY, Text, func
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    accounts = relationship("SocialAccount", back_populates="user")


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    platform = Column(String, nullable=False)  # twitter | instagram | facebook | linkedin
    platform_account_id = Column(String, nullable=False)
    display_name = Column(String)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text)
    token_expires_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="accounts")
    posts = relationship("Post", back_populates="account")


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    media_type = Column(String, default="none")
    media_urls = Column(ARRAY(String))
    hashtags = Column(ARRAY(String))
    link_url = Column(String)
    scheduled_time = Column(TIMESTAMP, nullable=False)
    status = Column(String, default="scheduled")  # scheduled|publishing|published|failed|cancelled
    predicted_engagement = Column(Float)
    prediction_source = Column(String)  # heuristic | model
    model_version_id = Column(Integer)
    platform_post_id = Column(String)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    published_at = Column(TIMESTAMP)

    account = relationship("SocialAccount", back_populates="posts")
    metrics = relationship("PostMetric", back_populates="post")


class PostMetric(Base):
    __tablename__ = "post_metrics"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))
    measured_offset_hours = Column(Integer, nullable=False)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    engagement_score = Column(Float)
    measured_at = Column(TIMESTAMP, server_default=func.now())

    post = relationship("Post", back_populates="metrics")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"))
    trained_at = Column(TIMESTAMP, server_default=func.now())
    training_rows = Column(Integer)
    validation_mae = Column(Float)
    heuristic_mae = Column(Float)
    promoted = Column(Boolean, default=False)
    artifact_path = Column(String, nullable=False)
