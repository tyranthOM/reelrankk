"""
ReelRank — seed script (final: 5 domains x 4 videos = 20 total)
Batch 1 = first 2 per domain (explore, loop 1 fixed)
Batch 2 = next 2 per domain (prediction pool)
"""
import random
from db import DB_PATH, init_db

MY_VIDEOS = [
    # Sports 
    dict(title="Sports Reel 1", category="Sports", creator="Creator", youtube_id="PPKl0a1CRxE", batch=1),
    dict(title="Sports Reel 2", category="Sports", creator="Creator", youtube_id="n3nSmnIMHbQ", batch=1),
    dict(title="Sports Reel 3", category="Sports", creator="Creator", youtube_id="CCa1t7DbMsw", batch=2),
    dict(title="Sports Reel 4", category="Sports", creator="Creator", youtube_id="_cj17ngg5bc", batch=2),
    # Gaming
    dict(title="Gaming Reel 1", category="Gaming", creator="Creator", youtube_id="ZeN-mVKd0UY", batch=1),
    dict(title="Gaming Reel 2", category="Gaming", creator="Creator", youtube_id="XzagEYM1aOI", batch=1),
    dict(title="Gaming Reel 3", category="Gaming", creator="Creator", youtube_id="Ee7P-MVzA8w", batch=2),
    dict(title="Gaming Reel 4", category="Gaming", creator="Creator", youtube_id="EGTUE_eLkwU", batch=2),
    # Food
    dict(title="Food Reel 1", category="Food", creator="Creator", youtube_id="0KaM2wO5NSs", batch=1),
    dict(title="Food Reel 2", category="Food", creator="Creator", youtube_id="OEx3h4yD5-E", batch=1),
    dict(title="Food Reel 3", category="Food", creator="Creator", youtube_id="A5hrMz_LeyY?", batch=2),
    dict(title="Food Reel 4", category="Food", creator="Creator", youtube_id="M9jmTp3h_Zg", batch=2),
    # Tech
    dict(title="Tech Reel 1", category="Tech", creator="Creator", youtube_id="vsRy-g5Hc-8", batch=1),
    dict(title="Tech Reel 2", category="Tech", creator="Creator", youtube_id="dWERTtzlZgA", batch=1),
    dict(title="Tech Reel 3", category="Tech", creator="Creator", youtube_id="d9rEk96zcco", batch=2),
    dict(title="Tech Reel 4", category="Tech", creator="Creator", youtube_id="3on5z1welxk", batch=2),
    # Movies
    dict(title="Movies Reel 1", category="Movies", creator="Creator", youtube_id="rd8zBiitdmE", batch=1),
    dict(title="Movies Reel 2", category="Movies", creator="Creator", youtube_id="bOreolmPxSI", batch=1),
    dict(title="Movies Reel 3", category="Movies", creator="Creator", youtube_id="ap777f-3H7w", batch=2),
    dict(title="Movies Reel 4", category="Movies", creator="Creator", youtube_id="ZRRGUkYaHp0", batch=2),
]


def main():
    print(f"Creating {DB_PATH} from schema.sql (reset=True) ...")
    conn = init_db(reset=True)
    cur = conn.cursor()

    import uuid
    for spec in MY_VIDEOS:
        vid = uuid.uuid4().hex[:12]
        cur.execute("""
            INSERT INTO videos (id, title, category, creator, source, youtube_id,
                duration_seconds, likes, skips, total_watch_seconds, watch_events, watch_ratio_avg)
            VALUES (?, ?, ?, ?, 'youtube', ?, 60, 0, 0, 0, 0, 0)
        """, (vid, spec["title"], spec["category"], spec["creator"], spec["youtube_id"]))

        tag_name = f"batch{spec['batch']}"
        cur.execute("INSERT OR IGNORE INTO tags (id, name, category) VALUES (?, ?, ?)",
                    (uuid.uuid4().hex[:12], tag_name, spec["category"]))
        cur.execute("INSERT INTO video_tags (video_id, tag_name) VALUES (?, ?)", (vid, tag_name))

    conn.commit()
    conn.close()
    print(f"Inserted {len(MY_VIDEOS)} videos across 5 domains.")


if __name__ == "__main__":
    main()