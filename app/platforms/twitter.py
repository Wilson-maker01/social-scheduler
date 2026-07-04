"""
Twitter/X connector using API v2 (tweepy). Requires a user-context OAuth 2.0
access token obtained via the PKCE flow with 'tweet.read tweet.write
users.read offline.access' scopes (you'll need to build that OAuth callback
route yourself — see README).
"""
import tweepy
from .base import PlatformConnector, PublishResult, MetricsResult


class TwitterConnector(PlatformConnector):
    def publish(self, content: str, media_urls: list[str], access_token: str,
                account_id: str) -> PublishResult:
        try:
            client = tweepy.Client(access_token)
            media_ids = None
            if media_urls:
                # Media upload requires v1.1 endpoints with OAuth1 user context,
                # or the newer media upload endpoint with OAuth2 — upload each
                # URL's bytes and collect IDs. Left as a call-out since it needs
                # your media-hosting/download step first.
                media_ids = self._upload_media(media_urls, access_token)

            response = client.create_tweet(text=content, media_ids=media_ids)
            tweet_id = response.data.get("id")
            return PublishResult(success=True, platform_post_id=str(tweet_id))
        except Exception as e:
            return PublishResult(success=False, error_message=str(e))

    def fetch_metrics(self, platform_post_id: str, access_token: str) -> MetricsResult:
        try:
            client = tweepy.Client(access_token)
            tweet = client.get_tweet(
                platform_post_id,
                tweet_fields=["public_metrics"],
            )
            m = tweet.data.public_metrics
            return MetricsResult(
                likes=m.get("like_count", 0),
                comments=m.get("reply_count", 0),
                shares=m.get("retweet_count", 0) + m.get("quote_count", 0),
                impressions=m.get("impression_count", 0),
            )
        except Exception:
            return MetricsResult()

    def _upload_media(self, media_urls: list[str], access_token: str) -> list[str]:
        # Placeholder: implement download-then-upload-to-Twitter here.
        raise NotImplementedError("Media upload needs your media pipeline wired in.")
