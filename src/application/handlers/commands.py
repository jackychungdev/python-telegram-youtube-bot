"""
Command Handlers

Telegram command handlers (/start, /lang, /download, etc.).
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .base_handler import BaseHandler


logger = logging.getLogger(__name__)


class CommandHandlers(BaseHandler):
    """Handler for Telegram bot commands.
    
    Implements:
    - /start - Welcome and authorization
    - /lang - Language selection
    - /download - Download help
    - /help - Help information
    - /status - Bot status
    """
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle command based on command name.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        if not update.message or not update.effective_user:
            return
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        command = update.message.text.split()[0].replace('/', '') if update.message.text else ''
        
        # Route to specific handler
        handlers = {
            'start': self.handle_start,
            'lang': self.handle_lang,
            'download': self.handle_download,
            'help': self.handle_help,
            'status': self.handle_status,
        }
        
        handler = handlers.get(command)
        if handler:
            await handler(update, context)
        else:
            logger.warning(f"Unknown command: {command}")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"/start command from user {user_id} ({user.username})")
        
        # Log user action
        await self.log_user_action(user_id, 'start')
        
        # Create or update user record
        if self.user_repo:
            await self.user_repo.create_or_update(
                user_id=user_id,
                username=user.username or 'unknown'
            )
        
        # Check authorization
        is_authorized = False
        if self.auth_repo:
            is_authorized = await self.auth_repo.is_authorized(user_id)
        
        # Build welcome message
        welcome_text = f"👋 <b>Welcome {user.first_name}!</b>\n\n"
        
        if is_authorized:
            welcome_text += (
                "✅ <b>You are authorized</b>\n\n"
                "I can download YouTube videos for you!\n\n"
                "📝 <b>How to use:</b>\n"
                "• Send me a YouTube link\n"
                "• Or use /download command\n\n"
                "⚙️ <b>Commands:</b>\n"
                "/lang - Change language\n"
                "/status - Check bot status\n"
                "/help - Get help"
            )
        else:
            welcome_text += (
                "ℹ️ <b>Authorization Required</b>\n\n"
                "This bot is private. Please contact the administrator for access.\n\n"
                "If you think this is a mistake, please reach out to the bot owner."
            )
        
        # Send message
        if self.telegram_service:
            await self.telegram_service.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode='HTML'
            )
    
    async def handle_lang(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /lang command for language selection.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        user_id = update.effective_user.id
        
        logger.info(f"/lang command from user {user_id}")
        await self.log_user_action(user_id, 'lang')
        
        # Check authorization
        if not await self.check_authorization(user_id):
            await self.send_error_message(
                update.effective_chat.id,
                "You are not authorized to use this bot"
            )
            return
        
        # Create language selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            ],
            [
                InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
                InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if self.telegram_service:
            await self.telegram_service.send_message(
                chat_id=update.effective_chat.id,
                text="<b>Select your language:</b>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    
    async def handle_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /download command with usage instructions.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        user_id = update.effective_user.id
        
        logger.info(f"/download command from user {user_id}")
        await self.log_user_action(user_id, 'download')
        
        # Check authorization
        if not await self.check_authorization(user_id):
            await self.send_error_message(
                update.effective_chat.id,
                "You are not authorized to use this bot"
            )
            return
        
        # Get user context
        user_context = await self.get_user_context(user_id)
        downloads_count = 0
        can_download = True
        
        if user_context:
            downloads_count = user_context.get('downloads_in_hour') or 0
            # Simple rate limit check
            can_download = downloads_count < 10
        
        download_text = (
            "📥 <b>Download Instructions</b>\n\n"
            "1️⃣ <b>Send a YouTube link</b>\n"
            "   • youtube.com/watch?v=...\n"
            "   • youtu.be/...\n\n"
            "2️⃣ <b>Choose quality</b>\n"
            "   • I'll ask you to select quality\n"
            "   • Options: 144p to 4K + Audio only\n\n"
            "3️⃣ <b>Wait for download</b>\n"
            "   • I'll process and send the file\n"
            "   • Progress updates provided\n\n"
            "⚠️ <b>Limitations:</b>\n"
            f"• Max 10 downloads per hour\n"
            f"• Your usage: {downloads_count}/10 this hour\n"
            "• Videos up to 2GB\n\n"
            "💡 <b>Tip:</b> Just paste the link and I'll handle the rest!"
        )
        
        if self.telegram_service:
            await self.telegram_service.send_message(
                chat_id=update.effective_chat.id,
                text=download_text,
                parse_mode='HTML'
            )
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command with comprehensive help information.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        user_id = update.effective_user.id
        
        logger.info(f"/help command from user {user_id}")
        await self.log_user_action(user_id, 'help')
        
        help_text = (
            "🤖 <b>Bot Help</b>\n\n"
            "<b>What I do:</b>\n"
            "I download YouTube videos and send them to you as files.\n\n"
            "<b>Supported Features:</b>\n"
            "• Multiple quality options (144p - 4K)\n"
            "• Audio-only extraction\n"
            "• Fast downloads with progress tracking\n"
            "• Smart caching for popular videos\n\n"
            "<b>Commands:</b>\n"
            "/start - Start the bot\n"
            "/lang - Change language\n"
            "/download - Download instructions\n"
            "/status - Bot status\n"
            "/help - This help message\n\n"
            "<b>Quick Start:</b>\n"
            "1. Send me any YouTube link\n"
            "2. Choose your preferred quality\n"
            "3. Wait for me to process\n"
            "4. Receive your video!\n\n"
            "<b>Troubleshooting:</b>\n"
            "• Make sure links are public\n"
            "• Check your download limit (10/hour)\n"
            "• Large videos may take longer\n\n"
            "Need more help? Contact the administrator."
        )
        
        if self.telegram_service:
            await self.telegram_service.send_message(
                chat_id=update.effective_chat.id,
                text=help_text,
                parse_mode='HTML'
            )
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command showing bot and queue status.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        user_id = update.effective_user.id
        
        logger.info(f"/status command from user {user_id}")
        await self.log_user_action(user_id, 'status')
        
        # Check authorization
        if not await self.check_authorization(user_id):
            await self.send_error_message(
                update.effective_chat.id,
                "You are not authorized to use this bot"
            )
            return
        
        # Get queue status
        queue_status = {}
        if self.queue_service:
            queue_status = self.queue_service.get_queue_status()
        
        # Get cache stats
        cache_stats = {}
        if self.cache_service:
            cache_stats = await self.cache_service.get_cache_statistics()
        
        # Build status message
        status_text = "📊 <b>Bot Status</b>\n\n"
        
        # Queue info
        if queue_status:
            status_text += (
                f"<b>Queue:</b>\n"
                f"• Waiting: {queue_status.get('queue_length', 0)}\n"
                f"• Active: {queue_status.get('active_tasks', 0)}\n"
                f"• Max concurrent: {queue_status.get('max_concurrent', 3)}\n\n"
            )
        
        # Cache info
        if cache_stats and cache_stats.get('enabled'):
            status_text += (
                f"<b>Cache:</b>\n"
                f"• Files: {cache_stats.get('total_files', 0)}\n"
                f"• Unique videos: {cache_stats.get('unique_videos', 0)}\n"
                f"• Size: {cache_stats.get('total_size_mb', 0):.1f} MB\n\n"
            )
        
        # User info
        user_context = await self.get_user_context(user_id)
        if user_context:
            downloads = user_context.get('downloads_in_hour') or 0
            status_text += (
                f"<b>Your Usage:</b>\n"
                f"• Downloads this hour: {downloads}/10\n"
            )
        
        status_text += "\n✅ Bot is online and ready!"
        
        if self.telegram_service:
            await self.telegram_service.send_message(
                chat_id=update.effective_chat.id,
                text=status_text,
                parse_mode='HTML'
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages containing YouTube links.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        if not update.message or not update.effective_user:
            return
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message_text = update.message.text.strip()
        
        # Check if it's a YouTube URL
        if not self._is_youtube_url(message_text):
            return
        
        logger.info(f"YouTube link received from user {user_id}: {message_text}")
        await self.log_user_action(user_id, 'youtube_link')
        
        # Check authorization
        if not await self.check_authorization(user_id):
            await self.send_error_message(
                chat_id,
                "🔒 You are not authorized to use this bot. Please contact the admin."
            )
            return
        
        # Check rate limit
        user_context = await self.get_user_context(user_id)
        downloads_count = user_context.get('downloads_in_hour', 0) if user_context else 0
        
        if downloads_count >= 10:
            await self.send_error_message(
                chat_id,
                "⚠️ You've reached your download limit for this hour (10 downloads). Please wait before downloading again."
            )
            return
        
        try:
            # Send processing message
            processing_msg = await self.telegram_service.send_message(
                chat_id=chat_id,
                text="🔄 <b>Processing YouTube link...</b>\n\nPlease wait while I fetch video information.",
                parse_mode='HTML'
            )
            
            # Get video info
            video = await self.youtube_service.get_video_info(message_text)
            
            # Delete processing message
            try:
                await processing_msg.delete()
            except:
                pass
            
            # Create quality selection keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🎬 4K (2160p)", callback_data=f"dl_2160_{video.video_id}"),
                    InlineKeyboardButton("🎬 2K (1440p)", callback_data=f"dl_1440_{video.video_id}")
                ],
                [
                    InlineKeyboardButton("🎬 Full HD (1080p)", callback_data=f"dl_1080_{video.video_id}"),
                    InlineKeyboardButton("🎬 HD (720p)", callback_data=f"dl_720_{video.video_id}")
                ],
                [
                    InlineKeyboardButton("📱 SD (480p)", callback_data=f"dl_480_{video.video_id}"),
                    InlineKeyboardButton("📱 SD (360p)", callback_data=f"dl_360_{video.video_id}")
                ],
                [
                    InlineKeyboardButton("🎵 Audio Only", callback_data=f"dl_audio_{video.video_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send video info with quality options
            duration_str = self._format_duration(video.duration)
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    f"📹 <b>{video.title}</b>\n\n"
                    f"🎬 Channel: {video.uploader}\n"
                    f"⏱ Duration: {duration_str}\n"
                    f"👁 Views: {video.view_count:,}\n\n"
                    f"<b>Select download quality:</b>"
                ),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Failed to process YouTube link: {e}", exc_info=True)
            await self.send_error_message(
                chat_id,
                f"❌ Failed to process this video. Please check the link and try again.\n\nError: {str(e)}"
            )
    
    def _is_youtube_url(self, text: str) -> bool:
        """Check if text is a YouTube URL.
        
        Args:
            text: Text to check
            
        Returns:
            True if YouTube URL
        """
        youtube_patterns = [
            'youtube.com/watch',
            'youtu.be/',
            'youtube.com/shorts/',
        ]
        
        return any(pattern in text for pattern in youtube_patterns)
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if not seconds:
            return "0:00"
        
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
