"""
Unit tests for models.py - Data models.
"""

import pytest
from datetime import datetime, timedelta
from models import Draw, Prediction, NumberStats


class TestDraw:
    """Tests for Draw dataclass."""

    def test_draw_creation(self, sample_draw):
        """Test creating a Draw instance."""
        assert sample_draw.game == "daily_lotto"
        assert sample_draw.draw_number == 1234
        assert sample_draw.main_numbers == [5, 12, 18, 25, 33]
        assert sample_draw.bonus_numbers == []

    def test_draw_with_bonus_numbers(self, sample_powerball_draw):
        """Test creating a Draw with bonus numbers."""
        assert sample_powerball_draw.game == "powerball"
        assert sample_powerball_draw.main_numbers == [7, 15, 23, 38, 45]
        assert sample_powerball_draw.bonus_numbers == [12]

    def test_draw_to_dict(self, sample_draw):
        """Test converting Draw to dictionary."""
        data = sample_draw.to_dict()

        assert data["game"] == "daily_lotto"
        assert data["draw_number"] == 1234
        assert data["main_numbers"] == [5, 12, 18, 25, 33]
        assert data["bonus_numbers"] == []
        assert "draw_date" in data

    def test_draw_from_dict(self):
        """Test creating Draw from dictionary."""
        data = {
            "game": "daily_lotto",
            "draw_number": 999,
            "draw_date": "2025-12-29T21:00:00",
            "main_numbers": [1, 2, 3, 4, 5],
            "bonus_numbers": []
        }

        draw = Draw.from_dict(data)

        assert draw.game == "daily_lotto"
        assert draw.draw_number == 999
        assert draw.main_numbers == [1, 2, 3, 4, 5]
        assert isinstance(draw.draw_date, datetime)

    def test_draw_from_dict_without_bonus(self):
        """Test creating Draw from dict without bonus_numbers key."""
        data = {
            "game": "daily_lotto",
            "draw_number": 1,
            "draw_date": "2025-12-29T21:00:00",
            "main_numbers": [1, 2, 3, 4, 5]
        }

        draw = Draw.from_dict(data)
        assert draw.bonus_numbers == []

    def test_draw_roundtrip(self, sample_draw):
        """Test that to_dict and from_dict are inverse operations."""
        data = sample_draw.to_dict()
        restored = Draw.from_dict(data)

        assert restored.game == sample_draw.game
        assert restored.draw_number == sample_draw.draw_number
        assert restored.main_numbers == sample_draw.main_numbers
        assert restored.bonus_numbers == sample_draw.bonus_numbers

    def test_format_numbers_daily_lotto(self, sample_draw):
        """Test formatting numbers for Daily Lotto."""
        formatted = sample_draw.format_numbers()

        assert "05" in formatted
        assert "12" in formatted
        assert "18" in formatted
        assert "25" in formatted
        assert "33" in formatted
        assert " - " in formatted
        assert "PB" not in formatted

    def test_format_numbers_powerball(self, sample_powerball_draw):
        """Test formatting numbers for PowerBall with bonus."""
        formatted = sample_powerball_draw.format_numbers()

        assert "07" in formatted
        assert "PB:" in formatted
        assert "12" in formatted

    def test_format_numbers_sorted(self):
        """Test that format_numbers sorts the numbers."""
        draw = Draw(
            game="daily_lotto",
            draw_number=1,
            draw_date=datetime.now(),
            main_numbers=[33, 5, 18, 12, 25],  # Unsorted
            bonus_numbers=[]
        )

        formatted = draw.format_numbers()
        # Should be sorted: 05 - 12 - 18 - 25 - 33
        assert formatted.index("05") < formatted.index("12")
        assert formatted.index("12") < formatted.index("18")


