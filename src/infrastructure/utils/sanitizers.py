"""
Sanitizers Utility

Filename and text sanitization for safe file operations.
"""
import re
import unicodedata
from typing import Optional
from pathlib import Path


class Sanitizer:
    """Utility for sanitizing filenames and text.
    
    Provides safe string cleaning for:
    - File names (remove invalid characters)
    - Paths (prevent directory traversal)
    - Text (remove dangerous characters)
    - URLs (safe extraction)
    
    Attributes:
        max_filename_length: Maximum filename length
        replacement_char: Character to replace invalid chars
    """
    
    # Invalid characters for different platforms
    WINDOWS_INVALID = '<>:"/\\|？*'
    MAC_INVALID = ':'
    LINUX_INVALID = '/'
    
    # Combined invalid chars
    ALL_INVALID = WINDOWS_INVALID + MAC_INVALID + LINUX_INVALID
    
    # Control characters
    CONTROL_CHARS = ''.join(map(chr, range(0, 32))) + chr(127)
    
    def __init__(
        self, 
        max_filename_length: int = 255,
        replacement_char: str = '_'
    ):
        """Initialize sanitizer.
        
        Args:
            max_filename_length: Maximum filename length
            replacement_char: Character to replace invalid chars
        """
        self.max_filename_length = max_filename_length
        self.replacement_char = replacement_char
    
    def sanitize_filename(self, filename: str, allow_unicode: bool = False) -> str:
        """Sanitize filename for safe file operations.
        
        Args:
            filename: Original filename
            allow_unicode: Allow Unicode characters
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return self.replacement_char
        
        # Clean up
        filename = str(filename).strip()
        
        # Remove control characters
        filename = ''.join(c for c in filename if c not in self.CONTROL_CHARS)
        
        # Normalize Unicode if not allowed
        if not allow_unicode:
            filename = unicodedata.normalize('NFKD', filename)
            filename = filename.encode('ascii', 'ignore').decode('ascii')
        
        # Remove invalid characters
        for char in self.ALL_INVALID:
            filename = filename.replace(char, self.replacement_char)
        
        # Replace multiple consecutive separators with single
        filename = re.sub(r'[\s_]+', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Handle special names
        if filename in ('.', '..'):
            filename = self.replacement_char
        
        # Truncate to max length
        if len(filename) > self.max_filename_length:
            # Preserve extension
            name, ext = Path(filename).stem, Path(filename).suffix
            max_name_length = self.max_filename_length - len(ext)
            filename = name[:max_name_length] + ext
        
        # Ensure not empty
        if not filename:
            filename = self.replacement_char
        
        return filename
    
    def sanitize_path(self, path: str) -> str:
        """Sanitize path to prevent directory traversal.
        
        Args:
            path: Original path
            
        Returns:
            Sanitized path without .. components
        """
        if not path:
            return ''
        
        # Convert to Path object
        path_obj = Path(path)
        
        # Get parts
        parts = path_obj.parts
        
        # Filter out dangerous components
        safe_parts = []
        for part in parts:
            # Skip parent directory references
            if part in ('..', '.'):
                continue
            
            # Sanitize each component
            safe_part = self.sanitize_filename(part)
            safe_parts.append(safe_part)
        
        # Reconstruct path
        if path_obj.is_absolute():
            return str(Path(path_obj.root) / Path(*safe_parts))
        else:
            return str(Path(*safe_parts))
    
    def sanitize_text(self, text: str, max_length: int = None) -> str:
        """Sanitize general text.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length (optional)
            
        Returns:
            Sanitized text
        """
        if not text:
            return ''
        
        # Convert to string
        text = str(text)
        
        # Remove control characters except newlines and tabs
        text = ''.join(
            c for c in text 
            if c not in self.CONTROL_CHARS or c in '\n\r\t'
        )
        
        # Remove zero-width characters
        text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '...'
        
        return text.strip()
    
    def make_safe_filename(
        self, 
        title: str, 
        quality: str = '',
        extension: str = 'mp4'
    ) -> str:
        """Create a safe filename from title and metadata.
        
        Args:
            title: Video/content title
            quality: Quality label (e.g., '720p')
            extension: File extension
            
        Returns:
            Safe filename
        """
        # Sanitize title
        safe_title = self.sanitize_filename(title)
        
        # Build filename
        parts = [safe_title]
        
        if quality:
            safe_quality = self.sanitize_filename(quality)
            parts.append(safe_quality)
        
        # Add extension
        if extension and not extension.startswith('.'):
            extension = '.' + extension
        
        filename = '_'.join(parts) + extension
        
        # Final sanitization
        return self.sanitize_filename(filename)
    
    def remove_duplicate_spaces(self, text: str) -> str:
        """Remove duplicate spaces from text.
        
        Args:
            text: Input text
            
        Returns:
            Text with single spaces
        """
        return ' '.join(text.split())
    
    def truncate_words(self, text: str, max_words: int) -> str:
        """Truncate text to maximum number of words.
        
        Args:
            text: Input text
            max_words: Maximum words
            
        Returns:
            Truncated text
        """
        words = text.split()
        
        if len(words) <= max_words:
            return text
        
        return ' '.join(words[:max_words]) + '...'
    
    def slugify(self, text: str, separator: str = '-') -> str:
        """Convert text to URL-friendly slug.
        
        Args:
            text: Input text
            separator: Word separator
            
        Returns:
            Slugified text
        """
        # Lowercase
        text = text.lower()
        
        # Replace spaces and underscores with separator
        text = re.sub(r'[\s_]+', separator, text)
        
        # Remove non-alphanumeric except separator
        text = re.sub(r'[^a-z0-9' + re.escape(separator) + ']', '', text)
        
        # Remove consecutive separators
        text = re.sub(rf'{re.escape(separator)}+', separator, text)
        
        # Strip separators from ends
        return text.strip(separator)
    
    def is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe.
        
        Args:
            filename: Filename to check
            
        Returns:
            True if filename is safe
        """
        sanitized = self.sanitize_filename(filename)
        return sanitized == filename
    
    def escape_glob(self, pattern: str) -> str:
        """Escape special glob characters.
        
        Args:
            pattern: Pattern with potential glob chars
            
        Returns:
            Escaped pattern
        """
        # Escape special glob characters
        special_chars = ['*', '?', '[', ']', '{', '}']
        
        for char in special_chars:
            pattern = pattern.replace(char, f'\\{char}')
        
        return pattern
