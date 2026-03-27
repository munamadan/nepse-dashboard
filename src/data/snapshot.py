import logging

logger = logging.getLogger(__name__)


def load_snapshot(symbol: str) -> list[dict]:
    logger.warning(
        f"load_snapshot({symbol}): snapshot not yet built — returning empty. "
        "Run scripts/capture_snapshot.py on Day 3."
    )
    return []
