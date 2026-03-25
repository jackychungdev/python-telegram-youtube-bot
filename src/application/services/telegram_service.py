"""
Telegram Service

Business logic for Telegram bot operations including message sending,
file uploads, and user interactions.
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from core.exceptions import BotException


logger = logging.getLogger(__name__)


class TelegramService:
    """Service for Telegram bot operations.
    
    Handles all Telegram API interactions:
    - Message sending (text, media, documents)
    - Keyboard/inline button management
    - File uploads with progress
    - User notifications
    
    Attributes:
        application: Telegram application instance
        bot: Bot instance
    """
    
    def __init__(self, application: Application):
        """Initialize Telegram service.
        
        Args:
            application: Telegram application instance
        """
        self.application = application
        self.bot = application.bot
        logger.info("Telegram service initialized")
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = 'HTML',
        reply_markup: InlineKeyboardMarkup = None,
        disable_notification: bool = False
    ) -> bool:
        """Send text message to user.
        
        Args:
            chat_id: Target chat ID
            text: Message text
            parse_mode: Message parse mode ('HTML', 'Markdown')
            reply_markup: Optional inline keyboard
            disable_notification: Send without notification
            
        Returns:
            True if sent successfully
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=disable_notification
            )
            logger.debug(f"Message sent to {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False
    
    async def send_video(
        self,
        chat_id: int,
        video_path: str,
        title: str,
        thumbnail_path: str = None,
        caption: str = None,
        reply_markup: InlineKeyboardMarkup = None,
        progress_callback: callable = None
    ) -> Optional[str]:
        """Send video file to user.
        
        Args:
            chat_id: Target chat ID
            video_path: Path to video file
            title: Video title
            thumbnail_path: Path to thumbnail (optional)
            caption: Video caption
            reply_markup: Optional inline keyboard
            progress_callback: Upload progress callback
            
        Returns:
            File ID if successful, None otherwise
        """
        try:
            from pathlib import Path
            
            video_file = Path(video_path)
            if not video_file.exists():
                logger.error(f"Video file not found: {video_path}")
                return None
            
            # Prepare thumbnail
            thumb = None
            if thumbnail_path:
                thumb_file = Path(thumbnail_path)
                if thumb_file.exists():
                    thumb = thumb_file
            
            # Send video
            with open(video_file, 'rb') as f:
                message = await self.bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    thumbnail=thumb,
                    caption=caption or title,
                    parse_mode='HTML',
                    reply_markup=reply_markup,
                    filename=video_file.name
                )
            
            file_id = message.video.file_id
            logger.info(f"Video sent to {chat_id}: {title}")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to send video to {chat_id}: {e}")
            return None
    
    async def send_audio(
        self,
        chat_id: int,
        audio_path: str,
        title: str,
        performer: str = None,
        thumbnail_path: str = None,
        caption: str = None,
        reply_markup: InlineKeyboardMarkup = None
    ) -> Optional[str]:
        """Send audio file to user.
        
        Args:
            chat_id: Target chat ID
            audio_path: Path to audio file
            title: Audio title
            performer: Performer name (optional)
            thumbnail_path: Path to thumbnail (optional)
            caption: Audio caption
            reply_markup: Optional inline keyboard
            
        Returns:
            File ID if successful, None otherwise
        """
        try:
            from pathlib import Path
            
            audio_file = Path(audio_path)
            if not audio_file.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            # Prepare thumbnail
            thumb = None
            if thumbnail_path:
                thumb_file = Path(thumbnail_path)
                if thumb_file.exists():
                    thumb = thumb_file
            
            # Send audio
            with open(audio_file, 'rb') as f:
                message = await self.bot.send_audio(
                    chat_id=chat_id,
                    audio=f,
                    thumbnail=thumb,
                    caption=caption or title,
                    parse_mode='HTML',
                    reply_markup=reply_markup,
                    title=title,
                    performer=performer,
                    filename=audio_file.name
                )
            
            file_id = message.audio.file_id
            logger.info(f"Audio sent to {chat_id}: {title}")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to send audio to {chat_id}: {e}")
            return None
    
    async def send_document(
        self,
        chat_id: int,
        document_path: str,
        caption: str = None,
        reply_markup: InlineKeyboardMarkup = None
    ) -> Optional[str]:
        """Send document file to user.
        
        Args:
            chat_id: Target chat ID
            document_path: Path to document
            caption: Document caption
            reply_markup: Optional inline keyboard
            
        Returns:
            File ID if successful, None otherwise
        """
        try:
            from pathlib import Path
            
            doc_file = Path(document_path)
            if not doc_file.exists():
                logger.error(f"Document not found: {document_path}")
                return None
            
            with open(doc_file, 'rb') as f:
                message = await self.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=reply_markup,
                    filename=doc_file.name
                )
            
            file_id = message.document.file_id
            logger.info(f"Document sent to {chat_id}: {doc_file.name}")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to send document to {chat_id}: {e}")
            return None
    
    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str = 'HTML',
        reply_markup: InlineKeyboardMarkup = None
    ) -> bool:
        """Edit existing message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID to edit
            text: New text
            parse_mode: Parse mode
            reply_markup: New keyboard (optional)
            
        Returns:
            True if edited successfully
        """
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            logger.debug(f"Message {message_id} edited in {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return False
    
    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            await self.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
            logger.debug(f"Message {message_id} deleted in {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False
    
    def create_inline_keyboard(self, buttons: List[List[Dict[str, Any]]]) -> InlineKeyboardMarkup:
        """Create inline keyboard from button configuration.
        
        Args:
            buttons: List of button rows, each row is list of dicts
                     Each dict has 'text' and 'callback_data' keys
            
        Returns:
            InlineKeyboardMarkup instance
            
        Example:
            ```python
            buttons = [
                [{'text': '✅ Accept', 'callback_data': 'accept_123'}],
                [{'text': '❌ Reject', 'callback_data': 'reject_123'}]
            ]
            keyboard = create_inline_keyboard(buttons)
            ```
        """
        keyboard = []
        
        for row in buttons:
            button_row = []
            for btn in row:
                button = InlineKeyboardButton(
                    text=btn['text'],
                    callback_data=btn['callback_data']
                )
                button_row.append(button)
            keyboard.append(button_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    async def notify_user(
        self,
        user_id: int,
        message: str,
        notification_type: str = 'info'
    ) -> bool:
        """Send notification to user.
        
        Args:
            user_id: User ID
            message: Notification message
            notification_type: Type of notification ('info', 'success', 'error', 'warning')
            
        Returns:
            True if sent successfully
        """
        # Add emoji based on type
        emojis = {
            'info': 'ℹ️',
            'success': '✅',
            'error': '❌',
            'warning': '⚠️'
        }
        
        emoji = emojis.get(notification_type, 'ℹ️')
        formatted_message = f"{emoji} <b>{message}</b>"
        
        return await self.send_message(
            chat_id=user_id,
            text=formatted_message,
            disable_notification=False
        )
    
    async def broadcast_message(
        self,
        user_ids: List[int],
        message: str,
        delay_seconds: float = 0.1
    ) -> Dict[str, int]:
        """Broadcast message to multiple users.
        
        Args:
            user_ids: List of user IDs
            message: Message to broadcast
            delay_seconds: Delay between messages to avoid rate limits
            
        Returns:
            Dictionary with success/failure counts
        """
        stats = {'sent': 0, 'failed': 0}
        
        for user_id in user_ids:
            try:
                success = await self.send_message(user_id, message)
                if success:
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1
                
                # Small delay to avoid hitting rate limits
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)
                    
            except Exception as e:
                logger.error(f"Broadcast failed for user {user_id}: {e}")
                stats['failed'] += 1
        
        logger.info(f"Broadcast complete: {stats['sent']} sent, {stats['failed']} failed")
        return stats
