"""
User Repository

Repository for user-related database operations with full CRUD support.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user data access and management.
    
    Handles all database operations related to users including:
    - User creation and updates
    - Language preferences
    - Download tracking
    - Activity monitoring
    """
    
    def __init__(self, db_path: str = 'users.db'):
        """Initialize user repository.
        
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
        """Create necessary tables if they don't exist."""
        # Create users table
        await self.create_table(
            'users',
            {
                'user_id': 'INTEGER',
                'username': 'TEXT',
                'last_video_url': 'TEXT',
                'last_online': 'TEXT',
                'awaiting_link': 'INTEGER DEFAULT 0',
                'downloads_in_hour': 'INTEGER DEFAULT 0',
                'last_download_time': 'TEXT'
            },
            primary_key='user_id'
        )
        
        # Create user_languages table
        await self.create_table(
            'user_languages',
            {
                'user_id': 'INTEGER',
                'language_code': 'TEXT'
            },
            primary_key='user_id'
        )
    
    async def _ensure_initialized(self):
        """Ensure repository is initialized."""
        if not self._tables_created:
            await self.initialize()
    
    async def create_or_update(self, user_id: int, username: str, 
                              video_url: str = None, awaiting_link: bool = False) -> int:
        """Create new user or update existing user.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            video_url: Last processed video URL (optional)
            awaiting_link: Whether user is waiting to send link
            
        Returns:
            Number of affected rows
        """
        await self._ensure_initialized()
        last_online = datetime.now().isoformat()
        
        query = """
            INSERT INTO users (user_id, username, last_video_url, last_online, awaiting_link)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            last_video_url = excluded.last_video_url,
            last_online = excluded.last_online,
            awaiting_link = excluded.awaiting_link
        """
        
        return await self.execute(query, (
            user_id, 
            username, 
            video_url, 
            last_online, 
            1 if awaiting_link else 0
        ))
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User data dictionary or None
        """
        return await self.fetch_one(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users.
        
        Returns:
            List of all user dictionaries
        """
        return await self.fetch_all('SELECT * FROM users ORDER BY last_online DESC')
    
    async def delete_user(self, user_id: int) -> int:
        """Delete a user.
        
        Args:
            user_id: Telegram user ID to delete
            
        Returns:
            Number of deleted rows
        """
        return await self.delete(
            'DELETE FROM users WHERE user_id = ?',
            (user_id,)
        )
    
    async def update_language(self, user_id: int, language_code: str) -> int:
        """Update or insert user's language preference.
        
        Args:
            user_id: Telegram user ID
            language_code: Language code (e.g., 'en', 'ru')
            
        Returns:
            Number of affected rows
        """
        query = """
            INSERT OR REPLACE INTO user_languages (user_id, language_code)
            VALUES (?, ?)
        """
        return await self.execute(query, (user_id, language_code))
    
    async def get_language(self, user_id: int) -> Optional[str]:
        """Get user's language preference.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Language code or None
        """
        result = await self.fetch_one(
            'SELECT language_code FROM user_languages WHERE user_id = ?',
            (user_id,)
        )
        return result['language_code'] if result else None
    
    async def increment_downloads(self, user_id: int) -> int:
        """Increment user's download counter with hourly reset.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            New download count
        """
        now = datetime.now()
        
        # Get current state
        user = await self.get_user(user_id)
        if not user:
            # User doesn't exist, create record
            await self.create_or_update(user_id, 'unknown')
            user = await self.get_user(user_id)
        
        downloads = user.get('downloads_in_hour') or 0
        last_time_str = user.get('last_download_time')
        
        # Reset if hour has passed
        if last_time_str:
            last_time = datetime.fromisoformat(last_time_str)
            if (now - last_time).total_seconds() > 3600:
                downloads = 0
        
        downloads += 1
        
        # Update counter
        await self.execute(
            'UPDATE users SET downloads_in_hour = ?, last_download_time = ? WHERE user_id = ?',
            (downloads, now.isoformat(), user_id)
        )
        
        return downloads
    
    async def get_downloads_count(self, user_id: int) -> int:
        """Get current download count for user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Download count (resets every hour)
        """
        user = await self.get_user(user_id)
        if not user:
            return 0
        
        downloads = user.get('downloads_in_hour') or 0
        last_time_str = user.get('last_download_time')
        
        # Check if counter should be reset
        if last_time_str:
            last_time = datetime.fromisoformat(last_time_str)
            if (datetime.now() - last_time).total_seconds() > 3600:
                return 0
        
        return downloads
    
    async def can_download(self, user_id: int, limit_per_hour: int) -> bool:
        """Check if user can download based on rate limit.
        
        Args:
            user_id: Telegram user ID
            limit_per_hour: Maximum downloads allowed per hour
            
        Returns:
            True if user can download, False otherwise
        """
        count = await self.get_downloads_count(user_id)
        return count < limit_per_hour
    
    async def update_activity(self, user_id: int, username: str = None, 
                             video_url: str = None) -> int:
        """Update user's last online time and activity.
        
        Args:
            user_id: Telegram user ID
            username: Current username (optional)
            video_url: Last video URL (optional)
            
        Returns:
            Number of affected rows
        """
        last_online = datetime.now().isoformat()
        
        # Build dynamic update based on provided fields
        updates = ['last_online = ?']
        params = [last_online]
        
        if username:
            updates.append('username = ?')
            params.append(username)
        
        if video_url:
            updates.append('last_video_url = ?')
            params.append(video_url)
        
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        return await self.execute(query, tuple(params))
    
    async def set_awaiting_link(self, user_id: int, awaiting: bool = True) -> int:
        """Set whether user is awaiting link input.
        
        Args:
            user_id: Telegram user ID
            awaiting: True if awaiting link, False otherwise
            
        Returns:
            Number of affected rows
        """
        return await self.execute(
            'UPDATE users SET awaiting_link = ? WHERE user_id = ?',
            (1 if awaiting else 0, user_id)
        )
    
    async def is_awaiting_link(self, user_id: int) -> bool:
        """Check if user is awaiting link input.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if awaiting link, False otherwise
        """
        result = await self.fetch_val(
            'SELECT awaiting_link FROM users WHERE user_id = ?',
            (user_id,),
            'awaiting_link'
        )
        return bool(result)
    
    async def get_active_users(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get users who were active in the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of active user dictionaries
        """
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        return await self.fetch_all(
            'SELECT * FROM users WHERE last_online > ? ORDER BY last_online DESC',
            (cutoff,)
        )
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Get overall user statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_query = 'SELECT COUNT(*) as total FROM users'
        active_query = """
            SELECT COUNT(*) as active FROM users 
            WHERE datetime(last_online) > datetime('now', '-24 hours')
        """
        
        total = await self.fetch_val(total_query) or 0
        active = await self.fetch_val(active_query) or 0
        
        return {
            'total_users': total,
            'active_users_24h': active
        }
