# ReelRank — Database Layer (SQLite)

Replaces the earlier MongoDB version. Pure Python stdlib — no dependencies
to install at all.

## Files

- `schema.sql` — your schema, as-is (source of truth for constraints).
- `db.py` — connection helper (`get_connection`, `init_db`).
- `models.py` — dataclasses mirroring the schema (`Video`, `Tag`, `Interaction`),
  plus `Video.embed_url` / `Video.default_thumbnail_url` helpers for the frontend.
- `seed_data.py` — builds `reelrank.db` from `schema.sql` and inserts 18 sample
  videos across all 8 categories, 23 tags, 48 tag links, and 5 demo interactions.
- `verify.py` — automated sanity check (see below).

## Running it

```bash
python seed_data.py
python verify.py
```

That's it — no env vars, no external server, no Docker, no Atlas account.
`reelrank.db` is created next to these scripts. Re-running `seed_data.py`
wipes and recreates it (`reset=True` in `init_db`).

**This has actually been run and verified** — `verify.py` output:

```
[PASS] videos table populated — found 18, expected 18
[PASS] tags table populated — found 23
[PASS] video_tags junction populated — found 48 links across 18 videos
[PASS] interactions table populated — found 5, expected 5
[PASS] foreign_keys pragma is ON — value=1
[PASS] videos indexes applied
[PASS] all 8 categories represented
[PASS] cross-category tag overlap exists ('priority-queue') — spans: ['Graphs', 'Heaps']
[PASS] CHECK constraint rejects invalid category — IntegrityError
[PASS] embed_url resolves without error
All checks passed.
```

The `priority-queue` tag deliberately spans Graphs (Dijkstra's Algorithm)
and Heaps — that's the cross-category edge the Graph/BFS module will use.

## ⚠️ Important: SQLite + Vercel serverless

If you deploy the FastAPI backend to **Vercel serverless functions**,
writes to `reelrank.db` will **not persist**. Vercel's function filesystem
is read-only except `/tmp`, and `/tmp` is wiped on every cold start — so
likes/skips/watch-time updates would silently vanish between requests.

This is fine for:
- Running the backend **locally** during your live PPT demo (which is
  probably what you actually want for a classroom demo anyway — full
  control, no network dependency).
- Deploying the backend to a host with a **persistent disk**: Render,
  Fly.io, Railway, a plain VPS.

If you do want it live on Vercel with real persistence later, the fix is
**Turso** (SQLite-compatible, but a real hosted service — same SQL, no
code changes beyond the connection string) rather than a local `.db` file.

The **frontend** (React) still deploys to Vercel with zero issues either
way — this limitation is specific to where the SQLite file physically lives.

## Browsing the data directly

```bash
sqlite3 reelrank.db
sqlite> SELECT title, category FROM videos LIMIT 5;
sqlite> .quit
```

Or open `reelrank.db` in DB Browser for SQLite (free GUI) if you'd rather
click through it.

## Next step

Same as before — FastAPI backend + the three recommender modules
(`graph.py`, `heap.py`, `sort_rank.py`) reading from these tables via
plain SQL queries (BFS needs `video_tags` joined back to `videos`; Heap
and Sort/Rank read `likes`/`watch_ratio_avg`/`last_interaction_at`
directly off `videos`). Say the word when you want that built.
