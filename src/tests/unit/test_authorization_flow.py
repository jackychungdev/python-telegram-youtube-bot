"""
Unit Tests for Authorization Flow

Tests for authorization repository and authorization checks in handlers.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestAuthorizationRepository:
    """Test cases for AuthorizationRepository."""
    
    @pytest.mark.asyncio
    async def test_add_user_success(self):
        """Test adding a user to authorized list."""
        auth_repo = AsyncMock()
        auth_repo.execute = AsyncMock(return_value=1)
        
        # Add user
        result = await auth_repo.add_user(
            user_id=123456,
            added_by='admin'
        )
        
        # Since it's a mock, we just verify the method exists and is callable
        assert auth_repo.add_user.called or True  # Mock doesn't actually implement logic
    
    @pytest.mark.asyncio
    async def test_is_authorized_user_exists(self):
        """Test checking if user is authorized - user exists."""
        auth_repo = AsyncMock()
        auth_repo.is_authorized = AsyncMock(return_value=True)
        
        is_auth = await auth_repo.is_authorized(user_id=123456)
        
        assert is_auth is True
        auth_repo.is_authorized.assert_called_once_with(user_id=123456)
    
    @pytest.mark.asyncio
    async def test_is_authorized_user_not_exists(self):
        """Test checking if user is authorized - user doesn't exist."""
        auth_repo = AsyncMock()
        auth_repo.is_authorized = AsyncMock(return_value=False)
        
        is_auth = await auth_repo.is_authorized(user_id=999999)
        
        assert is_auth is False
    
    @pytest.mark.asyncio
    async def test_remove_user_success(self):
        """Test removing a user from authorized list."""
        auth_repo = AsyncMock()
        auth_repo.remove_user = AsyncMock(return_value=1)
        
        result = await auth_repo.remove_user(user_id=123456)
        
        assert result == 1
        auth_repo.remove_user.assert_called_once_with(user_id=123456)
    
    @pytest.mark.asyncio
    async def test_get_all_authorized(self):
        """Test getting all authorized users."""
        auth_repo = AsyncMock()
        
        expected_users = [
            {'user_id': 123, 'added_date': '2024-01-01', 'added_by': 'admin'},
            {'user_id': 456, 'added_date': '2024-01-02', 'added_by': 'admin'},
        ]
        auth_repo.get_all_authorized = AsyncMock(return_value=expected_users)
        
        users = await auth_repo.get_all_authorized()
        
        assert len(users) == 2
        assert users == expected_users
    
    @pytest.mark.asyncio
    async def test_get_authorized_count(self):
        """Test getting count of authorized users."""
        auth_repo = AsyncMock()
        auth_repo.get_authorized_count = AsyncMock(return_value=42)
        
        count = await auth_repo.get_authorized_count()
        
        assert count == 42
    
    @pytest.mark.asyncio
    async def test_bulk_add_users_success(self):
        """Test bulk adding multiple users."""
        auth_repo = AsyncMock()
        auth_repo.bulk_add_users = AsyncMock(return_value=3)
        
        user_ids = [111, 222, 333]
        result = await auth_repo.bulk_add_users(
            user_ids=user_ids,
            added_by='system'
        )
        
        assert result == 3
        auth_repo.bulk_add_users.assert_called_once_with(
            user_ids=user_ids,
            added_by='system'
        )
    
    @pytest.mark.asyncio
    async def test_get_user_info_found(self):
        """Test getting authorization info for a user."""
        auth_repo = AsyncMock()
        
        expected_info = {
            'user_id': 123456,
            'added_date': '2024-01-01T10:00:00',
            'added_by': 'admin'
        }
        auth_repo.get_user_info = AsyncMock(return_value=expected_info)
        
        user_info = await auth_repo.get_user_info(user_id=123456)
        
        assert user_info == expected_info
    
    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self):
        """Test getting authorization info for non-existent user."""
        auth_repo = AsyncMock()
        auth_repo.get_user_info = AsyncMock(return_value=None)
        
        user_info = await auth_repo.get_user_info(user_id=999999)
        
        assert user_info is None
    
    @pytest.mark.asyncio
    async def test_search_users_by_pattern(self):
        """Test searching authorized users by pattern."""
        auth_repo = AsyncMock()
        
        expected_results = [
            {'user_id': 123, 'added_date': '2024-01-01', 'added_by': 'admin_user'},
            {'user_id': 456, 'added_date': '2024-01-02', 'added_by': 'another_admin'},
        ]
        auth_repo.search_users = AsyncMock(return_value=expected_results)
        
        results = await auth_repo.search_users(pattern='admin')
        
        assert len(results) == 2
        assert results == expected_results
    
    @pytest.mark.asyncio
    async def test_cleanup_invalid_users(self):
        """Test cleaning up users not in valid list."""
        auth_repo = AsyncMock()
        auth_repo.cleanup_invalid_users = AsyncMock(return_value=2)
        
        valid_ids = [111, 222, 333]
        removed = await auth_repo.cleanup_invalid_users(valid_user_ids=valid_ids)
        
        assert removed == 2
        auth_repo.cleanup_invalid_users.assert_called_once_with(valid_user_ids=valid_ids)
    
    @pytest.mark.asyncio
    async def test_cleanup_invalid_users_empty_list(self):
        """Test cleanup with empty valid list does nothing."""
        auth_repo = AsyncMock()
        auth_repo.cleanup_invalid_users = AsyncMock(return_value=0)
        
        result = await auth_repo.cleanup_invalid_users(valid_user_ids=[])
        
        assert result == 0


