"""
URL Parser Utility

Comprehensive URL parsing and validation for multiple video platforms.
"""
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs


class URLParser:
    """Utility for parsing and validating video URLs.
    
    Supports multiple platforms:
    - YouTube (youtube.com, youtu.be)
    - Archive.org
    - Direct video links
    
    Attributes:
        supported_platforms: List of supported platform names
    """
    
    # Platform patterns
    PATTERNS = {
        'youtube': [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([\w-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([\w-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([\w-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([\w-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([\w-]+)',
        ],
        'youtube_playlist': [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/playlist\?list=([\w-]+)',
        ],
        'archive_org': [
            r'(?:https?:\/\/)?(?:www\.)?archive\.org\/details\/([\w-]+)',
            r'(?:https?:\/\/)?(?:www\.)?archive\.org\/embed\/([\w-]+)',
        ],
    }
    
    def __init__(self):
        """Initialize URL parser."""
        self.supported_platforms = list(self.PATTERNS.keys())
    
    def parse(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse URL and extract platform information.
        
        Args:
            url: URL to parse
            
        Returns:
            Dictionary with platform, video_id, and extra data or None
        """
        if not url or not isinstance(url, str):
            return None
        
        url = url.strip()
        
        # Try each platform pattern
        for platform, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    result = {
                        'platform': platform,
                        'video_id': match.group(1),
                        'url': url,
                        'raw_query': self._extract_query_params(url)
                    }
                    
                    # Add platform-specific data
                    if platform == 'youtube':
                        result['canonical_url'] = f'https://www.youtube.com/watch?v={result["video_id"]}'
                    elif platform == 'archive_org':
                        result['canonical_url'] = f'https://archive.org/details/{result["video_id"]}'
                    
                    return result
        
        return None
    
    def _extract_query_params(self, url: str) -> Dict[str, str]:
        """Extract query parameters from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Dictionary of query parameters
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Flatten lists (parse_qs returns lists)
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if YouTube URL
        """
        return any(
            re.match(pattern, url) 
            for pattern in self.PATTERNS['youtube']
        )
    
    def is_youtube_playlist(self, url: str) -> bool:
        """Check if URL is a YouTube playlist URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if playlist URL
        """
        return any(
            re.match(pattern, url) 
            for pattern in self.PATTERNS['youtube_playlist']
        )
    
    def is_archive_url(self, url: str) -> bool:
        """Check if URL is an Archive.org URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if Archive.org URL
        """
        return any(
            re.match(pattern, url) 
            for pattern in self.PATTERNS['archive_org']
        )
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from URL.
        
        Args:
            url: Video URL
            
        Returns:
            Video ID or None
        """
        result = self.parse(url)
        return result['video_id'] if result else None
    
    def extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Playlist ID or None
        """
        if not self.is_youtube_url(url):
            return None
        
        query_params = self._extract_query_params(url)
        return query_params.get('list')
    
    def get_canonical_url(self, url: str) -> Optional[str]:
        """Get canonical URL for a video.
        
        Args:
            url: Video URL
            
        Returns:
            Canonical URL or None
        """
        result = self.parse(url)
        return result['canonical_url'] if result else None
    
    def normalize(self, url: str) -> Optional[str]:
        """Normalize URL to canonical form.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL or None
        """
        return self.get_canonical_url(url)
    
    def validate(self, url: str) -> bool:
        """Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid supported URL
        """
        return self.parse(url) is not None
    
    def get_platform(self, url: str) -> Optional[str]:
        """Get platform name from URL.
        
        Args:
            url: Video URL
            
        Returns:
            Platform name or None
        """
        result = self.parse(url)
        return result['platform'] if result else None
    
    def is_supported(self, url: str) -> bool:
        """Check if URL platform is supported.
        
        Args:
            url: URL to check
            
        Returns:
            True if supported
        """
        return self.validate(url)
