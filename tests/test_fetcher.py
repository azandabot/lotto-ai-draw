"""
Unit tests for fetcher.py - Web scraping and data fetching.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from models import Draw


class TestCaching:
    """Tests for caching functionality."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path, monkeypatch):
        """Set up temporary cache directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        import fetcher
        monkeypatch.setattr(fetcher, "CACHE_DIR", cache_dir)

        return cache_dir

    def test_cache_path_generation(self, temp_cache_dir):
        """Test cache path is generated from URL hash."""
        from fetcher import _get_cache_path

        path = _get_cache_path("https://example.com/test")

        assert path.parent == temp_cache_dir
        assert path.suffix == ".json"

    def test_cache_path_consistent(self, temp_cache_dir):
        """Test same URL always generates same cache path."""
        from fetcher import _get_cache_path

        url = "https://example.com/test"
        path1 = _get_cache_path(url)
        path2 = _get_cache_path(url)

        assert path1 == path2

    def test_cache_path_different_urls(self, temp_cache_dir):
        """Test different URLs generate different cache paths."""
        from fetcher import _get_cache_path

        path1 = _get_cache_path("https://example.com/test1")
        path2 = _get_cache_path("https://example.com/test2")

        assert path1 != path2

    def test_clear_cache(self, temp_cache_dir):
        """Test clearing cache."""
        from fetcher import clear_cache

        # Create some cache files
        (temp_cache_dir / "file1.json").write_text("{}")
        (temp_cache_dir / "file2.json").write_text("{}")

        count = clear_cache()

        assert count == 2
        assert list(temp_cache_dir.glob("*.json")) == []


class TestFetchError:
    """Tests for FetchError exception."""

    def test_fetch_error_creation(self):
        """Test creating FetchError."""
        from fetcher import FetchError

        error = FetchError("Test error message")

        assert str(error) == "Test error message"

    def test_fetch_error_inheritance(self):
        """Test FetchError is an Exception."""
        from fetcher import FetchError

        assert issubclass(FetchError, Exception)


class TestGameConfig:
    """Tests for game configuration in fetcher."""

    def test_game_config_contains_all_games(self):
        """Test GAME_CONFIG contains all games."""
        from fetcher import GAME_CONFIG

        expected_games = [
            "lotto",
            "lotto_plus_1",
            "lotto_plus_2",
            "powerball",
            "powerball_plus",
            "daily_lotto"
        ]

        for game in expected_games:
            assert game in GAME_CONFIG

    def test_daily_lotto_config(self):
        """Test Daily Lotto configuration."""
        from fetcher import GAME_CONFIG

        config = GAME_CONFIG["daily_lotto"]

        assert config["url"] == "/daily-lotto/results"
        assert config["main_ball_class"] == "daily-lotto-ball"
        assert config["bonus_ball_class"] is None

    def test_powerball_config(self):
        """Test PowerBall configuration."""
        from fetcher import GAME_CONFIG

        config = GAME_CONFIG["powerball"]

        assert config["url"] == "/powerball/results"
        assert config["main_ball_class"] == "powerball-ball"
        assert config["bonus_ball_class"] == "powerball-powerball"


class TestMonthMap:
    """Tests for month name mapping."""

    def test_month_map_complete(self):
        """Test MONTH_MAP has all months."""
        from fetcher import MONTH_MAP

        assert len(MONTH_MAP) == 12

        assert MONTH_MAP['january'] == 1
        assert MONTH_MAP['december'] == 12

    def test_month_map_lowercase(self):
        """Test MONTH_MAP uses lowercase keys."""
        from fetcher import MONTH_MAP

        for month in MONTH_MAP.keys():
            assert month == month.lower()


class TestFetchResultsSync:
    """Tests for synchronous fetch wrapper."""

    def test_fetch_results_sync_invalid_game(self):
        """Test fetch_results_sync with invalid game."""
        from fetcher import fetch_results_sync

        with pytest.raises(ValueError):
            fetch_results_sync("invalid_game")


class TestFetchResultsForGame:
    """Tests for fetch_results_for_game function."""

    def test_fetch_results_sync_invalid_game(self):
        """Test fetching results for invalid game (sync wrapper)."""
        from fetcher import fetch_results_sync

        with pytest.raises(ValueError) as excinfo:
            fetch_results_sync("invalid_game")

        assert "Unknown game" in str(excinfo.value)


class TestExtendedHistory:
    """Tests for extended history fetching."""

    def test_archive_years_defined(self):
        """Test ARCHIVE_YEARS is defined."""
        from fetcher import ARCHIVE_YEARS

        assert isinstance(ARCHIVE_YEARS, list)
        assert len(ARCHIVE_YEARS) >= 2
        assert 2024 in ARCHIVE_YEARS or 2025 in ARCHIVE_YEARS


class TestFetchWithRetry:
    """Tests for fetch_with_retry function."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path, monkeypatch):
        """Set up temporary cache directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        import fetcher
        monkeypatch.setattr(fetcher, "CACHE_DIR", cache_dir)

        return cache_dir

    def test_cache_set_and_get(self, temp_cache_dir):
        """Test that cache set and get work correctly."""
        from fetcher import _set_cached, _get_cached

        url = "https://example.com/test"
        content = "<html>Test Content</html>"

        # Set cached content
        _set_cached(url, content)

        # Verify cache hit
        cached = _get_cached(url)
        assert cached == content


class TestDrawParsing:
    """Tests for draw parsing from HTML."""

    def test_parse_valid_numbers(self):
        """Test parsing valid lottery numbers."""
        # This would require mocking the HTML structure
        # Basic test to ensure module loads correctly
        from fetcher import Draw

        draw = Draw(
            game="daily_lotto",
            draw_number=1234,
            draw_date=datetime.now(),
            main_numbers=[1, 5, 12, 25, 33],
            bonus_numbers=[]
        )

        assert len(draw.main_numbers) == 5


class TestFallbackSource:
    """Tests for fallback data source."""

    def test_fallback_urls_defined(self):
        """Test fallback URLs are defined for all games."""
        # The fallback URLs are defined in _fetch_from_fallback
        # This is a basic sanity check
        from fetcher import _fetch_from_fallback

        assert callable(_fetch_from_fallback)


class TestExtendedHistorySync:
    """Tests for synchronous extended history wrapper."""

    def test_fetch_extended_history_sync_exists(self):
        """Test fetch_extended_history_sync function exists."""
        from fetcher import fetch_extended_history_sync

        assert callable(fetch_extended_history_sync)


class TestHTTPConfiguration:
    """Tests for HTTP configuration constants."""

    def test_timeout_reasonable(self):
        """Test timeout is reasonable."""
        from fetcher import DEFAULT_TIMEOUT

        assert 10 <= DEFAULT_TIMEOUT <= 60

    def test_max_retries_reasonable(self):
        """Test max retries is reasonable."""
        from fetcher import MAX_RETRIES

        assert 1 <= MAX_RETRIES <= 5

    def test_cache_ttl_reasonable(self):
        """Test cache TTL is reasonable."""
        from fetcher import CACHE_TTL_HOURS

        assert 0.5 <= CACHE_TTL_HOURS <= 24

    def test_base_url_defined(self):
        """Test base URL is defined."""
        from fetcher import LOTTERY_CO_ZA_BASE

        assert "lottery.co.za" in LOTTERY_CO_ZA_BASE
        assert LOTTERY_CO_ZA_BASE.startswith("https://")


class TestFetchAllGames:
    """Tests for fetch_all_games function."""

    def test_fetch_all_games_exists(self):
        """Test fetch_all_games function exists."""
        from fetcher import fetch_all_games

        assert callable(fetch_all_games)
        assert asyncio.iscoroutinefunction(fetch_all_games)
