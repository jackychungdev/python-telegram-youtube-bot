"""
Authorization Repository

Repository for user authorization management.
"""
from typing import List, Dict, Any
from .base_repository import BaseRepository
from ..database import Database


class AuthorizationRepository(BaseRepository):
    """Repository for authorized users management.
    
    Handles whitelist-based authorization system for bot access control.
    """
    
    def __init__(self, db: Database):
        """Initialize authorization repository.
        
        Args:
            db: Database instance for connection management
        """
        super().__init__(db.db_path)
        self.db = db
        self._tables_created = False
    
    async def initialize(self):
        """Initialize repository by creating tables if needed."""
        if not self._tables_created:
            await self._create_tables()
            self._tables_created = True
    
    async def _create_tables(self):
        """Create authorized_users table if it doesn't exist."""
        await self.create_table(
            'authorized_users',
            {
                'user_id': 'INTEGER',
                'added_date': 'TEXT',
                'added_by': 'TEXT'
            },
            primary_key='user_id'
        )
    
    async def add_user(self, user_id: int, added_by: str = None) -> int:
        """Add user to authorized list.
        
        Args:
            user_id: Telegram user ID to authorize
            added_by: Username or identifier of who added this user
            
        Returns:
            Number of affected rows (0 if already exists, 1 if added)
        """
        from datetime import datetime
        
        query = """
            INSERT OR IGNORE INTO authorized_users (user_id, added_date, added_by)
            VALUES (?, ?, ?)
        """
        
        return await self.execute(query, (
            user_id, 
            datetime.now().isoformat(),
            added_by
        ))
    
    async def remove_user(self, user_id: int) -> int:
        """Remove user from authorized list.
        
        Args:
            user_id: Telegram user ID to remove
            
        Returns:
            Number of deleted rows
        """
        return await self.delete(
            'DELETE FROM authorized_users WHERE user_id = ?',
            (user_id,)
        )
    
    async def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if authorized, False otherwise
        """
        return await self.exists(
            'SELECT user_id FROM authorized_users WHERE user_id = ?',
            (user_id,)
        )
    
    async def get_all_authorized(self) -> List[Dict[str, Any]]:
        """Get all authorized users.
        
        Returns:
            List of authorized user dictionaries
        """
        return await self.fetch_all(
            'SELECT * FROM authorized_users ORDER BY added_date DESC'
        )
    
    async def get_authorized_count(self) -> int:
        """Get total number of authorized users.
        
        Returns:
            Number of authorized users
        """
        return await self.count('SELECT 1 FROM authorized_users')
    
    async def bulk_add_users(self, user_ids: List[int], added_by: str = None) -> int:
        """Add multiple users at once.
        
        Args:
            user_ids: List of user IDs to authorize
            added_by: Username or identifier of who added these users
            
        Returns:
            Number of users actually added (excluding duplicates)
        """
        from datetime import datetime
        
        now = datetime.now().isoformat()
        params_list = [(uid, now, added_by) for uid in user_ids]
        
        query = """
            INSERT OR IGNORE INTO authorized_users (user_id, added_date, added_by)
            VALUES (?, ?, ?)
        """
        
        return await self.executemany(query, params_list)
    
    async def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Get authorization information for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with authorization details or None
        """
        return await self.fetch_one(
            'SELECT * FROM authorized_users WHERE user_id = ?',
            (user_id,)
        )
    
    async def search_users(self, pattern: str) -> List[Dict[str, Any]]:
        """Search authorized users by pattern.
        
        Args:
            pattern: Search pattern (partial match on added_by)
            
        Returns:
            List of matching user dictionaries
        """
        return await self.fetch_all(
            '''SELECT * FROM authorized_users 
               WHERE added_by LIKE ? 
               ORDER BY added_date DESC''',
            (f'%{pattern}%',)
        )
    
    async def cleanup_invalid_users(self, valid_user_ids: List[int]) -> int:
        """Remove authorized users that are no longer in the valid list.
        
        This is useful for cleaning up when the authorized users list
        in configuration changes.
        
        Args:
            valid_user_ids: List of currently valid user IDs
            
        Returns:
            Number of removed users
        """
        if not valid_user_ids:
            # If no valid users provided, don't delete anything
            return 0
        
        placeholders = ','.join(['?' for _ in valid_user_ids])
        query = f"""
            DELETE FROM authorized_users 
            WHERE user_id NOT IN ({placeholders})
        """
        
        return await self.execute(query, tuple(valid_user_ids))
