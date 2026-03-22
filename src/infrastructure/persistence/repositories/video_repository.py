"""
Video Repository

Repository for video cache management and retrieval operations.
"""
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
from .base_repository import BaseRepository


class VideoRepository(BaseRepository):
    """Repository for video cache data access.
    
    Handles caching of uploaded videos to avoid re-uploading
    the same content multiple times.
    """
    
    def __init__(self, db_path: str = 'users.db'):
        """Initialize video repository.
        
        Args:
            db_path: Path to SQLite database file
        """
        super().__init__(db_path)
        self._tables_created = False
    
    async def initialize(self):
        """Initialize repository by creating tables if needed."""
        if not self._tables_created:
            await self._create_tables()
            self._tables_created = True
    
    async def _create_tables(self):
        """Create uploaded_videos table if it doesn't exist."""
        await self.create_table(
            'uploaded_videos',
            {
                'video_id': 'TEXT',
                'quality': 'TEXT',
                'file_id': 'TEXT',
                'upload_date': 'TEXT',
                'file_size': 'INTEGER',
                'title': 'TEXT',
                'channel_username': 'TEXT',
                'channel_url': 'TEXT'
            },
            primary_key='file_id'
        )
        
        # Create index for faster lookups
        await self.execute(
            'CREATE INDEX IF NOT EXISTS idx_video_id_quality ON uploaded_videos (video_id, quality)'
        )
    
    async def _ensure_initialized(self):
        """Ensure repository is initialized."""
        if not self._tables_created:
            await self.initialize()
    
    async def save(self, video_id: str, quality: str, file_id: str, 
                   file_size: int, title: str = None, 
                   channel_username: str = None, 
                   channel_url: str = None) -> int:
        """Save or update video file information in cache.
        
        Args:
            video_id: YouTube video ID
            quality: Download quality (e.g., '720', 'audio')
            file_id: Telegram file ID
            file_size: File size in bytes
            title: Video title
            channel_username: Channel username
            channel_url: Channel URL
            
        Returns:
            Number of affected rows
        """
        await self._ensure_initialized()
        upload_date = datetime.now().isoformat()
        
        query = """
            INSERT OR REPLACE INTO uploaded_videos 
            (video_id, quality, file_id, upload_date, file_size, title, channel_username, channel_url) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        return await self.execute(query, (
            video_id, quality, file_id, upload_date, 
            file_size, title, channel_username, channel_url
        ))
    
    async def get_cached(self, video_id: str, quality: str) -> Optional[Tuple[str, str, str, str]]:
        """Get cached file information for a specific video and quality.
        
        Args:
            video_id: YouTube video ID
            quality: Download quality
            
        Returns:
            Tuple of (file_id, title, channel_username, channel_url) or None
        """
        result = await self.fetch_one(
            '''SELECT file_id, title, channel_username, channel_url 
               FROM uploaded_videos 
               WHERE video_id = ? AND quality = ?''',
            (video_id, quality)
        )
        
        if result:
            return (
                result['file_id'],
                result['title'],
                result['channel_username'],
                result['channel_url']
            )
        return None
    
    async def get_cached_by_file_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached video information by Telegram file ID.
        
        Args:
            file_id: Telegram file ID
            
        Returns:
            Dictionary with all cached information or None
        """
        return await self.fetch_one(
            'SELECT * FROM uploaded_videos WHERE file_id = ?',
            (file_id,)
        )
    
    async def get_all_cached_videos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all cached videos with optional limit.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of cached video dictionaries
        """
        return await self.fetch_all(
            'SELECT * FROM uploaded_videos ORDER BY upload_date DESC LIMIT ?',
            (limit,)
        )
    
    async def get_cached_count(self) -> int:
        """Get total number of cached videos.
        
        Returns:
            Number of cached videos
        """
        return await self.count('SELECT 1 FROM uploaded_videos')
    
    async def delete_cached(self, file_id: str) -> int:
        """Delete a specific cached video entry.
        
        Args:
            file_id: Telegram file ID to delete
            
        Returns:
            Number of deleted rows
        """
        return await self.delete(
            'DELETE FROM uploaded_videos WHERE file_id = ?',
            (file_id,)
        )
    
    async def delete_old(self, days: int = 30) -> int:
        """Delete old cached videos.
        
        Args:
            days: Delete videos older than this many days
            
        Returns:
            Number of deleted rows
        """
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        return await self.delete(
            'DELETE FROM uploaded_videos WHERE upload_date < ?',
            (cutoff_date,)
        )
    
    async def delete_by_video_id(self, video_id: str) -> int:
        """Delete all cached versions of a specific video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Number of deleted rows
        """
        return await self.delete(
            'DELETE FROM uploaded_videos WHERE video_id = ?',
            (video_id,)
        )
    
    async def get_cached_qualities(self, video_id: str) -> List[str]:
        """Get list of cached qualities for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of quality strings
        """
        rows = await self.fetch_all(
            'SELECT quality FROM uploaded_videos WHERE video_id = ?',
            (video_id,)
        )
        return [row['quality'] for row in rows]
    
    async def is_cached(self, video_id: str, quality: str = None) -> bool:
        """Check if a video is cached (optionally for specific quality).
        
        Args:
            video_id: YouTube video ID
            quality: Specific quality to check (optional)
            
        Returns:
            True if cached, False otherwise
        """
        if quality:
            return await self.exists(
                'SELECT 1 FROM uploaded_videos WHERE video_id = ? AND quality = ?',
                (video_id, quality)
            )
        else:
            return await self.exists(
                'SELECT 1 FROM uploaded_videos WHERE video_id = ?',
                (video_id,)
            )
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_query = 'SELECT COUNT(*) as total FROM uploaded_videos'
        size_query = 'SELECT SUM(file_size) as total_size FROM uploaded_videos'
        
        total = await self.fetch_val(total_query, column='total') or 0
        total_size = await self.fetch_val(size_query, column='total_size') or 0
        
        # Get unique videos count
        unique_videos = await self.fetch_val(
            'SELECT COUNT(DISTINCT video_id) as count FROM uploaded_videos',
            column='count'
        ) or 0
        
        return {
            'total_files': total,
            'unique_videos': unique_videos,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }
    
    async def cleanup_duplicates(self) -> int:
        """Remove duplicate entries keeping only the newest.
        
        Returns:
            Number of deleted duplicate rows
        """
        # This is a complex operation, we'll use a transaction
        query = """
            DELETE FROM uploaded_videos 
            WHERE file_id IN (
                SELECT file_id FROM (
                    SELECT file_id, 
                           ROW_NUMBER() OVER (
                               PARTITION BY video_id, quality 
                               ORDER BY upload_date DESC
                           ) as rn
                    FROM uploaded_videos
                ) WHERE rn > 1
            )
        """
        return await self.execute(query)
