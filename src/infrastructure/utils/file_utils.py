"""
File Utils Utility

File operations helpers for safe file handling and management.
"""
import os
import shutil
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging


logger = logging.getLogger(__name__)


class FileUtils:
    """Utility for file operations.
    
    Provides safe file handling with async support:
    - File size formatting
    - Safe file deletion
    - Directory management
    - File type detection
    - Temporary file handling
    
    Attributes:
        temp_dir: Directory for temporary files
    """
    
    SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']
    
    def __init__(self, temp_dir: str = 'temp'):
        """Initialize file utilities.
        
        Args:
            temp_dir: Base directory for temporary files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g., "15.3 MB")
        """
        if size_bytes == 0:
            return "0 B"
        
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(FileUtils.SIZE_UNITS) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {FileUtils.SIZE_UNITS[unit_index]}"
    
    @staticmethod
    def parse_size(size_str: str) -> int:
        """Parse size string back to bytes.
        
        Args:
            size_str: Size string (e.g., "15.3 MB")
            
        Returns:
            Size in bytes
        """
        parts = size_str.strip().split()
        if len(parts) != 2:
            raise ValueError(f"Invalid size format: {size_str}")
        
        value = float(parts[0])
        unit = parts[1].upper()
        
        try:
            unit_index = FileUtils.SIZE_UNITS.index(unit)
        except ValueError:
            raise ValueError(f"Unknown unit: {unit}")
        
        return int(value * (1024 ** unit_index))
    
    async def safe_delete(self, file_path: Path) -> bool:
        """Safely delete a file with error handling.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.debug(f"File does not exist: {file_path}")
                return False
            
            # Run in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: path.unlink()
            )
            
            logger.debug(f"Deleted file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    async def safe_move(self, src: Path, dst: Path) -> bool:
        """Safely move a file with error handling.
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Returns:
            True if moved successfully
        """
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            if not src_path.exists():
                logger.error(f"Source file does not exist: {src}")
                return False
            
            # Create destination directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: src_path.rename(dst_path)
            )
            
            logger.debug(f"Moved file from {src} to {dst}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return False
    
    async def copy_file(self, src: Path, dst: Path) -> bool:
        """Copy a file to destination.
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Returns:
            True if copied successfully
        """
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            if not src_path.exists():
                logger.error(f"Source file does not exist: {src}")
                return False
            
            # Create destination directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: shutil.copy2(src_path, dst_path)
            )
            
            logger.debug(f"Copied file from {src} to {dst}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return False
    
    def get_file_type(self, file_path: Path) -> str:
        """Get file type based on extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            File type ('video', 'audio', 'image', 'document', 'unknown')
        """
        ext = Path(file_path).suffix.lower()
        
        video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.flv'}
        audio_exts = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        document_exts = {'.pdf', '.doc', '.docx', '.txt', '.rtf'}
        
        if ext in video_exts:
            return 'video'
        elif ext in audio_exts:
            return 'audio'
        elif ext in image_exts:
            return 'image'
        elif ext in document_exts:
            return 'document'
        else:
            return 'unknown'
    
    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a video.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if video file
        """
        return self.get_file_type(file_path) == 'video'
    
    def is_audio_file(self, file_path: Path) -> bool:
        """Check if file is an audio file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if audio file
        """
        return self.get_file_type(file_path) == 'audio'
    
    async def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes or 0 if not found
        """
        try:
            path = Path(file_path)
            if path.exists():
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: path.stat().st_size
                )
            return 0
        except Exception as e:
            logger.error(f"Failed to get file size: {e}")
            return 0
    
    async def create_temp_file(self, prefix: str = 'temp_', suffix: str = '') -> Path:
        """Create a temporary file.
        
        Args:
            prefix: Filename prefix
            suffix: Filename suffix
            
        Returns:
            Path to created temporary file
        """
        import tempfile
        
        loop = asyncio.get_event_loop()
        
        fd, path = await loop.run_in_executor(
            None,
            lambda: tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=self.temp_dir)
        )
        
        # Close the file descriptor
        os.close(fd)
        
        return Path(path)
    
    def cleanup_temp_files(self, max_age_hours: int = 1) -> int:
        """Clean up old temporary files.
        
        Args:
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Number of files deleted
        """
        import time
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        for file_path in self.temp_dir.iterdir():
            if file_path.is_file():
                try:
                    file_age = now - file_path.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Cleaned up temp file: {file_path}")
                        
                except Exception as e:
                    logger.error(f"Failed to cleanup temp file: {e}")
        
        logger.info(f"Cleaned up {deleted_count} temporary files")
        return deleted_count
    
    def ensure_directory(self, dir_path: Path) -> bool:
        """Ensure directory exists, create if necessary.
        
        Args:
            dir_path: Directory path
            
        Returns:
            True if directory exists or was created
        """
        try:
            path = Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            return False
    
    def list_files(
        self, 
        directory: Path, 
        pattern: str = '*', 
        recursive: bool = False
    ) -> List[Path]:
        """List files in directory matching pattern.
        
        Args:
            directory: Directory to search
            pattern: Glob pattern (e.g., '*.mp4')
            recursive: Search recursively
            
        Returns:
            List of matching file paths
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return []
        
        if recursive:
            return list(dir_path.rglob(pattern))
        else:
            return list(dir_path.glob(pattern))
    
    def get_storage_info(self, path: Path = None) -> Dict[str, Any]:
        """Get storage information for a path.
        
        Args:
            path: Path to check (uses root if None)
            
        Returns:
            Dictionary with total, used, free space in bytes
        """
        import shutil
        
        check_path = Path(path) if path else Path('/')
        
        try:
            usage = shutil.disk_usage(check_path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent_used': round((usage.used / usage.total) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'percent_used': 0
            }
