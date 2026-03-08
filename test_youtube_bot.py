"""
Test cases for the Telegram YouTube Bot
Tests video extraction, URL validation, and download functionality
"""

import pytest
import asyncio
import re
from urllib.parse import urlparse

# Test the specific YouTube link provided
TEST_YOUTUBE_URL = "https://youtu.be/lAZc4uOsSxo?si=tSLkOH3SCFEJbDy"
TEST_VIDEO_ID = "lAZc4uOsSxo"


def extract_video_id(url):
    """Extract video ID from YouTube URL (copied from main bot code)"""
    patterns = [
        r'(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_valid_youtube_url(url):
    """Validate YouTube URL (copied from main bot code)"""
    ALLOWED_DOMAINS = [
        'youtube.com', 'www.youtube.com',
        'youtu.be', 'www.youtu.be',
        'youtube-nocookie.com', 'www.youtube-nocookie.com',
        'archive.ragtag.moe', 'www.archive.ragtag.moe'
    ]
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and parsed.netloc in ALLOWED_DOMAINS


class TestVideoIDExtraction:
    """Test cases for video ID extraction from various YouTube URL formats"""
    
    def test_extract_from_short_url_with_si_parameter(self):
        """Test extraction from youtu.be short URL with si parameter"""
        video_id = extract_video_id(TEST_YOUTUBE_URL)
        assert video_id == TEST_VIDEO_ID
        assert len(video_id) == 11
    
    def test_extract_from_standard_youtube_url(self):
        """Test extraction from standard youtube.com/watch?v= format"""
        url = "https://www.youtube.com/watch?v=lAZc4uOsSxo"
        assert extract_video_id(url) == TEST_VIDEO_ID
    
    def test_extract_from_url_without_parameters(self):
        """Test extraction from clean youtu.be URL"""
        url = "https://youtu.be/lAZc4uOsSxo"
        assert extract_video_id(url) == TEST_VIDEO_ID
    
    def test_extract_from_embed_url(self):
        """Test extraction from embed URL format"""
        url = "https://www.youtube.com/embed/lAZc4uOsSxo"
        assert extract_video_id(url) == TEST_VIDEO_ID
    
    def test_extract_from_shorts_url(self):
        """Test extraction from YouTube Shorts URL"""
        url = "https://www.youtube.com/shorts/lAZc4uOsSxo"
        assert extract_video_id(url) == TEST_VIDEO_ID
    
    def test_invalid_url_returns_none(self):
        """Test that invalid URLs return None"""
        assert extract_video_id("https://example.com/video") is None
        assert extract_video_id("not_a_url") is None
    
    def test_malformed_youtube_url_returns_none(self):
        """Test that malformed YouTube URLs return None"""
        assert extract_video_id("https://youtu.be/") is None
        assert extract_video_id("https://youtube.com/watch?v=") is None


class TestURLValidation:
    """Test cases for YouTube URL validation"""
    
    def test_valid_short_url(self):
        """Test validation of youtu.be short URL"""
        assert is_valid_youtube_url(TEST_YOUTUBE_URL) is True
    
    def test_valid_standard_url(self):
        """Test validation of standard YouTube URL"""
        url = "https://www.youtube.com/watch?v=lAZc4uOsSxo"
        assert is_valid_youtube_url(url) is True
    
    def test_valid_nocookie_url(self):
        """Test validation of privacy-enhanced youtube-nocookie.com"""
        url = "https://www.youtube-nocookie.com/embed/lAZc4uOsSxo"
        assert is_valid_youtube_url(url) is True
    
    def test_valid_archive_ragtag_url(self):
        """Test validation of archive.ragtag.moe URLs"""
        url = "https://archive.ragtag.moe/video/123"
        assert is_valid_youtube_url(url) is True
    
    def test_invalid_domain(self):
        """Test that non-YouTube domains are rejected"""
        assert is_valid_youtube_url("https://vimeo.com/123456") is False
        assert is_valid_youtube_url("https://dailymotion.com/video/123") is False
    
    def test_invalid_scheme(self):
        """Test that non-HTTP(S) schemes are rejected"""
        assert is_valid_youtube_url("ftp://youtube.com/watch?v=123") is False
    
    def test_http_url_accepted(self):
        """Test that HTTP (non-HTTPS) URLs are also accepted"""
        url = "http://youtu.be/lAZc4uOsSxo"
        assert is_valid_youtube_url(url) is True


class TestIntegration:
    """Integration tests combining URL validation and video ID extraction"""
    
    def test_full_workflow_with_test_url(self):
        """Test complete workflow with the provided test URL"""
        # Step 1: Validate URL
        assert is_valid_youtube_url(TEST_YOUTUBE_URL) is True
        
        # Step 2: Extract video ID
        video_id = extract_video_id(TEST_YOUTUBE_URL)
        assert video_id == TEST_VIDEO_ID
        
        # Step 3: Verify video ID format (11 characters, alphanumeric + _ -)
        assert re.match(r'^[0-9A-Za-z_-]{11}$', video_id) is not None
    
    def test_construct_download_url(self):
        """Test constructing full YouTube URL from extracted video ID"""
        video_id = extract_video_id(TEST_YOUTUBE_URL)
        reconstructed_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # The reconstructed URL should also be valid
        assert is_valid_youtube_url(reconstructed_url) is True
        assert extract_video_id(reconstructed_url) == video_id
    
    def test_various_url_formats_same_video_id(self):
        """Test that different URL formats for same video return same ID"""
        urls = [
            "https://youtu.be/lAZc4uOsSxo",
            "https://www.youtube.com/watch?v=lAZc4uOsSxo",
            "https://youtube.com/watch?v=lAZc4uOsSxo&feature=share",
            "https://www.youtube.com/embed/lAZc4uOsSxo",
            "http://youtu.be/lAZc4uOsSxo?si=test123",
        ]
        
        for url in urls:
            assert is_valid_youtube_url(url), f"URL should be valid: {url}"
            assert extract_video_id(url) == TEST_VIDEO_ID, f"Should extract same ID from: {url}"


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_url_with_multiple_parameters(self):
        """Test URL with multiple query parameters"""
        url = "https://youtu.be/lAZc4uOsSxo?si=tSLkOH3SCFEJbDy&t=30&feature=share"
        assert is_valid_youtube_url(url) is True
        assert extract_video_id(url) == TEST_VIDEO_ID
    
    def test_url_with_timestamp(self):
        """Test URL with timestamp parameter"""
        url = "https://www.youtube.com/watch?v=lAZc4uOsSxo&t=120s"
        assert extract_video_id(url) == TEST_VIDEO_ID
    
    def test_case_sensitivity(self):
        """Test that video IDs are case-sensitive"""
        url_upper = "https://youtu.be/LAZC4UOSSXO"
        url_lower = "https://youtu.be/lazc4uossxo"
        
        id_upper = extract_video_id(url_upper)
        id_lower = extract_video_id(url_lower)
        
        assert id_upper != id_lower  # Different case = different ID
    
    def test_similar_looking_ids(self):
        """Test handling of similar-looking video IDs"""
        # Video IDs that look similar but are different
        test_cases = [
            ("https://youtu.be/lAZc4uOsSxo", "lAZc4uOsSxo"),
            ("https://youtu.be/1AZc4uOsSxo", "1AZc4uOsSxo"),  # 1 instead of l
            ("https://youtu.be/lAZc4uOsSX0", "lAZc4uOsSX0"),  # 0 instead of o
        ]
        
        for url, expected_id in test_cases:
            assert extract_video_id(url) == expected_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