class TestPrediction:
    """Tests for Prediction dataclass."""

    def test_prediction_creation(self, sample_prediction):
        """Test creating a Prediction instance."""
        assert sample_prediction.game == "daily_lotto"
        assert sample_prediction.main_numbers == [5, 12, 18, 25, 33]
        assert sample_prediction.bonus_numbers == []
        assert "hot numbers" in sample_prediction.reasoning.lower()

    def test_prediction_with_bonus(self, sample_powerball_prediction):
        """Test creating PowerBall Prediction with bonus."""
        assert sample_powerball_prediction.game == "powerball"
        assert sample_powerball_prediction.bonus_numbers == [12]

    def test_prediction_has_generated_at(self, sample_prediction):
        """Test that prediction has generated_at timestamp."""
        assert isinstance(sample_prediction.generated_at, datetime)
        # Should be recent (within last minute)
        assert (datetime.now() - sample_prediction.generated_at).seconds < 60

    def test_prediction_format_numbers(self, sample_prediction):
        """Test formatting prediction numbers."""
        formatted = sample_prediction.format_numbers()

        assert "05" in formatted
        assert "33" in formatted
        assert " - " in formatted

    def test_prediction_format_numbers_with_bonus(self, sample_powerball_prediction):
        """Test formatting PowerBall prediction with bonus."""
        formatted = sample_powerball_prediction.format_numbers()

        assert "PB:" in formatted
        assert "12" in formatted

    def test_prediction_default_values(self):
        """Test Prediction default values."""
        pred = Prediction(
            game="daily_lotto",
            main_numbers=[1, 2, 3, 4, 5]
        )

        assert pred.bonus_numbers == []
        assert pred.reasoning == ""
        assert pred.confidence_note == ""


class TestNumberStats:
    """Tests for NumberStats dataclass."""

    def test_number_stats_creation(self, hot_number_stats):
        """Test creating NumberStats instance."""
        assert hot_number_stats.number == 12
        assert hot_number_stats.frequency == 25
        assert hot_number_stats.days_since_drawn == 3

    def test_is_hot_property(self, hot_number_stats):
        """Test is_hot property for hot number."""
        assert hot_number_stats.is_hot is True

    def test_is_cold_property(self, cold_number_stats):
        """Test is_cold property for cold number."""
        assert cold_number_stats.is_cold is True
        assert cold_number_stats.is_hot is False

    def test_is_hot_false_for_cold_number(self, cold_number_stats):
        """Test that cold numbers are not hot."""
        assert cold_number_stats.is_hot is False

    def test_is_cold_false_for_hot_number(self, hot_number_stats):
        """Test that hot numbers are not cold."""
        assert hot_number_stats.is_cold is False

    def test_is_hot_requires_recent_draw(self):
        """Test that is_hot requires recent draw (within 30 days)."""
        stats = NumberStats(
            number=15,
            frequency=50,
            last_drawn=datetime.now() - timedelta(days=45),
            days_since_drawn=45
        )
        assert stats.is_hot is False

    def test_is_cold_threshold(self):
        """Test is_cold threshold (60 days)."""
        # 59 days - not cold yet
        stats_59 = NumberStats(
            number=20,
            frequency=5,
            last_drawn=datetime.now() - timedelta(days=59),
            days_since_drawn=59
        )
        assert stats_59.is_cold is False

        # 61 days - cold
        stats_61 = NumberStats(
            number=20,
            frequency=5,
            last_drawn=datetime.now() - timedelta(days=61),
            days_since_drawn=61
        )
        assert stats_61.is_cold is True

    def test_number_stats_without_last_drawn(self):
        """Test NumberStats when number has never been drawn."""
        stats = NumberStats(
            number=36,
            frequency=0,
            last_drawn=None,
            days_since_drawn=None
        )

        assert stats.is_hot is False
        assert stats.is_cold is False  # None days_since_drawn


class TestDrawValidation:
    """Tests for Draw validation edge cases."""

    def test_draw_with_duplicate_numbers(self):
        """Test Draw allows duplicate numbers (validation elsewhere)."""
        # Note: The Draw model doesn't prevent duplicates - that's done elsewhere
        draw = Draw(
            game="daily_lotto",
            draw_number=1,
            draw_date=datetime.now(),
            main_numbers=[1, 1, 2, 3, 4],  # Duplicate 1
            bonus_numbers=[]
        )
        assert 1 in draw.main_numbers

    def test_draw_with_empty_main_numbers(self):
        """Test Draw with empty main numbers."""
        draw = Draw(
            game="daily_lotto",
            draw_number=1,
            draw_date=datetime.now(),
            main_numbers=[],
            bonus_numbers=[]
        )
        assert draw.main_numbers == []
        assert draw.format_numbers() == ""

    def test_draw_date_serialization(self, sample_draw):
        """Test that draw date is properly serialized to ISO format."""
        data = sample_draw.to_dict()
        assert "T" in data["draw_date"]  # ISO format contains T separator
