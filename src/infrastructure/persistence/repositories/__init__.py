"""
Repositories module

Repository implementations for data access with dependency injection support.
"""
from .base_repository import BaseRepository
from .user_repository import UserRepository
from .video_repository import VideoRepository
from .authorization_repository import AuthorizationRepository

__all__ = [
    'BaseRepository',
    'UserRepository',
    'VideoRepository',
    'AuthorizationRepository',
]
