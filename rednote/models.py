from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RedNote:
    """Represents a Xiaohongshu note to be published."""
    title: str
    content: str
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    post_time: Optional[str] = None

@dataclass
class RedPublishResult:
    """Represents the result of a publishing attempt."""
    success: bool
    message: str
    note_title: str
    final_url: Optional[str] = None
