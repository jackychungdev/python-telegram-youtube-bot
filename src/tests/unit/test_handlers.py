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
        
        assert handler.telegram_service.send_message.called
    
    @pytest.mark.asyncio
    async def test_handle_start_unauthorized_user(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /start command for unauthorized user."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock authorization check - configure the method on the existing mock
        handler.auth_repo.is_authorized.return_value = False
        
        await handler.handle_start(mock_telegram_update, mock_context)
        
        # Should still send welcome but indicate unauthorized (via notify_user)
        assert handler.telegram_service.notify_user.called or handler.telegram_service.send_message.called
    
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


class TestMessageHandler:
    """Test cases for regular message handler (YouTube link processing)."""
    
    @pytest.mark.asyncio
    async def test_handle_youtube_link_valid_authorized_user(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test handling valid YouTube link from authorized user."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with YouTube link
        youtube_url = 'https://www.youtube.com/watch?v=test123'
        mock_message = AsyncMock()
        mock_message.text = youtube_url
        mock_message.strip = lambda: youtube_url
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user.id = 123456
        mock_telegram_update.effective_chat.id = 123456
        
        # Mock authorization
        handler.auth_repo.is_authorized = AsyncMock(return_value=True)
        
        # Mock user context
        handler.get_user_context = AsyncMock(return_value={'downloads_in_hour': 0})
        
        # Mock video info
        mock_video = MagicMock()
        mock_video.video_id = 'test123'
        mock_video.title = 'Test Video'
        mock_video.uploader = 'Test Channel'
        mock_video.duration = 180
        mock_video.view_count = 10000
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        # Mock message deletion
        processing_msg = AsyncMock()
        processing_msg.delete = AsyncMock()
        handler.telegram_service.send_message = AsyncMock(return_value=processing_msg)
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify authorization was checked
        handler.auth_repo.is_authorized.assert_called_once_with(123456)
        
        # Verify video info was fetched
        mock_all_services['youtube_service'].get_video_info.assert_called_once_with(youtube_url)
        
        # Verify messages were sent (processing + quality selection)
        assert handler.telegram_service.send_message.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_handle_youtube_link_unauthorized_user(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test handling YouTube link from unauthorized user."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with YouTube link
        mock_message = MagicMock()
        mock_message.text = 'https://www.youtube.com/watch?v=test123'
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user = MagicMock()
        mock_telegram_update.effective_user.id = 999999
        mock_telegram_update.effective_chat = MagicMock()
        mock_telegram_update.effective_chat.id = 999999
        
        # Mock unauthorized
        handler.auth_repo.is_authorized = AsyncMock(return_value=False)
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify authorization was checked
        handler.auth_repo.is_authorized.assert_called_once_with(999999)
        
        # Verify error message was sent via notify_user
        assert handler.telegram_service.notify_user.called
    
    @pytest.mark.asyncio
    async def test_handle_youtube_link_rate_limit_exceeded(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test handling YouTube link when user exceeded rate limit."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with YouTube link
        mock_message = MagicMock()
        mock_message.text = 'https://www.youtube.com/watch?v=test123'
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user = MagicMock()
        mock_telegram_update.effective_user.id = 123456
        mock_telegram_update.effective_chat = MagicMock()
        mock_telegram_update.effective_chat.id = 123456
        
        # Mock authorized
        handler.auth_repo.is_authorized = AsyncMock(return_value=True)
        
        # Mock user context with max downloads
        handler.get_user_context = AsyncMock(return_value={'downloads_in_hour': 10})
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify rate limit error message was sent via notify_user
        assert handler.telegram_service.notify_user.called
        call_args = handler.telegram_service.notify_user.call_args
        text = call_args.kwargs.get('message', '') or (call_args.args[1] if len(call_args.args) > 1 else '')
        assert 'limit' in text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_non_youtube_link_ignored(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test that non-YouTube links are ignored."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with non-YouTube link
        mock_message = AsyncMock()
        mock_message.text = 'https://example.com/video'
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user.id = 123456
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify no processing happened
        handler.auth_repo.is_authorized.assert_not_called()
        handler.telegram_service.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_youtube_link_short_url(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test handling youtu.be short URL."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with short URL
        youtube_url = 'https://youtu.be/abc123xyz'
        mock_message = AsyncMock()
        mock_message.text = youtube_url
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user.id = 123456
        mock_telegram_update.effective_chat.id = 123456
        
        # Mock authorization
        handler.auth_repo.is_authorized = AsyncMock(return_value=True)
        handler.get_user_context = AsyncMock(return_value={'downloads_in_hour': 0})
        
        # Mock video info
        mock_video = MagicMock()
        mock_video.video_id = 'abc123xyz'
        mock_video.title = 'Short URL Video'
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        processing_msg = AsyncMock()
        processing_msg.delete = AsyncMock()
        handler.telegram_service.send_message = AsyncMock(return_value=processing_msg)
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify short URL was processed
        mock_all_services['youtube_service'].get_video_info.assert_called_once_with(youtube_url)
    
    @pytest.mark.asyncio
    async def test_handle_youtube_link_shorts_url(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test handling YouTube Shorts URL."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with Shorts URL
        youtube_url = 'https://www.youtube.com/shorts/xyz789'
        mock_message = AsyncMock()
        mock_message.text = youtube_url
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user.id = 123456
        mock_telegram_update.effective_chat.id = 123456
        
        # Mock authorization
        handler.auth_repo.is_authorized = AsyncMock(return_value=True)
        handler.get_user_context = AsyncMock(return_value={'downloads_in_hour': 0})
        
        # Mock video info
        mock_video = MagicMock()
        mock_video.video_id = 'xyz789'
        mock_video.title = 'Shorts Video'
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        processing_msg = AsyncMock()
        processing_msg.delete = AsyncMock()
        handler.telegram_service.send_message = AsyncMock(return_value=processing_msg)
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify Shorts URL was processed
        mock_all_services['youtube_service'].get_video_info.assert_called_once_with(youtube_url)
    
    @pytest.mark.asyncio
    async def test_handle_youtube_link_video_fetch_error(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test handling YouTube link when video info fetch fails."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with YouTube link
        mock_message = MagicMock()
        mock_message.text = 'https://www.youtube.com/watch?v=invalid'
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user = MagicMock()
        mock_telegram_update.effective_user.id = 123456
        mock_telegram_update.effective_chat = MagicMock()
        mock_telegram_update.effective_chat.id = 123456
        
        # Mock authorization
        handler.auth_repo.is_authorized = AsyncMock(return_value=True)
        handler.get_user_context = AsyncMock(return_value={'downloads_in_hour': 0})
        
        # Mock video info fetch failure
        mock_all_services['youtube_service'].get_video_info = AsyncMock(side_effect=Exception("Video not found"))
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify error message was sent via notify_user
        assert handler.telegram_service.notify_user.called
        call_args = handler.telegram_service.notify_user.call_args
        text = call_args.kwargs.get('message', '') or (call_args.args[1] if len(call_args.args) > 1 else '')
        assert 'error' in text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_youtube_link_sends_quality_keyboard(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test that quality selection keyboard is sent."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Mock message with YouTube link
        mock_message = AsyncMock()
        mock_message.text = 'https://www.youtube.com/watch?v=test123'
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user.id = 123456
        mock_telegram_update.effective_chat.id = 123456
        
        # Mock authorization
        handler.auth_repo.is_authorized = AsyncMock(return_value=True)
        handler.get_user_context = AsyncMock(return_value={'downloads_in_hour': 0})
        
        # Mock video info
        mock_video = MagicMock()
        mock_video.video_id = 'test123'
        mock_video.title = 'Test Video'
        mock_video.uploader = 'Test Channel'
        mock_video.duration = 180
        mock_video.view_count = 50000
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        processing_msg = AsyncMock()
        processing_msg.delete = AsyncMock()
        handler.telegram_service.send_message = AsyncMock(return_value=processing_msg)
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify quality options were sent with reply_markup
        calls = handler.telegram_service.send_message.call_args_list
        assert len(calls) >= 2  # At least processing message and quality selection
        
        # Check last call has reply_markup
        last_call = calls[-1]
        assert 'reply_markup' in last_call.kwargs
    
    def test_is_youtube_url_detection(self, mock_all_services):
        """Test YouTube URL detection in message handler."""
        handler = CommandHandlers(mock_all_services['telegram_service'].bot, mock_all_services)
        
        # Test standard URLs
        assert handler._is_youtube_url('https://www.youtube.com/watch?v=abc123') is True
        assert handler._is_youtube_url('https://youtube.com/watch?v=xyz789') is True
        
        # Test short URLs
        assert handler._is_youtube_url('https://youtu.be/abc123') is True
        assert handler._is_youtube_url('http://youtu.be/xyz789') is True
        
        # Test Shorts URLs
        assert handler._is_youtube_url('https://www.youtube.com/shorts/abc123') is True
        
        # Test non-YouTube URLs
        assert handler._is_youtube_url('https://vimeo.com/123456') is False
        assert handler._is_youtube_url('https://example.com') is False
        assert handler._is_youtube_url('not a url') is False
        assert handler._is_youtube_url('') is False
    
    def test_format_duration_helper(self):
        """Test duration formatting helper method."""
        # Test MM:SS format
        assert CommandHandlers._format_duration(125) == "2:05"
        assert CommandHandlers._format_duration(60) == "1:00"
        assert CommandHandlers._format_duration(1) == "0:01"
        
        # Test HH:MM:SS format
        assert CommandHandlers._format_duration(3661) == "1:01:01"
        assert CommandHandlers._format_duration(3600) == "1:00:00"
        assert CommandHandlers._format_duration(7384) == "2:03:04"
        
        # Test edge cases
        assert CommandHandlers._format_duration(0) == "0:00"
        assert CommandHandlers._format_duration(None) == "0:00"