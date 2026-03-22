"""
Download status value object

Defines the possible states of a download task.
"""
from enum import Enum


class DownloadStatus(Enum):
    """Download task status values.
    
    Represents the state machine of a download operation.
    """
    PENDING = 'pending'          # Created but not queued
    QUEUED = 'queued'            # In download queue
    DOWNLOADING = 'downloading'  # Currently downloading
    PROCESSING = 'processing'    # Download complete, processing media
    UPLOADING = 'uploading'      # Uploading to Telegram
    COMPLETED = 'completed'      # Successfully completed
    FAILED = 'failed'            # Failed with error
    CANCELLED = 'cancelled'      # Cancelled by user/admin
    
    @property
    def is_active(self) -> bool:
        """Check if download is in an active state."""
        return self in (
            self.PENDING,
            self.QUEUED,
            self.DOWNLOADING,
            self.PROCESSING,
            self.UPLOADING
        )
    
    @property
    def is_finished(self) -> bool:
        """Check if download has finished (success or failure)."""
        return self in (self.COMPLETED, self.FAILED, self.CANCELLED)
    
    @property
    def is_error(self) -> bool:
        """Check if download ended with error."""
        return self == self.FAILED
