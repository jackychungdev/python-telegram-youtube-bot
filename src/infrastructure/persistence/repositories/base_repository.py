"""
Base Repository

Abstract base repository providing common CRUD operations and database access.
"""
import aiosqlite
from typing import Optional, List, Any, Dict
from abc import ABC, abstractmethod


class BaseRepository(ABC):
    """Abstract base repository for database operations.
    
    Provides common database operations with support for transactions
    and connection management.
    
    Attributes:
        db_path: Path to SQLite database file
    """
    
    def __init__(self, db_path: str):
        """Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
    
    async def execute(self, query: str, parameters: tuple = None) -> int:
        """Execute a query without returning results.
        
        Args:
            query: SQL query string
            parameters: Query parameters (optional)
            
        Returns:
            Number of affected rows
        """
        async with aiosqlite.connect(self.db_path) as conn:
            if parameters:
                cursor = await conn.execute(query, parameters)
            else:
                cursor = await conn.execute(query)
            await conn.commit()
            return cursor.rowcount
    
    async def executemany(self, query: str, parameters_list: List[tuple]) -> int:
        """Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            parameters_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.executemany(query, parameters_list)
            await conn.commit()
            return cursor.rowcount
    
    async def fetch_one(self, query: str, parameters: tuple = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row as dictionary.
        
        Args:
            query: SQL query string
            parameters: Query parameters (optional)
            
        Returns:
            Dictionary with column values or None if not found
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, parameters or ()) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def fetch_all(self, query: str, parameters: tuple = None) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries.
        
        Args:
            query: SQL query string
            parameters: Query parameters (optional)
            
        Returns:
            List of dictionaries with column values
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, parameters or ()) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def fetch_val(self, query: str, parameters: tuple = None, column: str = None) -> Optional[Any]:
        """Fetch a single value from first row.
        
        Args:
            query: SQL query string
            parameters: Query parameters (optional)
            column: Column name or index to return (default: first column)
            
        Returns:
            Single value or None
        """
        result = await self.fetch_one(query, parameters)
        if result:
            if column:
                return result.get(column)
            # Return first value
            return next(iter(result.values()))
        return None
    
    async def exists(self, query: str, parameters: tuple = None) -> bool:
        """Check if query returns any rows.
        
        Args:
            query: SQL query string
            parameters: Query parameters (optional)
            
        Returns:
            True if at least one row exists, False otherwise
        """
        result = await self.fetch_one(query, parameters)
        return result is not None
    
    async def count(self, query: str, parameters: tuple = None) -> int:
        """Count rows matching query.
        
        Args:
            query: SQL query string (should be SELECT ...)
            parameters: Query parameters (optional)
            
        Returns:
            Number of matching rows
        """
        count_query = f"SELECT COUNT(*) as cnt FROM ({query})"
        result = await self.fetch_one(count_query, parameters)
        return result['cnt'] if result else 0
    
    async def insert(self, query: str, parameters: tuple = None) -> int:
        """Insert a row and return the last inserted row ID.
        
        Args:
            query: INSERT SQL query
            parameters: Query parameters
            
        Returns:
            Last inserted row ID
        """
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(query, parameters or ())
            await conn.commit()
            return cursor.lastrowid
    
    async def update(self, query: str, parameters: tuple = None) -> int:
        """Update rows and return number of affected rows.
        
        Args:
            query: UPDATE SQL query
            parameters: Query parameters
            
        Returns:
            Number of updated rows
        """
        return await self.execute(query, parameters)
    
    async def delete(self, query: str, parameters: tuple = None) -> int:
        """Delete rows and return number of affected rows.
        
        Args:
            query: DELETE SQL query
            parameters: Query parameters
            
        Returns:
            Number of deleted rows
        """
        return await self.execute(query, parameters)
    
    async def create_table(self, table_name: str, columns: Dict[str, str], 
                          primary_key: str = None, if_not_exists: bool = True):
        """Create a table with specified columns.
        
        Args:
            table_name: Name of table to create
            columns: Dictionary of column names and types
            primary_key: Primary key column name (optional)
            if_not_exists: Whether to use IF NOT EXISTS clause
        """
        column_defs = [f"{name} {type_}" for name, type_ in columns.items()]
        
        if primary_key:
            column_defs.append(f"PRIMARY KEY ({primary_key})")
        
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        query = f"CREATE TABLE {exists_clause}{table_name} ({', '.join(column_defs)})"
        
        await self.execute(query)
    
    async def drop_table(self, table_name: str, if_exists: bool = True):
        """Drop a table.
        
        Args:
            table_name: Name of table to drop
            if_exists: Whether to use IF EXISTS clause
        """
        exists_clause = "IF EXISTS " if if_exists else ""
        query = f"DROP TABLE {exists_clause}{table_name}"
        await self.execute(query)
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.
        
        Args:
            table_name: Name of table to check
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        return await self.exists(query, (table_name,))
    
    async def get_table_columns(self, table_name: str) -> List[str]:
        """Get list of column names for a table.
        
        Args:
            table_name: Name of table
            
        Returns:
            List of column names
        """
        query = f"PRAGMA table_info({table_name})"
        rows = await self.fetch_all(query)
        return [row['name'] for row in rows]
    
    async def add_column(self, table_name: str, column_name: str, 
                        column_type: str, if_not_exists: bool = True):
        """Add a column to an existing table.
        
        Args:
            table_name: Name of table
            column_name: Name of new column
            column_type: SQL type for new column
            if_not_exists: Whether to check if column already exists
        """
        if if_not_exists:
            columns = await self.get_table_columns(table_name)
            if column_name in columns:
                return
        
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        await self.execute(query)
