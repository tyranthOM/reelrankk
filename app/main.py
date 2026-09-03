import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db.db import get_connection, init_db
from app.recommenders import graph, heap, sort_rank, feed_sequencer
from app.schemas import VideoCreate, VideoOut, InteractionCreate, CATEGORIES
from app.recommenders.scoring import compute_score

app = FastAPI(title="ReelRank API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before real deploy
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()  # safe on repeat runs, schema.sql uses CREATE TABLE/INDEX IF NOT EXISTS


# ---------- helpers ----------

def embed_url(row: dict) -> str:
    if row["source"] == "youtube":
        return f"https://www.youtube.com/embed/{row['youtube_id']}"
    return f"https://drive.google.com/file/d/{row['drive_file_id']}/preview"


def video_row_to_out(conn, row: dict, with_score: bool = False) -> dict:
    tags = [r["tag_name"] for r in conn.execute(
        "SELECT tag_name FROM video_tags WHERE video_id = ?", (row["id"],)
    ).fetchall()]
    out = dict(row)
    out["tags"] = tags
    out["embed_url"] = embed_url(row)
    if with_score:
        out["score"] = row.get("score", compute_score(row))
    else:
        out["score"] = None
    return out


# ---------- video CRUD ----------

@app.post("/videos", response_model=VideoOut)
def create_video(video: VideoCreate):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO videos (id, title, category, creator, source,
                youtube_id, drive_file_id, thumbnail_url, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (video.id, video.title, video.category, video.creator, video.source,
              video.youtube_id, video.drive_file_id, video.thumbnail_url,
              video.duration_seconds))

        for tag in video.tags:
            conn.execute("INSERT OR IGNORE INTO tags (id, name) VALUES (?, ?)",
                         (tag, tag))
            conn.execute("INSERT OR IGNORE INTO video_tags (video_id, tag_name) VALUES (?, ?)",
                         (video.id, tag))
            conn.execute("UPDATE tags SET video_count = video_count + 1 WHERE name = ?",
                         (tag,))

        conn.commit()
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video.id,)).fetchone()
        return video_row_to_out(conn, dict(row))
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/videos", response_model=list[VideoOut])
def list_videos(category: str = None):
    conn = get_connection()
    try:
        if category:
            rows = conn.execute("SELECT * FROM videos WHERE category = ?", (category,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM videos").fetchall()
        return [video_row_to_out(conn, dict(r)) for r in rows]
    finally:
        conn.close()


@app.get("/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: str):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="video not found")
        return video_row_to_out(conn, dict(row))
    finally:
        conn.close()


@app.delete("/videos/{video_id}")
def delete_video(video_id: str):
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="video not found")
        return {"deleted": video_id}
    finally:
        conn.close()


# ---------- interactions ----------

@app.post("/interactions")
def create_interaction(interaction: InteractionCreate):
    conn = get_connection()
    try:
        iid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO interactions (id, user_id, video_id, type, watch_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (iid, interaction.user_id, interaction.video_id, interaction.type,
              interaction.watch_seconds, now))

        # existing per-video denormalized stats (used by heap/sort/compute_score)
        row = conn.execute("SELECT category, duration_seconds, total_watch_seconds, watch_events, watch_ratio_avg FROM videos WHERE id = ?",
                            (interaction.video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="video not found")

        if interaction.type == "like":
            conn.execute("UPDATE videos SET likes = likes + 1, last_interaction_at = ? WHERE id = ?",
                         (now, interaction.video_id))
        elif interaction.type == "skip":
            conn.execute("UPDATE videos SET skips = skips + 1, last_interaction_at = ? WHERE id = ?",
                         (now, interaction.video_id))
        elif interaction.type == "watch" and interaction.watch_seconds is not None:
            new_total = row["total_watch_seconds"] + interaction.watch_seconds
            new_events = row["watch_events"] + 1
            ratio = interaction.watch_seconds / row["duration_seconds"] if row["duration_seconds"] else 0
            conn.execute("""
                UPDATE videos SET
                    total_watch_seconds = ?,
                    watch_events = ?,
                    watch_ratio_avg = ((watch_ratio_avg * watch_events) + ?) / ?,
                    last_interaction_at = ?
                WHERE id = ?
            """, (new_total, new_events, ratio, new_events, now, interaction.video_id))

        conn.commit()

        # NEW: feed this interaction into the explore/predict session's domain score
        feed_sequencer.register_interaction(
            interaction.user_id, row["category"], interaction.type,
            watch_seconds=interaction.watch_seconds, duration_seconds=row["duration_seconds"]
        )

        return {"id": iid, "recorded": True}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


# ---------- DSA recommender endpoints (kept for /docs testing) ----------

@app.get("/recommend/graph", response_model=list[VideoOut])
def recommend_graph(user_id: str = "demo-user", start_video_id: str = None,
                     max_hops: int = 3, limit: int = 10):
    conn = get_connection()
    try:
        ids = graph.bfs_recommend(conn, user_id, start_video_id, max_hops, limit)
        rows = []
        for vid in ids:
            r = conn.execute("SELECT * FROM videos WHERE id = ?", (vid,)).fetchone()
            if r:
                rows.append(video_row_to_out(conn, dict(r)))
        return rows
    finally:
        conn.close()


@app.get("/recommend/heap", response_model=list[VideoOut])
def recommend_heap(k: int = 10, category: str = None):
    conn = get_connection()
    try:
        rows = heap.top_k_by_heap(conn, k, category)
        return [video_row_to_out(conn, r, with_score=True) for r in rows]
    finally:
        conn.close()


@app.get("/recommend/sort", response_model=list[VideoOut])
def recommend_sort(k: int = 10, category: str = None):
    conn = get_connection()
    try:
        rows = sort_rank.top_k_by_sort(conn, k, category)
        return [video_row_to_out(conn, r, with_score=True) for r in rows]
    finally:
        conn.close()


# ---------- feed sequencer (explore / predict / loop) ----------

@app.get("/feed/start", response_model=list[VideoOut])
def feed_start(user_id: str = "demo-user"):
    """Reels 1-10: shuffled explore batch (no two adjacent reels share a domain)."""
    conn = get_connection()
    try:
        rows = feed_sequencer.start_loop(conn, user_id)
        return [video_row_to_out(conn, r) for r in rows]
    finally:
        conn.close()


@app.get("/feed/predict", response_model=list[VideoOut])
def feed_predict(user_id: str = "demo-user"):
    """Reels 11-12: 2 videos from whichever domain scored highest in reels 1-10."""
    conn = get_connection()
    try:
        rows = feed_sequencer.get_predict(conn, user_id)
        feed_sequencer.advance_loop(user_id)  # next /feed/start call = new loop
        return [video_row_to_out(conn, r) for r in rows]
    finally:
        conn.close()


@app.get("/categories")
def get_categories():
    return CATEGORIES


@app.get("/")
def root():
    return {"status": "ReelRank API running"}