"""
Unit Tests for Domain Entities

Tests for User, Video, and DownloadTask entities.
"""
import pytest
from datetime import datetime
from src.domain.entities.user import User
from src.domain.entities.video import Video, VideoFormat
from src.domain.entities.download_task import DownloadTask
from src.domain.value_objects.video_quality import VideoQuality
from src.domain.value_objects.download_status import DownloadStatus


class TestUser:
    """Test cases for User entity."""
    
    def test_create_user(self, mock_user_data):
        """Test user creation with valid data."""
        user = User(
            user_id=mock_user_data['user_id'],
            username=mock_user_data['username']
        )
        
        assert user.user_id == mock_user_data['user_id']
        assert user.username == mock_user_data['username']
        assert user.downloads_in_hour == 0
        assert user.last_video_url is None
    
    def test_user_can_download_within_limit(self):
        """Test rate limiting allows downloads under limit."""
        user = User(user_id=123, username='test')
        
        # Should allow when under limit
        assert user.can_download(limit_per_hour=10) is True
        
        # Increment to limit
        for _ in range(5):
            user.increment_downloads()
        
        # Should still allow (5 < 10)
        assert user.can_download(limit_per_hour=10) is True
    
    def test_user_blocked_when_over_limit(self):
        """Test rate limiting blocks downloads at/over limit."""
        user = User(user_id=123, username='test')
        
        # Increment to limit
        for _ in range(10):
            user.increment_downloads()
        
        # Should block at limit
        assert user.can_download(limit_per_hour=10) is False
    
    def test_user_update_username(self):
        """Test username update."""
        user = User(user_id=123, username='old_name')
        
        user.update_username('new_name')
        
        assert user.username == 'new_name'
    
    def test_user_increment_downloads(self):
        """Test download counter increment."""
        user = User(user_id=123, username='test')
        
        initial_count = user.downloads_in_hour
        
        user.increment_downloads()
        
        assert user.downloads_in_hour == initial_count + 1


class TestVideo:
    """Test cases for Video entity."""
    
    def test_create_video(self, mock_video_data):
        """Test video creation with valid data."""
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            duration=mock_video_data['duration']
        )
        
        assert video.video_id == mock_video_data['video_id']
        assert video.title == mock_video_data['title']
        assert video.uploader == mock_video_data['uploader']
        assert video.duration == mock_video_data['duration']
    
    def test_video_get_best_format_for_quality(self, mock_video_data):
        """Test format selection for specific quality."""
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            duration=mock_video_data['duration']
        )
        
        # Add some formats
        format_720 = VideoFormat(
            format_id='720',
            height=720,
            width=1280,
            ext='mp4',
            has_audio=True,
            has_video=True
        )
        
        format_1080 = VideoFormat(
            format_id='1080',
            height=1080,
            width=1920,
            ext='mp4',
            has_audio=True,
            has_video=True
        )
        
        video.formats = [format_720, format_1080]
        
        # Get best format for 720p
        best_format = video.get_best_format_for_quality('720')
        
        assert best_format is not None
        assert best_format.height == 720
    
    def test_video_available_qualities(self, mock_video_data):
        """Test available qualities extraction."""
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            duration=mock_video_data['duration']
        )
        
        # Add formats with different heights
        video.formats = [
            VideoFormat(format_id='1', height=360, ext='mp4'),
            VideoFormat(format_id='2', height=720, ext='mp4'),
            VideoFormat(format_id='3', height=1080, ext='mp4'),
        ]
        
        qualities = video.available_qualities
        
        assert len(qualities) > 0
        assert VideoQuality.P360 in qualities or VideoQuality.P720 in qualities


class TestVideoFormat:
    """Test cases for VideoFormat value object."""
    
    def test_create_video_format(self):
        """Test format creation."""
        fmt = VideoFormat(
            format_id='test',
            height=720,
            width=1280,
            ext='mp4'
        )
        
        assert fmt.height == 720
        assert fmt.width == 1280
        assert fmt.ext == 'mp4'
    
    def test_format_has_video(self):
        """Test video detection."""
        fmt_with_video = VideoFormat(
            format_id='test',
            height=720,
            has_video=True,
            has_audio=False
        )
        
        fmt_without_video = VideoFormat(
            format_id='test',
            has_video=False,
            has_audio=True
        )
        
        assert fmt_with_video.has_video() is True
        assert fmt_without_video.has_video() is False
    
    def test_format_has_audio(self):
        """Test audio detection."""
        fmt_with_audio = VideoFormat(
            format_id='test',
            has_video=False,
            has_audio=True
        )
        
        fmt_without_audio = VideoFormat(
            format_id='test',
            has_video=False,
            has_audio=False
        )
        
        assert fmt_with_audio.has_audio() is True
        assert fmt_without_audio.has_audio() is False


class TestDownloadTask:
    """Test cases for DownloadTask entity."""
    
    def test_create_download_task(self, mock_download_task_data):
        """Test task creation with valid data."""
        task = DownloadTask(
            chat_id=mock_download_task_data['chat_id'],
            user_id=mock_download_task_data['user_id'],
            username=mock_download_task_data['username'],
            video_id=mock_download_task_data['video_id'],
            url=mock_download_task_data['url'],
            quality=mock_download_task_data['quality']
        )
        
        assert task.chat_id == mock_download_task_data['chat_id']
        assert task.video_id == mock_download_task_data['video_id']
        assert task.quality == mock_download_task_data['quality']
        assert task.status == DownloadStatus.PENDING
        assert task.progress == 0
    
    def test_task_mark_started(self, mock_download_task_data):
        """Test marking task as started."""
        task = DownloadTask(**mock_download_task_data)
        
        task.mark_started()
        
        assert task.status == DownloadStatus.DOWNLOADING
        assert task.started_at is not None
    
    def test_task_mark_completed(self, mock_download_task_data):
        """Test marking task as completed."""
        task = DownloadTask(**mock_download_task_data)
        
        task.mark_completed()
        
        assert task.status == DownloadStatus.COMPLETED
        assert task.completed_at is not None
    
    def test_task_mark_failed(self, mock_download_task_data):
        """Test marking task as failed."""
        task = DownloadTask(**mock_download_task_data)
        
        error_msg = "Test error"
        task.mark_failed(error_msg)
        
        assert task.status == DownloadStatus.FAILED
        assert task.error_message == error_msg
    
    def test_task_update_progress(self, mock_download_task_data):
        """Test progress updates."""
        task = DownloadTask(**mock_download_task_data)
        
        task.update_progress(50)
        
        assert task.progress == 50
    
    def test_task_is_active(self, mock_download_task_data):
        """Test active status check."""
        task = DownloadTask(**mock_download_task_data)
        
        # Pending is active
        assert task.is_active() is True
        
        # Started is active
        task.mark_started()
        assert task.is_active() is True
        
        # Completed is not active
        task.mark_completed()
        assert task.is_active() is False
        
        # Failed is not active
        task.mark_failed("error")
        assert task.is_active() is False
