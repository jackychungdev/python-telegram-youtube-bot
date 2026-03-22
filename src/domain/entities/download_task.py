"""
Download task entity

Represents a download request with its state and progress.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .download_status import DownloadStatus


@dataclass
class DownloadTask:
    """Download task representing a download request.
    
    Attributes:
        chat_id: Telegram chat ID
        user_id: User who requested download
        username: Username of requester
        video_id: YouTube video ID
        url: Original YouTube URL
        quality: Requested quality (e.g., '720', 'audio')
        status: Current download status
        progress_message_id: Message ID for progress updates
        start_message_id: Initial message ID
        file_id: Telegram file ID after upload
        error_message: Error details if failed
        created_at: Task creation timestamp
        started_at: Download start timestamp
        completed_at: Download completion timestamp
        progress_percent: Download progress percentage
    """
    chat_id: int
    user_id: int
    username: str
    video_id: str
    url: str
    quality: str
    status: DownloadStatus = DownloadStatus.PENDING
    progress_message_id: Optional[int] = None
    start_message_id: Optional[int] = None
    file_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: int = 0
    
    def mark_started(self):
        """Mark download as started."""
        self.status = DownloadStatus.DOWNLOADING
        self.started_at = datetime.now()
    
    def mark_queued(self):
        """Mark download as queued."""
        self.status = DownloadStatus.QUEUED
    
    def mark_processing(self):
        """Mark download as processing (after download complete)."""
        self.status = DownloadStatus.PROCESSING
        self.progress_percent = 100
    
    def mark_uploading(self):
        """Mark download as uploading to Telegram."""
        self.status = DownloadStatus.UPLOADING
    
    def mark_completed(self, file_id: str = None):
        """Mark download as completed successfully.
        
        Args:
            file_id: Telegram file ID if available
        """
        self.status = DownloadStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress_percent = 100
        if file_id:
            self.file_id = file_id
    
    def mark_failed(self, error: str):
        """Mark download as failed.
        
        Args:
            error: Error message describing the failure
        """
        self.status = DownloadStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error
    
    def mark_cancelled(self):
        """Mark download as cancelled."""
        self.status = DownloadStatus.CANCELLED
        self.completed_at = datetime.now()
    
    def update_progress(self, percent: int):
        """Update download progress percentage.
        
        Args:
            percent: Progress percentage (0-100)
        """
        self.progress_percent = min(100, max(0, percent))
        # Auto-transition to downloading if still queued
        if self.status == DownloadStatus.QUEUED and percent > 0:
            self.mark_started()
    
    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed time since start in seconds."""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    @property
    def is_active(self) -> bool:
        """Check if download is still active."""
        return self.status.is_active
