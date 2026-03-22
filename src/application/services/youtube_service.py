"""
YouTube Service

Business logic for YouTube video operations including metadata fetching,
format selection, and download orchestration.
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import yt_dlp

from src.domain import Video, VideoFormat, VideoQuality
from src.core.exceptions import DownloadError, ValidationError


logger = logging.getLogger(__name__)


class YoutubeService:
    """Service for YouTube video operations.
    
    Handles all YouTube-related business logic:
    - Video metadata extraction
    - Format selection and filtering
    - Quality-based filtering
    - Download preparation
    
    Attributes:
        download_path: Path where videos will be downloaded
        ydl_opts: Base yt-dlp options
    """
    
    def __init__(self, download_path: str = 'downloads'):
        """Initialize YouTube service.
        
        Args:
            download_path: Base path for downloading videos
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # Base yt-dlp options (can be overridden per operation)
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
        }
    
    async def get_video_info(self, url: str) -> Video:
        """Fetch complete video information from YouTube.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video entity with complete metadata
            
        Raises:
            DownloadError: If video info cannot be fetched
            ValidationError: If URL is invalid
        """
        try:
            opts = {
                **self.ydl_opts,
                'writesubtitles': True,
                'writeautomaticsub': True,
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: ydl.extract_info(url, download=False)
                )
                
                if not info:
                    raise DownloadError(f"Failed to extract info from: {url}")
                
                # Convert to Video entity
                video = self._info_to_video(info)
                logger.info(f"Fetched video info: {video.title} by {video.uploader}")
                return video
                
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"YouTube download error for {url}: {e}")
            raise DownloadError(f"Failed to fetch video info: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching video info: {e}")
            raise DownloadError(f"Error extracting video info: {str(e)}")
    
    def _info_to_video(self, info: Dict[str, Any]) -> Video:
        """Convert yt-dlp info dict to Video entity.
        
        Args:
            info: Dictionary from yt-dlp extract_info
            
        Returns:
            Video entity
        """
        # Extract formats
        formats = []
        for fmt in info.get('formats', []):
            video_format = VideoFormat.from_ytdlp_format(fmt)
            if video_format:
                formats.append(video_format)
        
        return Video(
            video_id=info.get('id', ''),
            title=info.get('title', 'Unknown'),
            uploader=info.get('uploader', 'Unknown'),
            uploader_url=info.get('uploader_url', ''),
            duration=float(info.get('duration') or 0),
            thumbnail_url=info.get('thumbnail', ''),
            description=info.get('description'),
            view_count=info.get('view_count'),
            upload_date=info.get('upload_date'),
            formats=formats
        )
    
    def select_best_quality_format(
        self, 
        video: Video, 
        quality: str = 'best'
    ) -> Optional[VideoFormat]:
        """Select best available format matching requested quality.
        
        Args:
            video: Video entity with formats
            quality: Requested quality ('best', '720', '480', 'audio', etc.)
            
        Returns:
            Best matching VideoFormat or None
        """
        if not video.formats:
            return None
        
        # Handle special cases
        if quality == 'audio':
            return self._select_audio_format(video.formats)
        elif quality == 'best':
            return self._select_best_overall_format(video.formats)
        
        # Select specific quality
        try:
            quality_height = int(quality)
            return self._select_quality_format(video.formats, quality_height)
        except ValueError:
            logger.warning(f"Invalid quality specified: {quality}")
            return None
    
    def _select_audio_format(self, formats: List[VideoFormat]) -> Optional[VideoFormat]:
        """Select best audio-only format.
        
        Args:
            formats: List of available formats
            
        Returns:
            Best audio format or None
        """
        audio_formats = [
            f for f in formats 
            if f.is_audio and not f.is_video
        ]
        
        if not audio_formats:
            # Fallback to formats with audio
            audio_formats = [f for f in formats if f.is_audio]
        
        if audio_formats:
            # Sort by bitrate (prefer higher) - using tbr as proxy
            return max(audio_formats, key=lambda f: f.tbr or 0)
        
        return None
    
    def _select_best_overall_format(self, formats: List[VideoFormat]) -> Optional[VideoFormat]:
        """Select best overall format (highest quality with audio).
        
        Args:
            formats: List of available formats
            
        Returns:
            Best format or None
        """
        # Prefer formats with both video and audio
        combined = [f for f in formats if f.is_video and f.is_audio]
        
        if combined:
            return max(combined, key=lambda f: f.height or 0)
        
        # Fallback to highest quality video
        video_formats = [f for f in formats if f.is_video]
        if video_formats:
            return max(video_formats, key=lambda f: f.height or 0)
        
        return None
    
    def _select_quality_format(
        self, 
        formats: List[VideoFormat], 
        target_height: int
    ) -> Optional[VideoFormat]:
        """Select format closest to target quality.
        
        Args:
            formats: List of available formats
            target_height: Target video height in pixels
            
        Returns:
            Closest matching format or None
        """
        # Filter formats with video
        video_formats = [f for f in formats if f.is_video]
        
        if not video_formats:
            return None
        
        # Find closest match
        closest = min(
            video_formats,
            key=lambda f: abs((f.height or 0) - target_height)
        )
        
        return closest
    
    def get_available_qualities(self, video: Video) -> List[VideoQuality]:
        """Get list of available qualities for a video.
        
        Args:
            video: Video entity
            
        Returns:
            Sorted list of available VideoQuality enums
        """
        return video.available_qualities
    
    def validate_url(self, url: str) -> bool:
        """Validate YouTube URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid YouTube URL
        """
        import re
        
        youtube_patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=[\w-]+',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/[\w-]+',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/[\w-]+',
            r'(?:https?:\/\/)?(?:m\.)?youtube\.com\/watch\?v=[\w-]+',  # Mobile support
        ]
        
        for pattern in youtube_patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID or None
        """
        import re
        
        patterns = [
            r'youtube\.com\/watch\?v=([\w-]+)',
            r'youtu\.be\/([\w-]+)',
            r'youtube\.com\/embed\/([\w-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def download_thumbnail(self, url: str, save_path: Path) -> Path:
        """Download video thumbnail.
        
        Args:
            url: Thumbnail URL
            save_path: Where to save the thumbnail
            
        Returns:
            Path to saved thumbnail
        """
        import aiohttp
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())
            
            logger.debug(f"Thumbnail saved to: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Failed to download thumbnail: {e}")
            raise DownloadError(f"Thumbnail download failed: {str(e)}")