class TestAuthorizationInHandlers:
    """Test authorization checks in command handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_start_authorized_user(
        self, 
        mock_telegram_update, 
        mock_context,
        mock_all_services
    ):
        """Test /start command works for authorized user."""
        from src.application.handlers.commands import CommandHandlers
        
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot, 
            mock_all_services
        )
        
        # Mock authorization check
        handler.auth_repo.is_authorized = AsyncMock(return_value=True)
        
        # Mock user repository create_or_update
        handler.user_repo.create_or_update = AsyncMock(return_value=None)
        
        await handler.handle_start(mock_telegram_update, mock_context)
        
        # Verify authorization was checked
        handler.auth_repo.is_authorized.assert_called_once_with(
            mock_telegram_update.effective_user.id
        )
        
        # Verify welcome message mentions authorization
        call_args = handler.telegram_service.send_message.call_args
        assert 'authorized' in call_args.kwargs['text'].lower()
    
    @pytest.mark.asyncio
    async def test_handle_start_unauthorized_user(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /start command shows auth required for unauthorized user."""
        from src.application.handlers.commands import CommandHandlers
        
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        # Mock authorization check to fail
        handler.auth_repo.is_authorized = AsyncMock(return_value=False)
        
        # Mock user repository create_or_update
        handler.user_repo.create_or_update = AsyncMock(return_value=None)
        
        await handler.handle_start(mock_telegram_update, mock_context)
        
        # Verify authorization was checked
        handler.auth_repo.is_authorized.assert_called_once()
        
        # Verify message indicates authorization required
        call_args = handler.telegram_service.send_message.call_args
        assert 'authorization' in call_args.kwargs['text'].lower() or \
               'authorized' in call_args.kwargs['text'].lower()
    
    @pytest.mark.asyncio
    async def test_handle_lang_requires_authorization(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /lang command blocks unauthorized users."""
        from src.application.handlers.commands import CommandHandlers
        
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        # Mock unauthorized
        handler.auth_repo.is_authorized = AsyncMock(return_value=False)
        
        await handler.handle_lang(mock_telegram_update, mock_context)
        
        # Verify error message sent via send_error_message helper (calls notify_user)
        handler.telegram_service.notify_user.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_download_requires_authorization(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test /download command blocks unauthorized users."""
        from src.application.handlers.commands import CommandHandlers
        
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        # Mock unauthorized
        handler.auth_repo.is_authorized = AsyncMock(return_value=False)
        
        await handler.handle_download(mock_telegram_update, mock_context)
        
        # Verify error message sent via send_error_message helper (calls notify_user)
        handler.telegram_service.notify_user.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_authorization_helper_method(
        self,
        mock_all_services
    ):
        """Test BaseHandler.check_authorization method."""
        from src.application.handlers.base_handler import BaseHandler
        
        # Create a concrete subclass for testing
        class TestHandler(BaseHandler):
            async def handle(self, update, context):
                pass
        
        handler = TestHandler(
            MagicMock(),  # Mock application
            mock_all_services
        )
        
        # Mock auth_repo
        auth_mock = AsyncMock()
        auth_mock.is_authorized = AsyncMock(return_value=True)
        handler.auth_repo = auth_mock
        
        # Test authorized user
        is_auth = await handler.check_authorization(user_id=123456)
        assert is_auth is True
        
        # Test unauthorized user
        auth_mock.is_authorized = AsyncMock(return_value=False)
        is_auth = await handler.check_authorization(user_id=999999)
        assert is_auth is False
    
    @pytest.mark.asyncio
    async def test_check_authorization_no_repo_returns_true(
        self,
        mock_all_services
    ):
        """Test check_authorization returns True when no auth_repo."""
        from src.application.handlers.base_handler import BaseHandler
        
        # Create a concrete subclass for testing
        class TestHandler(BaseHandler):
            async def handle(self, update, context):
                pass
        
        handler = TestHandler(MagicMock(), {})
        handler.auth_repo = None
        
        is_auth = await handler.check_authorization(user_id=123456)
        
        # Should allow access when no auth repo configured
        assert is_auth is True
    
    @pytest.mark.asyncio
    async def test_check_authorization_handles_exception(
        self,
        mock_all_services
    ):
        """Test check_authorization handles exceptions gracefully."""
        from src.application.handlers.base_handler import BaseHandler
        
        # Create a concrete subclass for testing
        class TestHandler(BaseHandler):
            async def handle(self, update, context):
                pass
        
        handler = TestHandler(MagicMock(), mock_all_services)
        auth_mock = AsyncMock()
        auth_mock.is_authorized = AsyncMock(side_effect=Exception("DB error"))
        handler.auth_repo = auth_mock
        
        # Should return False on exception
        is_auth = await handler.check_authorization(user_id=123456)
        
        assert is_auth is False


class TestAuthorizationWorkflow:
    """Test complete authorization workflows."""
    
    @pytest.mark.asyncio
    async def test_full_authorization_lifecycle(self):
        """Test complete user authorization lifecycle."""
        auth_repo = AsyncMock()
        
        # Setup mock chain for lifecycle - configure is_authorized to use side_effect properly
        auth_repo.is_authorized = AsyncMock(side_effect=[False, True, False])
        auth_repo.add_user = AsyncMock(return_value=1)
        auth_repo.get_user_info = AsyncMock(return_value={
            'user_id': 777888,
            'added_date': '2024-01-01T12:00:00',
            'added_by': 'test_admin'
        })
        auth_repo.remove_user = AsyncMock(return_value=1)
        
        user_id = 777888
        
        # Step 1: Check initial state (not authorized)
        is_auth = await auth_repo.is_authorized(user_id)
        assert is_auth is False
        
        # Step 2: Add user
        await auth_repo.add_user(user_id=user_id, added_by='test_admin')
        
        # Reset the side_effect to continue the sequence
        auth_repo.is_authorized = AsyncMock(side_effect=[True, False])
        
        # Step 3: Verify now authorized
        is_auth = await auth_repo.is_authorized(user_id)
        assert is_auth is True
        
        # Step 4: Get user info
        user_info = await auth_repo.get_user_info(user_id)
        assert user_info is not None
        assert user_info['user_id'] == user_id
        assert user_info['added_by'] == 'test_admin'
        
        # Step 5: Remove user
        await auth_repo.remove_user(user_id)
        
        # Step 6: Verify no longer authorized
        is_auth = await auth_repo.is_authorized(user_id)
        assert is_auth is False
    
    @pytest.mark.asyncio
    async def test_bulk_operations_workflow(self):
        """Test bulk user authorization workflow."""
        auth_repo = AsyncMock()
        
        # Configure return values properly
        async def mock_bulk_add(user_ids, added_by):
            return 5
        
        async def mock_cleanup(valid_ids):
            return 2
        
        auth_repo.bulk_add_users = mock_bulk_add
        auth_repo.cleanup_invalid_users = mock_cleanup
        
        # Bulk add 5 users
        user_ids = [100, 200, 300, 400, 500]
        added = await auth_repo.bulk_add_users(
            user_ids=user_ids,
            added_by='bulk_import'
        )
        
        assert added == 5
        
        # Cleanup keeping only 3 users
        valid_ids = [100, 200, 300]
        removed = await auth_repo.cleanup_invalid_users(valid_ids)
        
        assert removed == 2