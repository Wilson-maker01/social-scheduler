"""
Common interface every platform connector implements. The scheduler and API
only ever talk to this interface, never to tweepy/requests/etc. directly —
that's what makes adding a new platform a one-file change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PublishResult:
    success: bool
    platform_post_id: str | None = None
    error_message: str | None = None


@dataclass
class MetricsResult:
    likes: int = 0
    comments: int = 0
    shares: int = 0
    impressions: int = 0

    def engagement_score(self) -> float:
        """Simple weighted composite; tune weights to match what you care about."""
        return round(
            self.likes * 1.0 + self.comments * 2.0 + self.shares * 3.0
            + self.impressions * 0.01,
            2,
        )


class PlatformConnector(ABC):
    @abstractmethod
    def publish(self, content: str, media_urls: list[str], access_token: str,
                account_id: str) -> PublishResult:
        ...

    @abstractmethod
    def fetch_metrics(self, platform_post_id: str, access_token: str) -> MetricsResult:
        ...
