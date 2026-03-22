"""
User entity

Represents a Telegram user with their preferences and state.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User entity representing a Telegram bot user.
    
    Attributes:
        user_id: Unique Telegram user ID
        username: Telegram username (optional)
        last_video_url: Last processed video URL
        last_online: Last activity timestamp
        awaiting_link: Whether user is waiting to send a link
        downloads_in_hour: Download counter for rate limiting
        last_download_time: Time of last download
        language_code: Preferred language code
        is_authorized: Whether user is authorized to use bot
    """
    user_id: int
    username: Optional[str] = None
    last_video_url: Optional[str] = None
    last_online: Optional[datetime] = None
    awaiting_link: bool = False
    downloads_in_hour: int = 0
    last_download_time: Optional[datetime] = None
    language_code: Optional[str] = None
    is_authorized: bool = False
    
    def __post_init__(self):
        """Convert string dates to datetime objects if needed."""
        if isinstance(self.last_online, str):
            self.last_online = datetime.fromisoformat(self.last_online)
        if isinstance(self.last_download_time, str):
            self.last_download_time = datetime.fromisoformat(self.last_download_time)
    
    def can_download(self, limit_per_hour: int) -> bool:
        """Check if user can download based on rate limit.
        
        Args:
            limit_per_hour: Maximum downloads allowed per hour
            
        Returns:
            True if user can download, False otherwise
        """
        # Admin always bypasses limits
        if self.user_id == -1:  # Will be overridden by actual admin check
            return True
        
        if self.downloads_in_hour < limit_per_hour:
            return True
        
        # Reset counter if hour has passed
        if self.last_download_time:
            elapsed = (datetime.now() - self.last_download_time).total_seconds()
            if elapsed > 3600:
                return True
        
        return False
    
    def reset_download_counter(self):
        """Reset the hourly download counter."""
        self.downloads_in_hour = 0
        self.last_download_time = datetime.now()
    
    def increment_downloads(self):
        """Increment download counter and update timestamp."""
        self.downloads_in_hour += 1
        self.last_download_time = datetime.now()
    
    def update_activity(self, username: str = None, video_url: str = None):
        """Update user activity information.
        
        Args:
            username: Current username
            video_url: Video URL being processed
        """
        if username:
            self.username = username
        if video_url:
            self.last_video_url = video_url
        self.last_online = datetime.now()
