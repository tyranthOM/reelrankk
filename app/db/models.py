"""
ReelRank — data model
=======================
Dataclasses matching schema.sql exactly (see that file for constraints —
CHECKs there are the real source of truth; these mirror them for type hints
and convenience properties only).

Tables: videos, tags, video_tags (junction), interactions.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Optional

CATEGORIES = (
    "Sorting", "Trees", "Graphs", "Heaps",
    "Dynamic Programming", "Hashing", "Recursion", "Greedy",
)
SOURCES = ("youtube", "drive")
INTERACTION_TYPES = ("like", "skip", "watch")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Video:
    id: str
    title: str
    category: str
    creator: str
    source: str                 # "youtube" | "drive"
    duration_seconds: int
    youtube_id: Optional[str] = None
    drive_file_id: Optional[str] = None
    thumbnail_url: Optional[str] = None

    likes: int = 0
    skips: int = 0
    total_watch_seconds: float = 0.0
    watch_events: int = 0
    watch_ratio_avg: float = 0.0
    last_interaction_at: Optional[str] = None
    created_at: Optional[str] = None

    tags: list[str] = field(default_factory=list)   # populated via join, not a real column

    def __post_init__(self):
        if self.category not in CATEGORIES:
            raise ValueError(f"Invalid category: {self.category}")
        if self.source not in SOURCES:
            raise ValueError(f"Invalid source: {self.source}")
        if self.source == "youtube" and not self.youtube_id:
            raise ValueError("youtube_id required when source == 'youtube'")
        if self.source == "drive" and not self.drive_file_id:
            raise ValueError("drive_file_id required when source == 'drive'")

    @property
    def embed_url(self) -> str:
        """Drop straight into an <iframe src=...> on the frontend."""
        if self.source == "youtube":
            return f"https://www.youtube.com/embed/{self.youtube_id}"
        return f"https://drive.google.com/file/d/{self.drive_file_id}/preview"

    @property
    def default_thumbnail_url(self) -> str:
        if self.thumbnail_url:
            return self.thumbnail_url
        if self.source == "youtube":
            return f"https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg"
        return f"https://drive.google.com/thumbnail?id={self.drive_file_id}"

    @classmethod
    def from_row(cls, row: sqlite3.Row, tags: Optional[list[str]] = None) -> "Video":
        return cls(
            id=row["id"], title=row["title"], category=row["category"],
            creator=row["creator"], source=row["source"],
            duration_seconds=row["duration_seconds"],
            youtube_id=row["youtube_id"], drive_file_id=row["drive_file_id"],
            thumbnail_url=row["thumbnail_url"],
            likes=row["likes"], skips=row["skips"],
            total_watch_seconds=row["total_watch_seconds"],
            watch_events=row["watch_events"], watch_ratio_avg=row["watch_ratio_avg"],
            last_interaction_at=row["last_interaction_at"], created_at=row["created_at"],
            tags=tags or [],
        )


@dataclass
class Tag:
    id: str
    name: str
    category: Optional[str] = None
    video_count: int = 0


@dataclass
class Interaction:
    id: str
    video_id: str
    type: str                    # "like" | "skip" | "watch"
    user_id: str = "demo-user"
    watch_seconds: Optional[float] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.type not in INTERACTION_TYPES:
            raise ValueError(f"Invalid interaction type: {self.type}")
