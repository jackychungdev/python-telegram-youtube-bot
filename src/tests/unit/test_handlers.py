"""
Unit Tests for Presentation Layer

Tests for command, callback, and inline handlers.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.application.handlers.commands import CommandHandlers
from src.application.handlers.callbacks import CallbackHandlers
from src.application.handlers.inline import InlineHandlers


class TestCommandHandlers:
    """Test cases for CommandHandlers."""
    
    @pytest.mark.asyncio
    async def test_handle_start_authorized_user(
        self, 
        mock_telegram_update, 
        mock_context,
        mock_all_services
    ):
        """Test /start command for authorized user."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock authorization check - configure the method on the existing mock
        handler.auth_repo.is_authorized.return_value = True
        
        await handler.handle_start(mock_telegram_update, mock_context)
        
        # Verify message was sent
        assert handler.telegram_service.send_message.called
        
        # Verify user was created/updated
        handler.user_repo.create_or_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_start_unauthorized_user(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /start command for unauthorized user."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock authorization check to fail
        handler.auth_repo.is_authorized.return_value = False
        
        await handler.handle_start(mock_telegram_update, mock_context)
        
        # Should still send welcome but indicate unauthorized
        assert handler.telegram_service.send_message.called
    
    @pytest.mark.asyncio
    async def test_handle_lang_shows_keyboard(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /lang command shows language selection."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock authorization
        handler.auth_repo.is_authorized.return_value = True
        
        await handler.handle_lang(mock_telegram_update, mock_context)
        
        # Verify keyboard was sent
        call_args = handler.telegram_service.send_message.call_args
        assert 'reply_markup' in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_handle_download_shows_instructions(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /download command shows instructions."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock authorization check
        handler.auth_repo.is_authorized.return_value = True
        
        # Mock get_user_context to return a dict (not a coroutine)
        async def mock_get_context(user_id):
            return {'downloads_in_hour': 0}
        
        handler.get_user_context = mock_get_context
        
        await handler.handle_download(mock_telegram_update, mock_context)
        
        assert handler.telegram_service.send_message.called
    
    @pytest.mark.asyncio
    async def test_handle_help_shows_info(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /help command shows help information."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        await handler.handle_help(mock_telegram_update, mock_context)
        
        assert handler.telegram_service.send_message.called
    
    @pytest.mark.asyncio
    async def test_handle_status_shows_stats(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /status command shows bot status."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock authorization check
        handler.auth_repo.is_authorized.return_value = True
        
        # Mock queue status
        mock_all_services['queue_service'].get_queue_status.return_value = {
            'queue_length': 2,
            'active_tasks': 1,
            'max_concurrent': 3
        }
        
        # Mock cache stats
        mock_all_services['cache_service'].get_cache_statistics.return_value = {'total_files': 50, 'enabled': True}
        
        await handler.handle_status(mock_telegram_update, mock_context)
        
        assert handler.telegram_service.send_message.called


class TestCallbackHandlers:
    """Test cases for CallbackHandlers."""
    
    @pytest.mark.asyncio
    async def test_handle_language_selection(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test language selection callback."""
        handler = CallbackHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Create callback query mock
        mock_query = AsyncMock()
        mock_query.data = 'lang_en'
        mock_query.from_user.id = 123456
        mock_query.message.chat_id = 123456
        mock_query.message.message_id = 1
        
        mock_telegram_update.callback_query = mock_query
        
        await handler.handle_language_selection(mock_telegram_update, mock_context)
        
        # Verify answer was sent
        mock_query.answer.assert_called()
        
        # Verify language was saved
        handler.user_repo.update_language.assert_called_once_with(123456, 'en')
    
    @pytest.mark.asyncio
    async def test_handle_quality_selection_starts_download(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test quality selection starts download."""
        handler = CallbackHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Create callback query mock
        mock_query = AsyncMock()
        mock_query.data = 'quality_720_testvideo123'
        mock_query.from_user.id = 123456
        mock_query.message.chat_id = 123456
        mock_query.message.message_id = 1
        
        mock_telegram_update.callback_query = mock_query
        
        # Mock youtube service
        mock_video = MagicMock()
        mock_video.video_id = 'testvideo123'
        mock_video.url = 'https://youtube.com/watch?v=testvideo123'
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        await handler.handle_quality_selection(mock_telegram_update, mock_context)
        
        # Verify task was added to queue
        mock_all_services['queue_service'].add_to_queue.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_cancellation_removes_from_queue(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test cancellation callback."""
        handler = CallbackHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Create callback query mock
        mock_query = AsyncMock()
        mock_query.data = 'cancel_123'
        mock_query.from_user.id = 123456
        mock_query.message.chat_id = 123456
        mock_query.message.message_id = 1
        
        mock_telegram_update.callback_query = mock_query
        
        # Mock queue removal
        mock_all_services['queue_service'].remove_from_queue = AsyncMock(return_value=True)
        
        await handler.handle_cancellation(mock_telegram_update, mock_context)
        
        # Verify removal was attempted
        mock_all_services['queue_service'].remove_from_queue.assert_called_once_with(123)


class TestInlineHandlers:
    """Test cases for InlineHandlers."""
    
    @pytest.mark.asyncio
    async def test_inline_empty_query_shows_help(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test inline query with empty text shows help."""
        handler = InlineHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Create inline query mock
        mock_query = AsyncMock()
        mock_query.query = ''
        mock_query.from_user.id = 123456
        
        mock_telegram_update.inline_query = mock_query
        
        await handler.handle(mock_telegram_update, mock_context)
        
        # Verify results were returned
        mock_query.answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_inline_youtube_url_shows_options(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test inline query with YouTube URL."""
        handler = InlineHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Create inline query mock
        mock_query = AsyncMock()
        mock_query.query = 'https://www.youtube.com/watch?v=test123'
        mock_query.from_user.id = 123456
        
        mock_telegram_update.inline_query = mock_query
        
        # Mock video info
        mock_video = MagicMock()
        mock_video.video_id = 'test123'
        mock_video.title = 'Test Video'
        mock_video.uploader = 'Test Channel'
        mock_video.duration = 180
        
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        await handler.handle(mock_telegram_update, mock_context)
        
        # Verify results were returned
        mock_query.answer.assert_called()
    
    def test_is_youtube_url(self, mock_all_services):
        """Test YouTube URL detection."""
        handler = InlineHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        assert handler._is_youtube_url('https://www.youtube.com/watch?v=abc123') is True
        assert handler._is_youtube_url('https://youtu.be/xyz789') is True
        assert handler._is_youtube_url('not a url') is False
        assert handler._is_youtube_url('https://example.com') is False
    
    def test_format_duration(self):
        """Test duration formatting."""
        # Test MM:SS format
        assert InlineHandlers._format_duration(125) == "2:05"
        
        # Test HH:MM:SS format
        assert InlineHandlers._format_duration(3661) == "1:01:01"
        
        # Test zero
        assert InlineHandlers._format_duration(0) == "0:00"
