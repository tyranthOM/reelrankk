from pydantic import BaseModel
from typing import Optional, List

CATEGORIES = [
    "Sorting", "Trees", "Graphs", "Heaps",
    "Dynamic Programming", "Hashing", "Recursion", "Greedy"
]


class VideoCreate(BaseModel):
    id: str
    title: str
    category: str
    creator: str
    source: str  # "youtube" | "drive"
    youtube_id: Optional[str] = None
    drive_file_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: int
    tags: List[str] = []


class VideoOut(BaseModel):
    id: str
    title: str
    category: str
    creator: str
    source: str
    youtube_id: Optional[str]
    drive_file_id: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: int
    likes: int
    skips: int
    total_watch_seconds: float
    watch_events: int
    watch_ratio_avg: float
    last_interaction_at: Optional[str]
    created_at: str
    tags: List[str] = []
    embed_url: str
    score: Optional[float] = None


class InteractionCreate(BaseModel):
    user_id: str = "demo-user"
    video_id: str
    type: str  # "like" | "skip" | "watch"
    watch_seconds: Optional[float] = None
