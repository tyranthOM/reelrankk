"""
Sort/Rank recommender.

Same score formula as the heap module, but sorts the *entire* list
with sorted() -- O(n log n) -- to make the contrast against the
heap's O(n log k) visible in the demo.
"""
from .scoring import compute_score


def top_k_by_sort(conn, k: int = 10, category: str = None) -> list[dict]:
    query = "SELECT * FROM videos"
    params = ()
    if category:
        query += " WHERE category = ?"
        params = (category,)

    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    for row in rows:
        row["score"] = compute_score(row)

    ranked = sorted(rows, key=lambda r: r["score"], reverse=True)
    return ranked[:k]
