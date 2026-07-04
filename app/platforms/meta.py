"""
Instagram/Facebook connector via the Meta Graph API. Instagram publishing
requires a two-step container flow: create a media container, then publish
it. Requires an IG Business/Creator account linked to a Facebook Page, and
a long-lived Page access token (see README for the OAuth app-review process
Meta requires before you can publish on behalf of other users).
"""
import time
import requests
from .base import PlatformConnector, PublishResult, MetricsResult

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class InstagramConnector(PlatformConnector):
    def publish(self, content: str, media_urls: list[str], access_token: str,
                account_id: str) -> PublishResult:
        if not media_urls:
            return PublishResult(
                success=False,
                error_message="Instagram requires at least one image/video URL.",
            )
        try:
            # Step 1: create media container
            container_resp = requests.post(
                f"{GRAPH_API_BASE}/{account_id}/media",
                data={
                    "image_url": media_urls[0],
                    "caption": content,
                    "access_token": access_token,
                },
                timeout=15,
            )
            container_resp.raise_for_status()
            creation_id = container_resp.json()["id"]

            # Step 2: poll container status until ready (containers process async)
            self._wait_for_container_ready(creation_id, access_token)

            # Step 3: publish
            publish_resp = requests.post(
                f"{GRAPH_API_BASE}/{account_id}/media_publish",
                data={"creation_id": creation_id, "access_token": access_token},
                timeout=15,
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json()["id"]
            return PublishResult(success=True, platform_post_id=media_id)
        except requests.HTTPError as e:
            return PublishResult(success=False, error_message=str(e.response.text))
        except Exception as e:
            return PublishResult(success=False, error_message=str(e))

    def fetch_metrics(self, platform_post_id: str, access_token: str) -> MetricsResult:
        try:
            resp = requests.get(
                f"{GRAPH_API_BASE}/{platform_post_id}/insights",
                params={
                    "metric": "likes,comments,shares,impressions",
                    "access_token": access_token,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = {d["name"]: d["values"][0]["value"] for d in resp.json().get("data", [])}
            return MetricsResult(
                likes=data.get("likes", 0),
                comments=data.get("comments", 0),
                shares=data.get("shares", 0),
                impressions=data.get("impressions", 0),
            )
        except Exception:
            return MetricsResult()

    def _wait_for_container_ready(self, creation_id: str, access_token: str,
                                   timeout_seconds: int = 60):
        elapsed = 0
        while elapsed < timeout_seconds:
            resp = requests.get(
                f"{GRAPH_API_BASE}/{creation_id}",
                params={"fields": "status_code", "access_token": access_token},
                timeout=15,
            )
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError("Instagram media container failed to process.")
            time.sleep(2)
            elapsed += 2
        raise TimeoutError("Instagram media container took too long to process.")
