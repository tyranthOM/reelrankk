PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS videos (
    id                   TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    category             TEXT NOT NULL CHECK (category IN
                          ('Sports','Gaming','Food','Tech','Movies')),
    creator              TEXT NOT NULL,
    source               TEXT NOT NULL CHECK (source IN ('youtube','drive')),
    youtube_id           TEXT,
    drive_file_id        TEXT,
    thumbnail_url        TEXT,
    duration_seconds     INTEGER NOT NULL,

    likes                INTEGER DEFAULT 0,
    skips                INTEGER DEFAULT 0,
    total_watch_seconds  REAL DEFAULT 0,
    watch_events         INTEGER DEFAULT 0,
    watch_ratio_avg      REAL DEFAULT 0,
    last_interaction_at  TEXT,

    created_at           TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),

    CHECK (
      (source = 'youtube' AND youtube_id IS NOT NULL) OR
      (source = 'drive' AND drive_file_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS tags (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    category     TEXT,
    video_count  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS video_tags (
    video_id  TEXT NOT NULL,
    tag_name  TEXT NOT NULL,
    PRIMARY KEY (video_id, tag_name),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_name) REFERENCES tags(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interactions (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL DEFAULT 'demo-user',
    video_id      TEXT NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('like','skip','watch')),
    watch_seconds REAL,
    created_at    TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_videos_creator  ON videos(creator);
CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category);
CREATE INDEX IF NOT EXISTS idx_videos_likes    ON videos(likes DESC);

CREATE INDEX IF NOT EXISTS idx_interactions_user_time ON interactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_video     ON interactions(video_id);

CREATE INDEX IF NOT EXISTS idx_video_tags_tag ON video_tags(tag_name);