"""
Shared scoring formula for the Heap and Sort/Rank recommenders.

Kept in one place deliberately: heap.py and sort_rank.py must agree on what
"good" means, or their top-K results will differ for reasons that have
nothing to do with heap vs. sort mechanics -- which would undermine the
whole point of the demo (same ranking, different algorithm/Big-O to get there).

score = w1*likes + w2*watch_ratio_avg - w3*recency_days

Weights tuned for the 18-video seed set: likes range ~0-250, watch_ratio_avg
range 0-1, recency_days range 0-30ish. w2=50 makes watch_ratio_avg matter
roughly as much as likes; w3=0.5 gives a gentle recency penalty rather than
letting it dominate.
"""

from datetime import datetime, timezone

W_LIKES = 1.0
W_WATCH_RATIO = 50.0
W_RECENCY = 0.5


def recency_days(last_interaction_at: str | None) -> float:
    if not last_interaction_at:
        return 999.0  # never interacted with -> treated as maximally stale
    try:
        dt = datetime.fromisoformat(last_interaction_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return 999.0
    now = datetime.now(timezone.utc)
    return max((now - dt).total_seconds() / 86400.0, 0.0)


def compute_score(row: dict) -> float:
    likes = row.get("likes", 0) or 0
    watch_ratio_avg = row.get("watch_ratio_avg", 0.0) or 0.0
    days = recency_days(row.get("last_interaction_at"))
    return W_LIKES * likes + W_WATCH_RATIO * watch_ratio_avg - W_RECENCY * days
