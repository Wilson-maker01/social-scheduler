from .twitter import TwitterConnector
from .meta import InstagramConnector

CONNECTORS = {
    "twitter": TwitterConnector(),
    "instagram": InstagramConnector(),
    # "facebook": FacebookConnector(),  # similar shape to InstagramConnector
    # "linkedin": LinkedInConnector(),  # add when you build it
}


def get_connector(platform: str):
    connector = CONNECTORS.get(platform)
    if connector is None:
        raise ValueError(f"No connector implemented for platform '{platform}'")
    return connector
