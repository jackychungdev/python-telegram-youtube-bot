"""
Video entity

Represents a YouTube video with its metadata and formats.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from value_objects.video_quality import VideoQuality


@dataclass
class VideoFormat:
    """Represents a single video/audio format.
    
    Attributes:
        format_id: yt-dlp format ID
        ext: File extension
        resolution: Resolution string (e.g., "1920x1080")
        height: Video height in pixels
        width: Video width in pixels
        vcodec: Video codec (or 'none' for audio-only)
        acodec: Audio codec (or 'none' for video-only)
        filesize: File size in bytes (if available)
        tbr: Total bitrate in kbps
    """
    format_id: str
    ext: str
    resolution: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    tbr: Optional[float] = None
    
    @property
    def is_video(self) -> bool:
        """Check if this format has video."""
        return self.vcodec and self.vcodec != 'none'
    
    @property
    def is_audio(self) -> bool:
        """Check if this format has audio."""
        return self.acodec and self.acodec != 'none'
    
    @classmethod
    def from_ytdlp_format(cls, fmt: Dict) -> 'VideoFormat':
        """Create VideoFormat from yt-dlp format dict.
        
        Args:
            fmt: Format dictionary from yt-dlp
            
        Returns:
            VideoFormat instance
        """
        return cls(
            format_id=fmt.get('format_id', ''),
            ext=fmt.get('ext', ''),
            resolution=fmt.get('resolution'),
            height=fmt.get('height'),
            width=fmt.get('width'),
            vcodec=fmt.get('vcodec'),
            acodec=fmt.get('acodec'),
            filesize=fmt.get('filesize'),
            tbr=fmt.get('tbr')
        )


@dataclass
class Video:
    """Video entity representing a YouTube video.
    
    Attributes:
        video_id: YouTube video ID
        title: Video title
        uploader: Channel name
        uploader_url: Channel URL
        duration: Duration in seconds
        thumbnail_url: Thumbnail image URL
        description: Video description (optional)
        view_count: View count (optional)
        upload_date: Upload date string (optional)
        formats: Available download formats
    """
    video_id: str
    title: str
    uploader: str
    uploader_url: str
    duration: float
    thumbnail_url: str
    description: Optional[str] = None
    view_count: Optional[int] = None
    upload_date: Optional[str] = None
    formats: List[VideoFormat] = field(default_factory=list)
    
    @property
    def url(self) -> str:
        """Get YouTube URL for this video."""
        return f'https://www.youtube.com/watch?v={self.video_id}'
    
    @property
    def short_url(self) -> str:
        """Get shortened YouTube URL."""
        return f'https://youtu.be/{self.video_id}'
    
    @property
    def available_qualities(self) -> List[VideoQuality]:
        """Get list of available video qualities.
        
        Returns:
            Sorted list of available VideoQuality values (highest first)
        """
        if not self.formats:
            return []
        
        heights = set()
        for fmt in self.formats:
            if fmt.is_video and fmt.height:
                heights.add(fmt.height)
        
        quality_map = {
            144: VideoQuality.Q144,
            240: VideoQuality.Q240,
            360: VideoQuality.Q360,
            480: VideoQuality.Q480,
            720: VideoQuality.Q720,
            1080: VideoQuality.Q1080,
            1440: VideoQuality.Q1440,
            2160: VideoQuality.Q2160,
        }
        
        return [quality_map[h] for h in sorted(heights, reverse=True) 
                if h in quality_map]
    
    def has_audio_format(self) -> bool:
        """Check if audio-only format is available.
        
        Returns:
            True if audio-only download is possible
        """
        if not self.formats:
            return False
        
        return any(
            fmt.is_audio and not fmt.is_video
            for fmt in self.formats
        )
    
    def get_formats_for_quality(self, quality: VideoQuality) -> List[VideoFormat]:
        """Get all formats matching a specific quality.
        
        Args:
            quality: Desired video quality
            
        Returns:
            List of matching VideoFormat objects
        """
        if quality == VideoQuality.AUDIO:
            return [fmt for fmt in self.formats if fmt.is_audio and not fmt.is_video]
        
        return [fmt for fmt in self.formats 
                if fmt.height and fmt.height <= quality.height]
