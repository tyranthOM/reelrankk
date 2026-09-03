"""
Heap recommender module.

Direct port of heap.c / heap.h -- same bubble_up/bubble_down structure,
kept explicit rather than using Python's built-in heapq, since showing the
heap mechanics is the point of this module in the demo.

top_k_by_heap() mirrors sort_rank.py's top_k_by_sort() calling convention
(same signature: conn, k, category) and uses the SAME compute_score() from
scoring.py, so heap and sort return identical rankings -- the only
difference visible in the demo should be O(n log k) vs O(n log n), not the
actual videos chosen.
"""
from dataclasses import dataclass

from .scoring import compute_score


@dataclass
class FeedItem:
    reel_id: str
    priority: float


class MaxHeap:
    def __init__(self):
        self.items: list[FeedItem] = []

    @property
    def size(self) -> int:
        return len(self.items)

    def _swap(self, i: int, j: int) -> None:
        self.items[i], self.items[j] = self.items[j], self.items[i]

    def _bubble_up(self, i: int) -> None:
        while i > 0:
            parent = (i - 1) // 2
            if self.items[parent].priority >= self.items[i].priority:
                break
            self._swap(parent, i)
            i = parent

    def _bubble_down(self, i: int) -> None:
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            largest = i
            if left < self.size and self.items[left].priority > self.items[largest].priority:
                largest = left
            if right < self.size and self.items[right].priority > self.items[largest].priority:
                largest = right
            if largest == i:
                break
            self._swap(i, largest)
            i = largest

    def push(self, item: FeedItem) -> None:
        self.items.append(item)
        self._bubble_up(self.size - 1)

    def pop_max(self) -> FeedItem:
        if self.size == 0:
            raise IndexError("pop_max() called on an empty heap")
        top = self.items[0]
        last = self.items.pop()
        if self.items:
            self.items[0] = last
            self._bubble_down(0)
        return top


def top_k(scored_videos: list[tuple[str, float]], k: int) -> list[str]:
    """Low-level: scored_videos = [(video_id, score), ...] -> top-k video_ids."""
    h = MaxHeap()
    for video_id, score in scored_videos:
        h.push(FeedItem(reel_id=video_id, priority=score))
    return [h.pop_max().reel_id for _ in range(min(k, h.size))]


def top_k_by_heap(conn, k: int = 10, category: str = None) -> list[dict]:
    """Same calling convention as sort_rank.top_k_by_sort: queries videos,
    computes score, returns full row dicts (with 'score' attached) for the
    top-k, ranked via the heap instead of sorted()."""
    query = "SELECT * FROM videos"
    params = ()
    if category:
        query += " WHERE category = ?"
        params = (category,)

    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    by_id = {row["id"]: row for row in rows}
    for row in rows:
        row["score"] = compute_score(row)

    ranked_ids = top_k([(row["id"], row["score"]) for row in rows], k)
    return [by_id[vid] for vid in ranked_ids]
