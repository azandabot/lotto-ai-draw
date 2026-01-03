"""
Unit tests for config.py - Game configurations.
"""

import pytest
from config import GameConfig, GAMES, get_game, list_games


class TestGameConfig:
    """Tests for GameConfig dataclass."""

    def test_game_config_creation(self):
        """Test creating a GameConfig instance."""
        config = GameConfig(
            name="test_game",
            display_name="Test Game",
            main_numbers=5,
            main_range=(1, 36),
            draw_days=["Monday", "Friday"]
        )

        assert config.name == "test_game"
        assert config.display_name == "Test Game"
        assert config.main_numbers == 5
        assert config.main_range == (1, 36)
        assert config.bonus_numbers == 0
        assert config.bonus_range is None
        assert config.draw_days == ["Monday", "Friday"]

    def test_game_config_with_bonus(self):
        """Test GameConfig with bonus numbers (PowerBall style)."""
        config = GameConfig(
            name="powerball_test",
            display_name="PowerBall Test",
            main_numbers=5,
            main_range=(1, 50),
            bonus_numbers=1,
            bonus_range=(1, 20),
            draw_days=["Tuesday", "Friday"]
        )

        assert config.bonus_numbers == 1
        assert config.bonus_range == (1, 20)

    def test_game_config_default_draw_days(self):
        """Test that draw_days defaults to empty list."""
        config = GameConfig(
            name="test",
            display_name="Test",
            main_numbers=5,
            main_range=(1, 36)
        )

        assert config.draw_days == []


class TestGAMES:
    """Tests for the GAMES dictionary."""

    def test_games_contains_all_expected_games(self):
        """Test that all expected games are defined."""
        expected_games = [
            "lotto",
            "lotto_plus_1",
            "lotto_plus_2",
            "powerball",
            "powerball_plus",
            "daily_lotto"
        ]

        for game in expected_games:
            assert game in GAMES, f"Expected game '{game}' not found in GAMES"

    def test_daily_lotto_config(self, daily_lotto_config):
        """Test Daily Lotto configuration."""
        assert daily_lotto_config.name == "daily_lotto"
        assert daily_lotto_config.display_name == "Daily Lotto"
        assert daily_lotto_config.main_numbers == 5
        assert daily_lotto_config.main_range == (1, 36)
        assert daily_lotto_config.bonus_numbers == 0
        assert len(daily_lotto_config.draw_days) == 7  # Daily

    def test_lotto_config(self, lotto_config):
        """Test LOTTO configuration."""
        assert lotto_config.name == "lotto"
        assert lotto_config.display_name == "LOTTO"
        assert lotto_config.main_numbers == 6
        assert lotto_config.main_range == (1, 58)
        assert "Wednesday" in lotto_config.draw_days
        assert "Saturday" in lotto_config.draw_days

    def test_powerball_config(self, powerball_config):
        """Test PowerBall configuration."""
        assert powerball_config.name == "powerball"
        assert powerball_config.display_name == "PowerBall"
        assert powerball_config.main_numbers == 5
        assert powerball_config.main_range == (1, 50)
        assert powerball_config.bonus_numbers == 1
        assert powerball_config.bonus_range == (1, 20)
        assert "Tuesday" in powerball_config.draw_days
        assert "Friday" in powerball_config.draw_days


class TestGetGame:
    """Tests for get_game function."""

    def test_get_valid_game(self):
        """Test getting a valid game configuration."""
        config = get_game("daily_lotto")

        assert config is not None
        assert config.name == "daily_lotto"

    def test_get_invalid_game_raises_error(self):
        """Test that invalid game name raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            get_game("invalid_game")

        assert "Unknown game" in str(excinfo.value)
        assert "invalid_game" in str(excinfo.value)

    @pytest.mark.parametrize("game_name", [
        "lotto",
        "lotto_plus_1",
        "lotto_plus_2",
        "powerball",
        "powerball_plus",
        "daily_lotto"
    ])
    def test_get_all_games(self, game_name):
        """Test getting each game configuration."""
        config = get_game(game_name)
        assert config.name == game_name


class TestListGames:
    """Tests for list_games function."""

    def test_list_games_returns_list(self):
        """Test that list_games returns a list."""
        games = list_games()
        assert isinstance(games, list)

    def test_list_games_count(self):
        """Test that list_games returns correct count."""
        games = list_games()
        assert len(games) == 6

    def test_list_games_contains_game_configs(self):
        """Test that list_games returns GameConfig objects."""
        games = list_games()
        for game in games:
            assert isinstance(game, GameConfig)

    def test_list_games_contains_daily_lotto(self):
        """Test that list_games includes Daily Lotto."""
        games = list_games()
        game_names = [g.name for g in games]
        assert "daily_lotto" in game_names


class TestGameRanges:
    """Tests for game number ranges."""

    @pytest.mark.parametrize("game_name,expected_min,expected_max", [
        ("daily_lotto", 1, 36),
        ("lotto", 1, 58),
        ("lotto_plus_1", 1, 58),
        ("lotto_plus_2", 1, 58),
        ("powerball", 1, 50),
        ("powerball_plus", 1, 50),
    ])
    def test_main_number_ranges(self, game_name, expected_min, expected_max):
        """Test main number ranges for each game."""
        config = get_game(game_name)
        assert config.main_range[0] == expected_min
        assert config.main_range[1] == expected_max

    @pytest.mark.parametrize("game_name,expected_bonus_min,expected_bonus_max", [
        ("powerball", 1, 20),
        ("powerball_plus", 1, 20),
    ])
    def test_bonus_number_ranges(self, game_name, expected_bonus_min, expected_bonus_max):
        """Test bonus number ranges for PowerBall games."""
        config = get_game(game_name)
        assert config.bonus_range[0] == expected_bonus_min
        assert config.bonus_range[1] == expected_bonus_max
