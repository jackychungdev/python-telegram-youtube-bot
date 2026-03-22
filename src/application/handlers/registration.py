"""
Handler Registration Utility

Utility functions for registering all bot handlers with the application.
"""
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InlineQueryHandler, MessageHandler, filters

from .commands import CommandHandlers
from .callbacks import CallbackHandlers
from .inline import InlineHandlers


logger = logging.getLogger(__name__)


def register_all_handlers(application: Application, services: dict):
    """Register all handlers with the Telegram application.
    
    Args:
        application: Telegram application instance
        services: Dictionary of service instances
    """
    logger.info("Registering all handlers...")
    
    # Create handler instances
    command_handlers = CommandHandlers(application, services)
    callback_handlers = CallbackHandlers(application, services)
    inline_handlers = InlineHandlers(application, services)
    
    # Register command handlers
    application.add_handler(CommandHandler('start', command_handlers.handle))
    application.add_handler(CommandHandler('lang', command_handlers.handle))
    application.add_handler(CommandHandler('download', command_handlers.handle))
    application.add_handler(CommandHandler('help', command_handlers.handle))
    application.add_handler(CommandHandler('status', command_handlers.handle))
    
    # Register message handler for YouTube links (must come after command handlers)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, command_handlers.handle_message))
    
    logger.info("Command handlers registered")
    
    # Register callback query handlers
    application.add_handler(CallbackQueryHandler(callback_handlers.handle))
    logger.info("Callback handlers registered")
    
    # Register inline query handlers
    application.add_handler(InlineQueryHandler(inline_handlers.handle))
    logger.info("Inline handlers registered")
    
    logger.info("All handlers registered successfully")


def register_minimal_handlers(application: Application, services: dict):
    """Register only essential handlers (for minimal setup).
    
    Args:
        application: Telegram application instance
        services: Dictionary of service instances
    """
    logger.info("Registering minimal handlers...")
    
    command_handlers = CommandHandlers(application, services)
    
    # Only register start and help
    application.add_handler(CommandHandler('start', command_handlers.handle))
    application.add_handler(CommandHandler('help', command_handlers.handle))
    
    logger.info("Minimal handlers registered")
