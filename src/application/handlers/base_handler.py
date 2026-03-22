"""
Base Handler

Abstract base handler providing common functionality for all handlers.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Abstract base handler for Telegram bot commands and callbacks.
    
    Provides common functionality:
    - Authorization checks
    - Error handling
    - Logging
    - User context management
    - Response helpers
    
    Attributes:
        application: Telegram application instance
        services: Dictionary of service instances
    """
    
    def __init__(self, application, services: Dict[str, Any]):
        """Initialize base handler.
        
        Args:
            application: Telegram application instance
            services: Dictionary with keys:
                - youtube_service: YoutubeService
                - download_service: DownloadService
                - cache_service: CacheService
                - telegram_service: TelegramService
                - queue_service: QueueService
                - user_repo: UserRepository
                - auth_repo: AuthorizationRepository
        """
        self.application = application
        self.services = services
        
        # Extract services for easy access
        self.youtube_service = services.get('youtube_service')
        self.download_service = services.get('download_service')
        self.cache_service = services.get('cache_service')
        self.telegram_service = services.get('telegram_service')
        self.queue_service = services.get('queue_service')
        self.user_repo = services.get('user_repo')
        self.auth_repo = services.get('auth_repo')
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    async def check_authorization(self, user_id: int) -> bool:
        """Check if user is authorized.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if authorized, False otherwise
        """
        try:
            # Check if authorization is required
            if not self.auth_repo:
                return True
            
            is_authorized = await self.auth_repo.is_authorized(user_id)
            
            if not is_authorized:
                logger.warning(f"Unauthorized access attempt by user {user_id}")
            
            return is_authorized
            
        except Exception as e:
            logger.error(f"Authorization check failed: {e}")
            return False
    
    async def get_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user context from database.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User context dictionary or None
        """
        try:
            if not self.user_repo:
                return None
            
            user_data = await self.user_repo.get_user(user_id)
            
            if user_data:
                # Get language preference
                language = await self.user_repo.get_language(user_id)
                user_data['language'] = language or 'en'
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return None
    
    async def send_error_message(self, chat_id: int, error: str):
        """Send error message to user.
        
        Args:
            chat_id: Chat ID
            error: Error message
        """
        try:
            if self.telegram_service:
                await self.telegram_service.notify_user(
                    user_id=chat_id,
                    message=f"Error: {error}",
                    notification_type='error'
                )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    async def send_success_message(self, chat_id: int, message: str):
        """Send success message to user.
        
        Args:
            chat_id: Chat ID
            message: Success message
        """
        try:
            if self.telegram_service:
                await self.telegram_service.notify_user(
                    user_id=chat_id,
                    message=message,
                    notification_type='success'
                )
        except Exception as e:
            logger.error(f"Failed to send success message: {e}")
    
    async def log_user_action(self, user_id: int, action: str, details: str = None):
        """Log user action for analytics.
        
        Args:
            user_id: Telegram user ID
            action: Action name
            details: Additional details (optional)
        """
        try:
            logger.info(f"User {user_id} performed action: {action}" + 
                       (f" - {details}" if details else ""))
            
            # Update user activity
            if self.user_repo:
                await self.user_repo.update_activity(user_id)
                
        except Exception as e:
            logger.error(f"Failed to log user action: {e}")
    
    def handle_exception(self, context: ContextTypes.DEFAULT_TYPE, error: Exception):
        """Handle exception in handler.
        
        Args:
            context: Telegram context
            error: Exception that occurred
        """
        logger.error(f"Exception in handler: {error}", exc_info=True)
        
        # Notify user if possible
        if context and context.chat_id:
            asyncio.create_task(
                self.send_error_message(context.chat_id, str(error))
            )
    
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle update - must be implemented by subclass.
        
        Args:
            update: Telegram update
            context: Telegram context
            
        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError("Subclasses must implement handle()")
