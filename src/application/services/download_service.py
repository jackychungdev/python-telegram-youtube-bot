"""
Download Service

Business logic for download orchestration, queue management, and progress tracking.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import yt_dlp

from domain import Video, DownloadTask, DownloadStatus
from core.exceptions import DownloadError
from application.services.youtube_service import YoutubeService
from application.services.telegram_service import TelegramService
from infrastructure.utils.file_utils import FileUtils
from infrastructure.utils.metadata_probe import MetadataProbe
from infrastructure.external.youtube.quality_selector import QualitySelector
from core.config import Config


logger = logging.getLogger(__name__)


class DownloadService:
    """Service for managing video downloads.
    
    Handles download execution, progress tracking, and file management:
    - Download orchestration with yt-dlp
    - Progress monitoring
    - File format selection
    - Error handling and retries
    
    Attributes:
        download_path: Base path for downloads
        progress_callback: Optional callback for progress updates
    """
    
    def __init__(self, download_path: str = 'downloads'):
        """Initialize download service.
        
        Args:
            download_path: Base path for downloading videos
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self._progress_callbacks: Dict[int, Callable] = {}
    
    async def execute_download(
        self,
        task: DownloadTask,
        quality: str = 'best',
        progress_callback: Optional[Callable] = None
    ) -> Path:
        """Execute video download with progress tracking.
        
        Args:
            task: DownloadTask with video details
            quality: Requested quality ('best', '720', 'audio', etc.)
            progress_callback: Function to call with progress updates
            
        Returns:
            Path to downloaded file
            
        Raises:
            DownloadError: If download fails
        """
        try:
            task.mark_started()
            logger.info(f"Starting download: {task.video_id} (quality: {quality})")
            
            # Prepare download options
            output_template = str(self.download_path / f"{task.video_id}_{quality}.%(ext)s")
            
            ydl_opts = {
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [lambda d: self._progress_hook(d, task)],
            }
            
            # Add quality-specific options
            if quality == 'audio':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                # Video download
                height = quality if quality != 'best' else 'inf'
                ydl_opts.update({
                    'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
                    'merge_output_format': 'mp4',
                })
            
            # Execute download
            url = f'https://www.youtube.com/watch?v={task.video_id}'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: ydl.download([url])
                )
            
            # Find downloaded file
            downloaded_file = self._find_downloaded_file(task.video_id, quality)
            
            if not downloaded_file:
                raise DownloadError("Download completed but file not found")
            
            task.mark_completed()
            logger.info(f"Download completed: {downloaded_file}")
            
            return downloaded_file
            
        except Exception as e:
            logger.error(f"Download failed for {task.video_id}: {e}")
            task.mark_failed(str(e))
            raise DownloadError(f"Download failed: {str(e)}")
    
    def _progress_hook(self, d: Dict[str, Any], task: DownloadTask):
        """yt-dlp progress hook callback.
        
        Args:
            d: Progress dictionary from yt-dlp
            task: Current download task
        """
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total and total > 0:
                percent = int((downloaded / total) * 100)
                task.update_progress(percent)
                
                # Notify callback
                if task.task_id in self._progress_callbacks:
                    self._progress_callbacks[task.task_id](percent)
                    
        elif d['status'] == 'finished':
            task.update_progress(100)
            logger.debug(f"Download finished: {task.video_id}")
    
    def _find_downloaded_file(self, video_id: str, quality: str) -> Optional[Path]:
        """Find the downloaded file in the download directory.
        
        Args:
            video_id: YouTube video ID
            quality: Download quality
            
        Returns:
            Path to file or None
        """
        # Try common extensions
        extensions = ['mp4', 'mkv', 'webm', 'mp3', 'm4a']
        
        for ext in extensions:
            candidate = self.download_path / f"{video_id}_{quality}.{ext}"
            if candidate.exists():
                return candidate
            
            # Also try without quality suffix
            candidate = self.download_path / f"{video_id}.{ext}"
            if candidate.exists():
                return candidate
        
        # Try to find any matching file
        pattern = f"{video_id}*.{extensions[0]}"
        matches = list(self.download_path.glob(pattern))
        
        if matches:
            return matches[0]
        
        return None
    
    def register_progress_callback(self, task_id: int, callback: Callable):
        """Register callback for progress updates.
        
        Args:
            task_id: Task identifier
            callback: Function(progress_percent) to call
        """
        self._progress_callbacks[task_id] = callback
    
    def unregister_progress_callback(self, task_id: int):
        """Remove progress callback.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self._progress_callbacks:
            del self._progress_callbacks[task_id]
    
    async def cancel_download(self, task: DownloadTask):
        """Cancel an ongoing download.
        
        Args:
            task: DownloadTask to cancel
        """
        task.status = DownloadStatus.CANCELLED
        logger.info(f"Download cancelled: {task.video_id}")
        
        # Clean up partial file
        downloaded_file = self._find_downloaded_file(task.video_id, task.quality)
        if downloaded_file and downloaded_file.exists():
            try:
                downloaded_file.unlink()
                logger.debug(f"Cleaned up partial file: {downloaded_file}")
            except Exception as e:
                logger.error(f"Failed to cleanup file: {e}")
    
    def get_download_directory(self) -> Path:
        """Get the base download directory.
        
        Returns:
            Path to download directory
        """
        return self.download_path
    
    def cleanup_old_downloads(self, max_age_hours: int = 24) -> int:
        """Clean up old downloaded files.
        
        Args:
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Number of files deleted
        """
        import time
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        for file_path in self.download_path.iterdir():
            if file_path.is_file():
                file_age = now - file_path.stat().st_mtime
                
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete old file: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old downloads")
        return deleted_count
