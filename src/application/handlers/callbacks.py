"""
Callback Handlers

Telegram callback query handlers for button clicks.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from .base_handler import BaseHandler


logger = logging.getLogger(__name__)


class CallbackHandlers(BaseHandler):
    """Handler for Telegram callback queries (button clicks).
    
    Implements:
    - Language selection callbacks
    - Quality selection callbacks
    - Authorization callbacks
    - Confirmation dialogs
    """
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback query based on callback data.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        if not update.callback_query:
            return
        
        query = update.callback_query
        data = query.data
        user_id = query.from_user.id
        
        logger.info(f"Callback received from user {user_id}: {data}")
        
        # Route to specific handler based on callback data prefix
        if data.startswith('lang_'):
            await self.handle_language_selection(update, context)
        elif data.startswith('dl_') or data.startswith('quality_'):
            await self.handle_quality_selection(update, context)
        elif data.startswith('confirm_'):
            await self.handle_confirmation(update, context)
        elif data.startswith('cancel_'):
            await self.handle_cancellation(update, context)
        else:
            logger.warning(f"Unknown callback data: {data}")
            await query.answer("Unknown action", show_alert=True)
    
    async def handle_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle language selection callback.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data  # e.g., "lang_en"
        
        # Extract language code
        lang_code = data.replace('lang_', '')
        
        # Map language codes to names
        lang_names = {
            'en': '🇬🇧 English',
            'ru': '🇷🇺 Русский',
            'es': '🇪🇸 Español',
            'de': '🇩🇪 Deutsch',
        }
        
        selected_lang = lang_names.get(lang_code, lang_code)
        
        # Save language preference
        if self.user_repo:
            await self.user_repo.update_language(user_id, lang_code)
            logger.info(f"User {user_id} selected language: {lang_code}")
        
        # Send confirmation
        await query.answer(f"Language set to {selected_lang}", show_alert=False)
        
        # Edit original message
        if self.telegram_service:
            await self.telegram_service.edit_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                text=f"✅ <b>Language Updated</b>\n\nSelected: {selected_lang}",
                parse_mode='HTML'
            )
    
    async def handle_quality_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quality selection callback.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data  # e.g., "dl_720_video123" or "quality_720_video123"
        
        # Parse quality and video ID (support both 'dl_' and 'quality_' prefixes)
        if data.startswith('dl_'):
            parts = data.replace('dl_', '').split('_')
        elif data.startswith('quality_'):
            parts = data.replace('quality_', '').split('_')
        else:
            await query.answer("Invalid selection", show_alert=True)
            return
        
        if len(parts) < 2:
            await query.answer("Invalid selection", show_alert=True)
            return
        
        quality = parts[0]
        video_id = '_'.join(parts[1:])
        
        logger.info(f"User {user_id} selected quality {quality} for video {video_id}")
        
        # Acknowledge selection with appropriate message
        if quality == 'audio':
            await query.answer("Downloading audio only...", show_alert=False)
        else:
            await query.answer(f"Downloading in {quality}p...", show_alert=False)
        
        # Get video info if needed
        if self.youtube_service:
            try:
                video = await self.youtube_service.get_video_info(
                    f'https://www.youtube.com/watch?v={video_id}'
                )
                
                # Create download task
                from src.domain import DownloadTask
                
                task = DownloadTask(
                    chat_id=query.message.chat_id,
                    user_id=user_id,
                    username=query.from_user.username or 'unknown',
                    video_id=video_id,
                    url=video.url,
                    quality=quality
                )
                
                # Add to queue
                if self.queue_service:
                    await self.queue_service.add_to_queue(task)
                    
                    # Notify user with appropriate message for audio or video
                    if quality == 'audio':
                        notification = (
                            f"✅ <b>Download Started</b>\n\n"
                            f"📹 {video.title}\n"
                            f"🎵 Quality: Audio Only\n"
                            f"⏳ You are in the queue..."
                        )
                    else:
                        notification = (
                            f"✅ <b>Download Started</b>\n\n"
                            f"📹 {video.title}\n"
                            f"🎬 Quality: {quality}p\n"
                            f"⏳ You are in the queue..."
                        )
                    
                    await self.telegram_service.edit_message(
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        text=notification,
                        parse_mode='HTML'
                    )
                    
            except Exception as e:
                logger.error(f"Failed to start download: {e}")
                await query.answer("Failed to start download", show_alert=True)
    
    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle confirmation dialog callback.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data  # e.g., "confirm_action123"
        
        action_id = data.replace('confirm_', '')
        
        logger.info(f"User {user_id} confirmed action: {action_id}")
        
        # Process confirmation based on action_id
        # This is a generic handler - specific logic depends on action type
        
        await query.answer("Confirmed!", show_alert=False)
        
        # Edit message to show confirmation
        if self.telegram_service:
            await self.telegram_service.edit_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                text="✅ <b>Action Confirmed</b>",
                parse_mode='HTML'
            )
    
    async def handle_cancellation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle cancellation callback.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data  # e.g., "cancel_task123"
        
        task_id_str = data.replace('cancel_', '')
        
        logger.info(f"User {user_id} cancelled: {task_id_str}")
        
        # Try to cancel from queue
        if self.queue_service:
            try:
                task_id = int(task_id_str)
                removed = await self.queue_service.remove_from_queue(task_id)
                
                if removed:
                    await query.answer("Cancelled!", show_alert=False)
                    
                    if self.telegram_service:
                        await self.telegram_service.edit_message(
                            chat_id=query.message.chat_id,
                            message_id=query.message.message_id,
                            text="❌ <b>Download Cancelled</b>",
                            parse_mode='HTML'
                        )
                else:
                    await query.answer("Task not found", show_alert=True)
                    
            except ValueError:
                logger.error(f"Invalid task ID: {task_id_str}")
                await query.answer("Invalid task ID", show_alert=True)
        else:
            await query.answer("Queue service not available", show_alert=True)
