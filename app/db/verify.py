"""
ReelRank — verify script (SQLite)
====================================
Sanity check that seed_data.py worked. Run after seeding:

    python verify.py
"""

import sys

from app.db import DB_PATH, get_connection
from app.db.models import Video

EXPECTED_VIDEO_COUNT = 18
EXPECTED_INTERACTION_COUNT = 5
EXPECTED_CATEGORIES = 8


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


def main():
    if not DB_PATH.exists():
        print(f"No database found at {DB_PATH}. Run `python seed_data.py` first.")
        sys.exit(1)

    conn = get_connection()
    cur = conn.cursor()
    all_passed = True

    # --- counts --------------------------------------------------------
    video_count = cur.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    tag_count = cur.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    interaction_count = cur.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    video_tags_count = cur.execute("SELECT COUNT(*) FROM video_tags").fetchone()[0]

    all_passed &= check("videos table populated", video_count == EXPECTED_VIDEO_COUNT,
                         f"found {video_count}, expected {EXPECTED_VIDEO_COUNT}")
    all_passed &= check("tags table populated", tag_count > 0, f"found {tag_count}")
    all_passed &= check("video_tags junction populated", video_tags_count > video_count,
                         f"found {video_tags_count} links across {video_count} videos")
    all_passed &= check("interactions table populated", interaction_count == EXPECTED_INTERACTION_COUNT,
                         f"found {interaction_count}, expected {EXPECTED_INTERACTION_COUNT}")

    # --- foreign keys actually enforced ----------------------------------
    fk_status = cur.execute("PRAGMA foreign_keys").fetchone()[0]
    all_passed &= check("foreign_keys pragma is ON", fk_status == 1, f"value={fk_status}")

    # --- indexes -----------------------------------------------------------
    indexes = [r[1] for r in cur.execute("PRAGMA index_list(videos)").fetchall()]
    all_passed &= check("videos indexes applied", "idx_videos_category" in indexes,
                         f"indexes: {indexes}")

    # --- category coverage --------------------------------------------------
    categories = [r[0] for r in cur.execute("SELECT DISTINCT category FROM videos").fetchall()]
    all_passed &= check("all 8 categories represented", len(categories) == EXPECTED_CATEGORIES,
                         f"found: {sorted(categories)}")

    # --- cross-category tag overlap (needed for the Graph/BFS module) ------
    rows = cur.execute(
        """
        SELECT DISTINCT v.category
        FROM videos v
        JOIN video_tags vt ON vt.video_id = v.id
        WHERE vt.tag_name = 'priority-queue'
        """
    ).fetchall()
    linked_categories = [r[0] for r in rows]
    all_passed &= check("cross-category tag overlap exists ('priority-queue')",
                         len(linked_categories) > 1, f"spans: {linked_categories}")

    # --- CHECK constraint actually rejects bad data ------------------------
    try:
        cur.execute(
            "INSERT INTO videos (id, title, category, creator, source, youtube_id, duration_seconds) "
            "VALUES ('badtest', 'Bad', 'NotACategory', 'X', 'youtube', 'abc', 60)"
        )
        conn.commit()
        all_passed &= check("CHECK constraint rejects invalid category", False, "insert should have failed but didn't")
        cur.execute("DELETE FROM videos WHERE id = 'badtest'")
        conn.commit()
    except Exception as e:
        all_passed &= check("CHECK constraint rejects invalid category", True, type(e).__name__)

    # --- embed_url sanity check --------------------------------------------
    row = cur.execute("SELECT * FROM videos LIMIT 1").fetchone()
    if row:
        tags = [r[0] for r in cur.execute(
            "SELECT tag_name FROM video_tags WHERE video_id = ?", (row["id"],)
        ).fetchall()]
        v = Video.from_row(row, tags=tags)
        print(f"\nSample video: \"{v.title}\"  (tags: {v.tags})")
        print(f"  embed_url:      {v.embed_url}")
        print(f"  thumbnail_url:  {v.default_thumbnail_url}")
        all_passed &= check("embed_url resolves without error", True)

    print("\n" + ("All checks passed." if all_passed else "Some checks failed — see above."))
    conn.close()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
