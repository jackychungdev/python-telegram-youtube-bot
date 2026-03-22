"""
Custom exceptions for the bot

Defines exception hierarchy for different error types in the application.
"""


class BotException(Exception):
    """Base exception for all bot-related errors."""
    pass


class DownloadError(BotException):
    """Error during download operation.
    
    Raised when YouTube download fails or encounters issues.
    """
    pass


class AuthorizationError(BotException):
    """Error related to user authorization.
    
    Raised when unauthorized user attempts restricted operations.
    """
    pass


class ValidationError(BotException):
    """Error in input validation.
    
    Raised when user input is invalid or malformed.
    """
    pass


class CacheError(BotException):
    """Error related to caching operations.
    
    Raised when cache read/write operations fail.
    """
    pass


class ConfigurationError(BotException):
    """Error in configuration loading or validation."""
    pass


class RepositoryError(BotException):
    """Error in database/repository operations."""
    pass
