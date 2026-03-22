"""
Core module initialization

Exports all core components for easy importing.
"""
from .config import Config
from .exceptions import (
    BotException, 
    DownloadError, 
    AuthorizationError,
    ValidationError,
    CacheError,
    ConfigurationError,
    RepositoryError
)
from .logging_config import setup_logging
from .container import Container, Scope, get_container, set_container, register, resolve

__all__ = [
    # Configuration
    'Config',
    
    # Exceptions
    'BotException',
    'DownloadError',
    'AuthorizationError',
    'ValidationError',
    'CacheError',
    'ConfigurationError',
    'RepositoryError',
    
    # Logging
    'setup_logging',
    
    # Dependency Injection
    'Container',
    'Scope',
    'get_container',
    'set_container',
    'register',
    'resolve',
]
