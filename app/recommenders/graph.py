"""
Graph + BFS recommender.

Builds an in-memory adjacency graph over videos: two videos are connected
if they share a tag OR share a creator. Given a starting video, BFS
outward N hops and return videos not yet interacted with by the user,
in BFS-discovery order (closest first).
"""
from collections import deque, defaultdict


def build_adjacency(conn) -> dict:
    """video_id -> set(video_id) adjacency, edges via shared tag or creator."""
    adj = defaultdict(set)

    # Edges via shared tag
    rows = conn.execute("""
        SELECT a.video_id AS va, b.video_id AS vb
        FROM video_tags a
        JOIN video_tags b ON a.tag_name = b.tag_name AND a.video_id != b.video_id
    """).fetchall()
    for r in rows:
        adj[r["va"]].add(r["vb"])
        adj[r["vb"]].add(r["va"])

    # Edges via shared creator
    rows = conn.execute("""
        SELECT a.id AS va, b.id AS vb
        FROM videos a
        JOIN videos b ON a.creator = b.creator AND a.id != b.id
    """).fetchall()
    for r in rows:
        adj[r["va"]].add(r["vb"])
        adj[r["vb"]].add(r["va"])

    return adj


def get_last_watched(conn, user_id: str) -> str | None:
    row = conn.execute("""
        SELECT video_id FROM interactions
        WHERE user_id = ? AND type IN ('watch', 'like')
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,)).fetchone()
    return row["video_id"] if row else None


def get_watched_ids(conn, user_id: str) -> set:
    rows = conn.execute("""
        SELECT DISTINCT video_id FROM interactions WHERE user_id = ?
    """, (user_id,)).fetchall()
    return {r["video_id"] for r in rows}


def bfs_recommend(conn, user_id: str, start_video_id: str = None,
                   max_hops: int = 3, limit: int = 10) -> list[str]:
    """Returns list of video_ids in BFS order, excluding already-watched ones."""
    start = start_video_id or get_last_watched(conn, user_id)
    if not start:
        return []

    adj = build_adjacency(conn)
    watched = get_watched_ids(conn, user_id)

    visited = {start}
    queue = deque([(start, 0)])
    result = []

    while queue and len(result) < limit:
        node, hop = queue.popleft()
        if hop >= max_hops:
            continue
        for neighbor in adj.get(node, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            if neighbor not in watched:
                result.append(neighbor)
                if len(result) >= limit:
                    break
            queue.append((neighbor, hop + 1))

    return result
