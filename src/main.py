"""
Main entry point for the refactored Telegram YouTube Bot

This uses the new modular architecture with layered design:
- Domain Layer (entities and value objects)
- Application Layer (services and handlers)
- Infrastructure Layer (repositories, utilities, external integrations)
- Presentation Layer (Telegram bot handlers)
"""
import logging
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from telegram import Update
from telegram.ext import Application
from core.config import Config
from core.logging_config import setup_logging
from infrastructure.persistence.database import Database
from infrastructure.persistence.repositories.user_repository import UserRepository
from infrastructure.persistence.repositories.video_repository import VideoRepository
from infrastructure.persistence.repositories.authorization_repository import AuthorizationRepository
from application.services.youtube_service import YoutubeService
from application.services.download_service import DownloadService
from application.services.cache_service import CacheService
from application.services.telegram_service import TelegramService
from application.services.queue_service import QueueService
from application.handlers.registration import register_all_handlers


logger = logging.getLogger(__name__)


def post_init(application: Application):
    """Post-initialization hook to start background tasks."""
    logger.info("Post-initialization starting...")
    
    # Get services from application context
    services = application.bot_data.get('services', {})
    queue_service = services.get('queue_service')
    
    if queue_service:
        logger.info("Starting queue worker...")
        # Queue worker will be started by its own internal task


def main():
    """Main entry point."""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting Telegram YouTube Bot (Refactored Version)")
        
        # Initialize configuration
        config = Config()
        
        # Get bot token
        bot_token = config.bot.get('TOKEN')
        if not bot_token:
            logger.error("Bot token not found in configuration!")
            return
        
        # Initialize database
        db = Database('users.db')
        import asyncio
        asyncio.get_event_loop().run_until_complete(db.connect())
        logger.info("Database connected")
        
        # Initialize repositories
        user_repo = UserRepository(db)
        video_repo = VideoRepository(db)
        auth_repo = AuthorizationRepository(db)
        logger.info("Repositories initialized")
        
        # Auto-authorize admin user from config
        admin_chat_id = config.bot.get('ADMIN_CHAT_ID')
        if admin_chat_id:
            import asyncio
            loop = asyncio.get_event_loop()
            # Initialize repository first to ensure table exists
            loop.run_until_complete(auth_repo.initialize())
            loop.run_until_complete(auth_repo.add_user(admin_chat_id, 'config_auto_authorize'))
            logger.info(f"Admin user {admin_chat_id} auto-authorized from config")
        
        # Initialize services
        youtube_service = YoutubeService()
        download_service = DownloadService()
        
        # Initialize cache service (repository already initialized via db)
        cache_service = CacheService(video_repo)
        queue_service = QueueService()
        
        # Create Telegram application
        application = Application.builder().token(bot_token).build()
        
        # Initialize Telegram service
        telegram_service = TelegramService(application)
        
        # Package all services for handlers
        services = {
            'youtube_service': youtube_service,
            'download_service': download_service,
            'cache_service': cache_service,
            'telegram_service': telegram_service,
            'queue_service': queue_service,
            'user_repo': user_repo,
            'auth_repo': auth_repo,
            'video_repo': video_repo,
        }
        
        # Store services in application context
        application.bot_data['services'] = services
        
        # Register all handlers
        register_all_handlers(application, services)
        logger.info("All handlers registered")
        
        # Start polling - this manages the event loop internally
        logger.info("Bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
