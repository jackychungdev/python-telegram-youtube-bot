"""
Cache Service

Business logic for file caching, cache invalidation, and storage management.
"""
import asyncio
import logging
from typing import Optional, Tuple, List
from aiocache import cached

from infrastructure.persistence import VideoRepository
from core.exceptions import BotException


logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing video file cache.
    
    Handles caching strategies, cache lookup, and storage optimization:
    - Check cache before download
    - Save newly downloaded files
    - Cache invalidation policies
    - Storage quota management
    
    Attributes:
        video_repo: Repository for cache metadata
        cache_enabled: Whether caching is enabled
        max_cache_age_days: Maximum age of cached files
    """
    
    def __init__(
        self, 
        video_repository,
        cache_enabled: bool = True,
        max_cache_age_days: int = 30
    ):
        """Initialize cache service.
        
        Args:
            video_repository: Repository for cache metadata
            cache_enabled: Enable/disable caching
            max_cache_age_days: Days before cache entries expire
        """
        self.video_repo = video_repository
        self.cache_enabled = cache_enabled
        self.max_cache_age_days = max_cache_age_days
        
        # Note: Repository initialization should be done externally
        # before using the cache service
    
    async def get_cached_file(
        self, 
        video_id: str, 
        quality: str
    ) -> Optional[Tuple[str, str, str, str]]:
        """Get cached file information if available.
        
        Args:
            video_id: YouTube video ID
            quality: Requested quality
            
        Returns:
            Tuple of (file_id, title, channel_username, channel_url) or None
        """
        if not self.cache_enabled:
            return None
        
        try:
            cached = await self.video_repo.get_cached(video_id, quality)
            
            if cached:
                file_id, title, username, url = cached
                logger.info(f"Cache HIT: {video_id} ({quality})")
                return cached
            else:
                logger.debug(f"Cache MISS: {video_id} ({quality})")
                return None
                
        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            return None
    
    async def save_to_cache(
        self,
        video_id: str,
        quality: str,
        file_id: str,
        file_size: int,
        title: str = None,
        channel_username: str = None,
        channel_url: str = None
    ) -> bool:
        """Save downloaded file to cache.
        
        Args:
            video_id: YouTube video ID
            quality: Download quality
            file_id: Telegram file ID
            file_size: File size in bytes
            title: Video title
            channel_username: Channel username
            channel_url: Channel URL
            
        Returns:
            True if saved successfully
        """
        if not self.cache_enabled:
            return False
        
        try:
            await self.video_repo.save(
                video_id=video_id,
                quality=quality,
                file_id=file_id,
                file_size=file_size,
                title=title,
                channel_username=channel_username,
                channel_url=channel_url
            )
            
            logger.info(f"Cached: {video_id} ({quality}) - {file_size} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save to cache: {e}")
            return False
    
    async def is_cached(self, video_id: str, quality: str = None) -> bool:
        """Check if video is cached.
        
        Args:
            video_id: YouTube video ID
            quality: Specific quality to check (optional)
            
        Returns:
            True if cached
        """
        if not self.cache_enabled:
            return False
        
        return await self.video_repo.is_cached(video_id, quality)
    
    async def get_cached_qualities(self, video_id: str) -> List[str]:
        """Get list of cached qualities for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of quality strings
        """
        if not self.cache_enabled:
            return []
        
        return await self.video_repo.get_cached_qualities(video_id)
    
    async def invalidate_cache(
        self, 
        video_id: str = None, 
        quality: str = None,
        file_id: str = None
    ) -> int:
        """Invalidate cache entries.
        
        Args:
            video_id: Invalidate specific video (optional)
            quality: Invalidate specific quality (optional)
            file_id: Invalidate specific file (optional)
            
        Returns:
            Number of entries invalidated
        """
        deleted_count = 0
        
        try:
            if file_id:
                deleted_count = await self.video_repo.delete_cached(file_id)
            elif video_id and quality:
                deleted_count = await self.video_repo.delete_cached(f"{video_id}_{quality}")
            elif video_id:
                deleted_count = await self.video_repo.delete_by_video_id(video_id)
            
            if deleted_count > 0:
                logger.info(f"Invalidated {deleted_count} cache entries")
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
        
        return deleted_count
    
    async def cleanup_old_cache(self, days: int = None) -> int:
        """Clean up old cache entries.
        
        Args:
            days: Override default max age (optional)
            
        Returns:
            Number of entries deleted
        """
        if not self.cache_enabled:
            return 0
        
        cleanup_days = days or self.max_cache_age_days
        
        try:
            deleted = await self.video_repo.delete_old(cleanup_days)
            logger.info(f"Cleaned up {deleted} cache entries older than {cleanup_days} days")
            return deleted
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
    
    async def get_cache_statistics(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        if not self.cache_enabled:
            return {
                'enabled': False,
                'total_files': 0,
                'unique_videos': 0,
                'total_size_mb': 0
            }
        
        try:
            stats = await self.video_repo.get_cache_stats()
            stats['enabled'] = True
            stats['max_age_days'] = self.max_cache_age_days
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'enabled': False}
    
    def should_use_cache(self) -> bool:
        """Check if caching should be used.
        
        Returns:
            True if caching is enabled
        """
        return self.cache_enabled
    
    def enable_cache(self):
        """Enable caching."""
        self.cache_enabled = True
        logger.info("Cache enabled")
    
    def disable_cache(self):
        """Disable caching."""
        self.cache_enabled = False
        logger.info("Cache disabled")
