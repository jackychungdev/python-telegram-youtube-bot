"""
Database Module

Centralized database connection management and migrations.
"""
import aiosqlite
from typing import Optional, Dict
from pathlib import Path


class Database:
    """Centralized database connection manager.
    
    Provides singleton database connections with support for:
    - Connection pooling
    - Transaction management
    - Schema migrations
    - Multiple database files
    """
    
    _instances: Dict[str, 'Database'] = {}
    
    def __new__(cls, db_path: str = None):
        """Singleton pattern to ensure one instance per database.
        
        Args:
            db_path: Path to database file (optional)
            
        Returns:
            Database instance for the specified path
        """
        if db_path is None:
            db_path = 'users.db'
        
        db_path_str = str(Path(db_path).resolve())
        
        if db_path_str not in cls._instances:
            instance = super().__new__(cls)
            instance.db_path = db_path_str
            instance._connection: Optional[aiosqlite.Connection] = None
            instance._initialized = False
            cls._instances[db_path_str] = instance
        
        return cls._instances[db_path_str]
    
    def __init__(self, db_path: str = None):
        """Initialize database connection.
        
        Note: Initialization happens in __new__ to maintain singleton.
        """
        pass  # Already initialized in __new__
    
    async def connect(self) -> aiosqlite.Connection:
        """Get or create database connection.
        
        Returns:
            Active aiosqlite connection
        """
        if self._connection is None or self._connection.closed:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute('PRAGMA foreign_keys = ON')
        
        return self._connection
    
    async def disconnect(self):
        """Close database connection."""
        if self._connection and not self._connection.closed:
            await self._connection.close()
            self._connection = None
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Get current connection or create new one.
        
        Returns:
            Active aiosqlite connection
        """
        return await self.connect()
    
    async def execute(self, query: str, parameters: tuple = None):
        """Execute a query on the database.
        
        Args:
            query: SQL query string
            parameters: Query parameters (optional)
            
        Returns:
            Cursor with results
        """
        conn = await self.connect()
        if parameters:
            return await conn.execute(query, parameters)
        else:
            return await conn.execute(query)
    
    async def commit(self):
        """Commit current transaction."""
        conn = await self.connect()
        await conn.commit()
    
    async def rollback(self):
        """Rollback current transaction."""
        conn = await self.connect()
        await conn.rollback()
    
    async def close_all(self):
        """Close all database connections."""
        for db in self._instances.values():
            await db.disconnect()
        self._instances.clear()
    
    async def backup(self, backup_path: str):
        """Create a backup of the database.
        
        Args:
            backup_path: Path for backup file
        """
        import shutil
        shutil.copy2(self.db_path, backup_path)
    
    async def vacuum(self):
        """Vacuum database to optimize size."""
        await self.execute('VACUUM')
    
    async def get_size(self) -> int:
        """Get database file size in bytes.
        
        Returns:
            File size in bytes
        """
        return Path(self.db_path).stat().st_size
    
    async def get_size_mb(self) -> float:
        """Get database file size in megabytes.
        
        Returns:
            File size in MB
        """
        return round(self.get_size() / (1024 * 1024), 2)


# Convenience functions for simple usage
async def get_database(db_path: str = None) -> Database:
    """Get database instance.
    
    Args:
        db_path: Path to database file (optional)
        
    Returns:
        Database instance
    """
    return Database(db_path)


async def execute_query(query: str, parameters: tuple = None, db_path: str = None):
    """Execute a query on default database.
    
    Args:
        query: SQL query
        parameters: Query parameters
        db_path: Database path (optional)
        
    Returns:
        Cursor with results
    """
    db = await get_database(db_path)
    return await db.execute(query, parameters)


async def fetch_one(query: str, parameters: tuple = None, db_path: str = None):
    """Fetch one row from database.
    
    Args:
        query: SELECT query
        parameters: Query parameters
        db_path: Database path (optional)
        
    Returns:
        Row dictionary or None
    """
    db = await get_database(db_path)
    cursor = await db.execute(query, parameters or ())
    row = await cursor.fetchone()
    return dict(row) if row else None


async def fetch_all(query: str, parameters: tuple = None, db_path: str = None):
    """Fetch all rows from database.
    
    Args:
        query: SELECT query
        parameters: Query parameters
        db_path: Database path (optional)
        
    Returns:
        List of row dictionaries
    """
    db = await get_database(db_path)
    cursor = await db.execute(query, parameters or ())
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
