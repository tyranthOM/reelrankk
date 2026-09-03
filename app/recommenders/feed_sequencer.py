"""
Feed sequencer — implements the explore/predict/loop cycle.

Explore (reels 1-10): 2 videos per domain (5 domains), shuffled so no two
consecutive reels share a domain. This constrained shuffle is the same
family of problem as LeetCode's "Reorganize String" / "Task Scheduler":
greedily place the domain with the most remaining videos, skip whichever
domain was just placed, use a max-heap to always know which domain has the
most left. Reuses the same MaxHeap from heap.py -- literally the same DSA
tool, applied to a scheduling problem instead of video ranking.

Predict (reels 11-12): after 10 explore interactions, sum each domain's
accumulated score, take the argmax, serve 2 unshown videos from that
domain's remaining pool (batch 2, or whichever weren't shown in explore).

Loop: after reel 12, domain scores reset to 0, new explore batch is drawn.
Loop 1 explore = batch 1 videos exactly. Loop 2+ = random 2-of-4 per domain.
"""

import random
from .heap import MaxHeap, FeedItem

DOMAINS = ["Sports", "Gaming", "Food", "Tech", "Movies"]

# in-memory session state, keyed by user_id -- fine for a single-demo-user
# class project; would need a real store (DB row or Redis) for multi-user.
_SESSIONS: dict[str, dict] = {}


def _get_session(user_id: str) -> dict:
    if user_id not in _SESSIONS:
        _SESSIONS[user_id] = {
            "loop": 1,
            "position": 0,             # 0-12, resets after 12
            "domain_scores": {d: 0.0 for d in DOMAINS},
            "explore_ids": [],          # the 10 video ids shown this loop
            "shown_ids": set(),          # all ids shown this loop (explore + predict)
        }
    return _SESSIONS[user_id]


def build_pool(conn) -> dict[str, list[dict]]:
    """domain -> list of its 4 video row-dicts, tagged with which batch."""
    pool = {d: [] for d in DOMAINS}
    rows = conn.execute("""
        SELECT v.*, vt.tag_name AS batch_tag
        FROM videos v
        JOIN video_tags vt ON vt.video_id = v.id
        WHERE vt.tag_name IN ('batch1', 'batch2')
    """).fetchall()
    for r in rows:
        d = dict(r)
        pool[d["category"]].append(d)
    return pool


def constrained_shuffle(picks: dict[str, list[dict]]) -> list[dict]:
    """picks: domain -> list of videos to place (any length, here always 2).
    Returns a flat ordering where no two consecutive entries share a domain.
    Heap-based greedy: always place from the domain with the most remaining.
    """
    heap = MaxHeap()
    for domain, vids in picks.items():
        if vids:
            heap.push(FeedItem(reel_id=domain, priority=len(vids)))

    remaining = {d: list(vids) for d, vids in picks.items()}
    result = []
    prev_domain = None
    parked = None  # holds a FeedItem we couldn't place last round (same as prev)

    while heap.size > 0 or parked:
        if heap.size == 0 and parked:
            # only one domain left with items -- can't satisfy the
            # no-adjacent constraint perfectly, place it anyway (edge case,
            # won't occur with 5 domains x 2 items each).
            item = parked
            parked = None
        else:
            item = heap.pop_max()

        if item.reel_id == prev_domain:
            # can't place same domain twice in a row -- park it, try next
            if heap.size == 0:
                # nothing else to interleave with, must place it anyway
                pass
            else:
                parked = item
                item = heap.pop_max()

        video = remaining[item.reel_id].pop()
        result.append(video)
        prev_domain = item.reel_id

        if remaining[item.reel_id]:
            heap.push(FeedItem(reel_id=item.reel_id, priority=len(remaining[item.reel_id])))
        if parked:
            heap.push(parked)
            parked = None

    return result


def start_loop(conn, user_id: str) -> list[dict]:
    """Begin (or restart) a loop: pick explore videos, shuffle, reset scores."""
    session = _get_session(user_id)
    session["domain_scores"] = {d: 0.0 for d in DOMAINS}
    session["position"] = 0
    session["shown_ids"] = set()

    pool = build_pool(conn)
    picks = {}
    for domain, videos in pool.items():
        if session["loop"] == 1:
            batch1 = [v for v in videos if v["batch_tag"] == "batch1"]
            picks[domain] = batch1[:2]
        else:
            picks[domain] = random.sample(videos, 2)

    ordered = constrained_shuffle(picks)
    session["explore_ids"] = [v["id"] for v in ordered]
    session["shown_ids"] = set(session["explore_ids"])
    session["position"] = len(ordered)  # will be 10
    return ordered


def register_interaction(user_id: str, category: str, itype: str,
                          watch_seconds: float = None, duration_seconds: float = None) -> None:
    """Called from the /interactions endpoint to feed the domain score."""
    session = _get_session(user_id)
    if itype == "like":
        weight = 10.0
    elif itype == "skip":
        weight = -5.0
    elif itype == "watch" and watch_seconds and duration_seconds:
        weight = 50.0 * min(watch_seconds / duration_seconds, 1.0)
    else:
        weight = 0.0
    session["domain_scores"][category] = session["domain_scores"].get(category, 0.0) + weight


def get_predict(conn, user_id: str) -> list[dict]:
    """Reels 11-12: winning domain's unshown videos."""
    session = _get_session(user_id)
    winner = max(session["domain_scores"], key=session["domain_scores"].get)

    pool = build_pool(conn)
    candidates = [v for v in pool[winner] if v["id"] not in session["shown_ids"]]
    chosen = candidates[:2] if len(candidates) >= 2 else candidates

    session["shown_ids"].update(v["id"] for v in chosen)
    session["position"] += len(chosen)
    return chosen


def is_loop_complete(user_id: str) -> bool:
    return _get_session(user_id)["position"] >= 12


def advance_loop(user_id: str) -> None:
    _get_session(user_id)["loop"] += 1