"""
Inline Handlers

Telegram inline query handlers for inline mode.
"""
import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes

from .base_handler import BaseHandler


logger = logging.getLogger(__name__)


class InlineHandlers(BaseHandler):
    """Handler for Telegram inline queries.
    
    Implements:
    - Inline video search
    - Quick download links
    - Preview generation
    """
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline query.
        
        Args:
            update: Telegram update (inline_query)
            context: Telegram context
        """
        if not update.inline_query:
            return
        
        inline_query = update.inline_query
        query_text = inline_query.query.strip()
        user_id = inline_query.from_user.id
        
        logger.info(f"Inline query from user {user_id}: '{query_text}'")
        
        # Check authorization
        if not await self.check_authorization(user_id):
            results = [
                InlineQueryResultArticle(
                    id='auth_required',
                    title="🔒 Authorization Required",
                    description="You need to be authorized to use this bot. Start the bot first.",
                    input_message_content=InputTextMessageContent(
                        message_text="🔒 <b>Authorization Required</b>\n\nPlease start the bot @YourBotName to get authorized.",
                        parse_mode='HTML'
                    )
                )
            ]
            await inline_query.answer(results, cache_time=0)
            return
        
        # Handle different query types
        if not query_text:
            # Empty query - show help
            results = await self._get_help_results()
        elif self._is_youtube_url(query_text):
            # YouTube URL - show download options
            results = await self._get_url_results(query_text)
        else:
            # Text query - could be video search
            results = await self._get_search_results(query_text)
        
        # Send results
        await inline_query.answer(results, cache_time=30)
    
    async def _get_help_results(self):
        """Get help inline query results.
        
        Returns:
            List of InlineQueryResultArticle
        """
        return [
            InlineQueryResultArticle(
                id='help_1',
                title="📥 How to Use",
                description="Send a YouTube link to download",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "📥 <b>How to Download</b>\n\n"
                        "1. Copy a YouTube video URL\n"
                        "2. Paste it here\n"
                        "3. Choose your quality\n"
                        "4. Get your video!\n\n"
                        "💡 Tip: Works with youtu.be and youtube.com links"
                    ),
                    parse_mode='HTML'
                )
            ),
            InlineQueryResultArticle(
                id='help_2',
                title="⚙️ Commands",
                description="Available bot commands",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "<b>Bot Commands:</b>\n\n"
                        "/start - Start the bot\n"
                        "/lang - Change language\n"
                        "/download - Instructions\n"
                        "/status - Bot status\n"
                        "/help - Get help"
                    ),
                    parse_mode='HTML'
                )
            )
        ]
    
    async def _get_url_results(self, url: str):
        """Get results for YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            List of InlineQueryResultArticle
        """
        try:
            # Get video info
            if self.youtube_service:
                video = await self.youtube_service.get_video_info(url)
                
                # Create quality options
                results = []
                
                # Add main result
                results.append(
                    InlineQueryResultArticle(
                        id=f'info_{video.video_id}',
                        title=f"📹 {video.title}",
                        description=f"by {video.uploader} • {self._format_duration(video.duration)}",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"<b>{video.title}</b>\n\n"
                                f"🎬 Channel: {video.uploader}\n"
                                f"⏱ Duration: {self._format_duration(video.duration)}\n"
                                f"👁 Views: {video.view_count:,}\n\n"
                                f"Select quality below to download:"
                            ),
                            parse_mode='HTML'
                        )
                    )
                )
                
                # Add quality options as separate results
                qualities = ['2160', '1440', '1080', '720', '480', '360', 'audio']
                
                for quality in qualities:
                    label = f"{quality}p" if quality != 'audio' else "🎵 Audio Only"
                    results.append(
                        InlineQueryResultArticle(
                            id=f'{quality}_{video.video_id}',
                            title=f"⬇️ Download {label}",
                            description=f"Click to download in {quality}",
                            input_message_content=InputTextMessageContent(
                                message_text=(
                                    f"📥 <b>Download Started</b>\n\n"
                                    f"Video: {video.title}\n"
                                    f"Quality: {label}\n\n"
                                    f"Processing..."
                                ),
                                parse_mode='HTML'
                            )
                        )
                    )
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
        
        # Fallback
        return [
            InlineQueryResultArticle(
                id='error',
                title="❌ Error",
                description="Failed to process video",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Failed to process this video. Please try another one."
                )
            )
        ]
    
    async def _get_search_results(self, query: str):
        """Get search results.
        
        Args:
            query: Search query
            
        Returns:
            List of InlineQueryResultArticle
        """
        # For now, just provide helpful message
        return [
            InlineQueryResultArticle(
                id='search_info',
                title=f"🔍 Searching for: {query}",
                description="Inline search is limited. Use the bot directly for full features.",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🔍 <b>Search Query</b>\n\n"
                        f"You searched for: <b>{query}</b>\n\n"
                        "For best results, please start the bot and send a YouTube URL directly.\n\n"
                        "This inline mode has limited functionality."
                    ),
                    parse_mode='HTML'
                )
            )
        ]
    
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
