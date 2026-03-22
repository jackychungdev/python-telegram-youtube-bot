"""
Quality Selector Utility

Advanced quality selection strategies for YouTube downloads.
"""
from typing import Optional, List, Dict, Any
from src.domain import VideoFormat, VideoQuality


class QualitySelector:
    """Utility for intelligent quality selection.
    
    Provides multiple selection strategies:
    - Best available quality
    - Specific height matching
    - Audio-only extraction
    - Format preference (mp4 over webm)
    - File size estimation
    
    Attributes:
        prefer_mp4: Prefer MP4 container format
        max_audio_bitrate: Maximum audio bitrate in kbps
    """
    
    def __init__(self, prefer_mp4: bool = True):
        """Initialize quality selector.
        
        Args:
            prefer_mp4: Prefer MP4 container when available
        """
        self.prefer_mp4 = prefer_mp4
    
    def select_best(
        self, 
        formats: List[VideoFormat],
        target_quality: str = 'best'
    ) -> Optional[VideoFormat]:
        """Select best format based on strategy.
        
        Args:
            formats: List of available formats
            target_quality: Target quality ('best', 'audio', or specific like '720')
            
        Returns:
            Best matching format or None
        """
        if not formats:
            return None
        
        if target_quality == 'audio':
            return self.select_audio_only(formats)
        elif target_quality == 'best':
            return self.select_best_overall(formats)
        else:
            try:
                height = int(target_quality)
                return self.select_by_height(formats, height)
            except ValueError:
                return None
    
    def select_audio_only(self, formats: List[VideoFormat]) -> Optional[VideoFormat]:
        """Select best audio-only format.
        
        Args:
            formats: List of available formats
            
        Returns:
            Best audio format or None
        """
        # Filter audio-only formats
        audio_formats = [
            f for f in formats
            if f.has_audio() and not f.has_video()
        ]
        
        if not audio_formats:
            # Fallback to formats with good audio
            audio_formats = [
                f for f in formats
                if f.has_audio() and f.audio_bitrate
            ]
        
        if audio_formats:
            # Sort by audio bitrate (descending)
            return max(audio_formats, key=lambda f: f.audio_bitrate or 0)
        
        return None
    
    def select_best_overall(self, formats: List[VideoFormat]) -> Optional[VideoFormat]:
        """Select best overall format (video + audio).
        
        Args:
            formats: List of available formats
            
        Returns:
            Best format or None
        """
        # Prefer formats with both video and audio
        combined = [
            f for f in formats
            if f.has_video() and f.has_audio()
        ]
        
        if combined:
            # Sort by height, then fps, then prefer mp4
            return max(
                combined,
                key=lambda f: (
                    f.height or 0,
                    f.fps or 0,
                    1 if self._is_mp4(f) else 0
                )
            )
        
        # No combined formats, select best video
        video_formats = [f for f in formats if f.has_video()]
        if video_formats:
            return max(
                video_formats,
                key=lambda f: f.height or 0
            )
        
        return None
    
    def select_by_height(
        self, 
        formats: List[VideoFormat], 
        target_height: int
    ) -> Optional[VideoFormat]:
        """Select format closest to target height.
        
        Args:
            formats: List of available formats
            target_height: Target video height (e.g., 720, 1080)
            
        Returns:
            Closest matching format or None
        """
        # Filter video formats
        video_formats = [f for f in formats if f.has_video()]
        
        if not video_formats:
            return None
        
        # Find exact match first
        exact_matches = [f for f in video_formats if f.height == target_height]
        
        if exact_matches:
            # Prefer mp4 among exact matches
            if self.prefer_mp4:
                mp4_matches = [f for f in exact_matches if self._is_mp4(f)]
                if mp4_matches:
                    return mp4_matches[0]
            return exact_matches[0]
        
        # Find closest match (prefer lower or equal height)
        lower_or_equal = [f for f in video_formats if f.height <= target_height]
        
        if lower_or_equal:
            # Get highest from lower or equal
            return max(lower_or_equal, key=lambda f: f.height or 0)
        
        # All formats are higher than target, get lowest
        return min(video_formats, key=lambda f: f.height or 0)
    
    def _is_mp4(self, format_obj: VideoFormat) -> bool:
        """Check if format is MP4 container.
        
        Args:
            format_obj: VideoFormat to check
            
        Returns:
            True if MP4
        """
        if format_obj.ext:
            return format_obj.ext.lower() == 'mp4'
        return False
    
    def filter_qualities(
        self,
        formats: List[VideoFormat],
        min_height: int = 0,
        max_height: int = None
    ) -> List[VideoFormat]:
        """Filter formats by height range.
        
        Args:
            formats: List of formats
            min_height: Minimum height (inclusive)
            max_height: Maximum height (inclusive)
            
        Returns:
            Filtered list of formats
        """
        filtered = [
            f for f in formats
            if f.has_video() and f.height and f.height >= min_height
        ]
        
        if max_height:
            filtered = [f for f in filtered if f.height <= max_height]
        
        return filtered
    
    def get_available_heights(self, formats: List[VideoFormat]) -> List[int]:
        """Get list of available video heights.
        
        Args:
            formats: List of formats
            
        Returns:
            Sorted list of unique heights
        """
        heights = set()
        
        for f in formats:
            if f.has_video() and f.height:
                heights.add(f.height)
        
        return sorted(heights, reverse=True)
    
    def estimate_file_size(
        self,
        format_obj: VideoFormat,
        duration_seconds: float
    ) -> int:
        """Estimate file size for a format.
        
        Args:
            format_obj: VideoFormat
            duration_seconds: Duration in seconds
            
        Returns:
            Estimated file size in bytes
        """
        if not duration_seconds or duration_seconds <= 0:
            return 0
        
        # Calculate from bitrate
        total_bitrate = (format_obj.video_bitrate or 0) + (format_obj.audio_bitrate or 0)
        
        if total_bitrate > 0:
            # Bitrate is in kbps, convert to bytes
            bits_per_second = total_bitrate * 1000
            bytes_per_second = bits_per_second / 8
            return int(bytes_per_second * duration_seconds)
        
        # Fallback: rough estimate based on resolution and duration
        if format_obj.has_video():
            # HD content: ~1-2 MB/s, SD: ~0.5 MB/s
            if format_obj.height and format_obj.height >= 720:
                return int(1.5 * 1024 * 1024 * duration_seconds)
            else:
                return int(0.5 * 1024 * 1024 * duration_seconds)
        
        # Audio only: ~128 kbps = 16 KB/s
        return int(16 * 1024 * duration_seconds)
    
    def compare_formats(
        self,
        format1: VideoFormat,
        format2: VideoFormat
    ) -> int:
        """Compare two formats for quality.
        
        Args:
            format1: First format
            format2: Second format
            
        Returns:
            Positive if format1 is better, negative if format2 is better
        """
        # Compare by height first
        height_diff = (format1.height or 0) - (format2.height or 0)
        if height_diff != 0:
            return height_diff
        
        # Then by FPS
        fps_diff = (format1.fps or 0) - (format2.fps or 0)
        if fps_diff != 0:
            return fps_diff
        
        # Then by total bitrate
        bitrate1 = (format1.video_bitrate or 0) + (format1.audio_bitrate or 0)
        bitrate2 = (format2.video_bitrate or 0) + (format2.audio_bitrate or 0)
        bitrate_diff = bitrate1 - bitrate2
        
        if bitrate_diff != 0:
            return bitrate_diff
        
        # Finally prefer MP4
        if self.prefer_mp4:
            if self._is_mp4(format1) and not self._is_mp4(format2):
                return 1
            elif not self._is_mp4(format1) and self._is_mp4(format2):
                return -1
        
        return 0
    
    def select_optimal(
        self,
        formats: List[VideoFormat],
        max_file_size: int = None,
        duration_seconds: float = None,
        prefer_60fps: bool = False
    ) -> Optional[VideoFormat]:
        """Select optimal format based on constraints.
        
        Args:
            formats: List of formats
            max_file_size: Maximum file size in bytes (optional)
            duration_seconds: Duration for size estimation (optional)
            prefer_60fps: Prefer 60fps content (optional)
            
        Returns:
            Optimal format or None
        """
        if not formats:
            return None
        
        candidates = formats.copy()
        
        # Filter by file size if constraint provided
        if max_file_size and duration_seconds:
            candidates = [
                f for f in candidates
                if self.estimate_file_size(f, duration_seconds) <= max_file_size
            ]
            
            if not candidates:
                # No formats fit constraint, relax and take smallest
                candidates = sorted(
                    formats,
                    key=lambda f: self.estimate_file_size(f, duration_seconds)
                )[:1]
        
        # Sort by quality
        if prefer_60fps:
            candidates.sort(
                key=lambda f: (
                    f.height or 0,
                    f.fps or 0,
                    1 if self._is_mp4(f) else 0
                ),
                reverse=True
            )
        else:
            candidates.sort(
                key=lambda f: (
                    f.height or 0,
                    1 if self._is_mp4(f) else 0
                ),
                reverse=True
            )
        
        return candidates[0] if candidates else None
