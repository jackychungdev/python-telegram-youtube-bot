"""
Video quality value object

Defines available video quality levels as a value object.
"""
from enum import Enum


class VideoQuality(Enum):
    """Video quality levels available for download.
    
    Each quality represents a maximum height in pixels.
    """
    Q144 = '144'      # 144p
    Q240 = '240'      # 240p
    Q360 = '360'      # 360p
    Q480 = '480'      # 480p
    Q720 = '720'      # 720p (HD)
    Q1080 = '1080'    # 1080p (Full HD)
    Q1440 = '1440'    # 1440p (2K)
    Q2160 = '2160'    # 2160p (4K)
    AUDIO = 'audio'   # Audio only
    
    @property
    def height(self) -> int:
        """Get the height in pixels for this quality."""
        if self == self.AUDIO:
            return 0
        return int(self.value)
    
    @property
    def is_audio_only(self) -> bool:
        """Check if this is audio-only quality."""
        return self == self.AUDIO
    
    @classmethod
    def from_height(cls, height: int) -> 'VideoQuality':
        """Create VideoQuality from pixel height.
        
        Args:
            height: Video height in pixels
            
        Returns:
            Closest VideoQuality enum value
        """
        if height >= 2160:
            return cls.Q2160
        elif height >= 1440:
            return cls.Q1440
        elif height >= 1080:
            return cls.Q1080
        elif height >= 720:
            return cls.Q720
        elif height >= 480:
            return cls.Q480
        elif height >= 360:
            return cls.Q360
        elif height >= 240:
            return cls.Q240
        else:
            return cls.Q144
    
    @classmethod
    def get_all_qualities(cls) -> list:
        """Get all available qualities sorted by quality (highest first).
        
        Returns:
            List of VideoQuality enums excluding AUDIO
        """
        return [q for q in cls if q != cls.AUDIO]
