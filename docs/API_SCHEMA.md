# ReelRank — Backend (API) Schema

This is the HTTP-level schema — what routes exist, what they accept, what
they return. Request/response shapes live in `backend_schemas.py`
(Pydantic). Database shape lives in `db/schema.sql` + `db/models.py` — two
different layers, kept separate on purpose (see the note in schemas.py).

## Endpoints

### Feed

**`GET /api/videos/next`**
Returns the single next reel to show, chosen by the active algorithm.
| Query param | Type | Notes |
|---|---|---|
| `algorithm` | `graph` \| `heap` \| `sort` | which module decides |
| `user_id` | string | default `demo-user` |
| `exclude` | string[] | video IDs already shown this session, so we don't repeat |

→ `NextReelOut` (single video + `explain` string for the demo, e.g. *"BFS
depth 2 from last watched: BFS Explained"*)

---

**`GET /api/videos/recommendations`**
Returns the "up next" grid — top N candidates instead of just one.
| Query param | Type | Notes |
|---|---|---|
| `algorithm` | `graph` \| `heap` \| `sort` | |
| `k` | int | default 6 |
| `user_id` | string | default `demo-user` |

→ `RecommendationOut` (list of `VideoOut`)

---

### Interactions

**`POST /api/interactions`**
Records a like / skip / watch event and updates that video's `score_inputs`
columns (`likes`, `skips`, `watch_events`, `watch_ratio_avg`,
`last_interaction_at`) in the same request — so the next `/next` call
reflects it immediately.

Body → `InteractionCreate`
Returns → `InteractionOut`

---

### Videos / Upload

**`POST /api/videos`**
Admin-lite upload — paste a YouTube URL or Drive share link, fill in
title/category/tags.

Body → `VideoCreate` (call `.validate_source_id()` in the route handler
before inserting)
Returns → `VideoOut`

**`GET /api/videos`**
List/browse all videos (used by the upload page to show what's already in).
| Query param | Type | Notes |
|---|---|---|
| `category` | Category? | optional filter |

→ `list[VideoOut]`

---

### Tags

**`GET /api/tags`**
Powers the upload page's tag autocomplete.

→ `list[TagOut]`

## How each algorithm route reads the DB

| Algorithm | Reads | Logic |
|---|---|---|
| `graph` | `interactions` (last watched), `video_tags` joined to `videos` | BFS outward from last-watched video's tags/creator (see `graph.py`, not yet built) |
| `heap` | `videos.likes/watch_ratio_avg/last_interaction_at` | compute score per candidate, `heap.py`'s `MaxHeap`, pop top-K |
| `sort` | same columns as heap | same score formula, `sorted()` instead — same result as heap for top-K, different Big-O, which is the point of showing both |

## Score formula (shared by heap + sort modules)

```
score = w1 * likes + w2 * watch_ratio_avg - w3 * recency_days
```
Suggested weights for the demo: `w1=1.0, w2=50.0, w3=0.5` (tune so no single
input totally dominates — with 18 seed videos, likes range 0–250 and
watch_ratio_avg range 0–1, so w2 needs to be large enough to matter).

## File layout this implies

```
backend/
├── main.py            # FastAPI app, mounts all routes below
├── schemas.py          # ← backend_schemas.py, rename on drop-in
├── graph.py             # not yet built
├── heap.py               # already built — ports heap.c 1:1
├── sort_rank.py           # not yet built
└── routes/
    ├── feed.py            # /api/videos/next, /api/videos/recommendations
    ├── interactions.py     # /api/interactions
    └── videos.py            # /api/videos, /api/tags
```

Say the word when you want `main.py` + the two missing modules
(`graph.py`, `sort_rank.py`) actually built.
