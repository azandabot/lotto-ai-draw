"""
Unit tests for play_tracker.py - Play and winnings tracking.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from models import Draw


class TestPlayTracker:
    """Tests for PlayTracker class."""

    @pytest.fixture
    def temp_tracker(self, tmp_path):
        """Create a PlayTracker with temporary data directory."""
        from play_tracker import PlayTracker

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        tracker = PlayTracker(data_dir=str(data_dir))
        return tracker

    def test_tracker_initialization(self, temp_tracker):
        """Test PlayTracker initialization."""
        assert temp_tracker.sessions == []

    def test_record_play(self, temp_tracker):
        """Test recording a play session."""
        tickets = [[1, 5, 12, 25, 33], [2, 8, 15, 22, 30]]
        session_id = temp_tracker.record_play(
            game="daily_lotto",
            tickets=tickets,
            total_cost=6.00
        )

        assert session_id is not None
        assert "daily_lotto" in session_id
        assert len(temp_tracker.sessions) == 1

    def test_record_play_saves_to_file(self, temp_tracker):
        """Test that recording a play saves to file."""
        tickets = [[1, 5, 12, 25, 33]]
        temp_tracker.record_play(
            game="daily_lotto",
            tickets=tickets,
            total_cost=3.00
        )

        tracker_file = Path(temp_tracker.tracker_file)
        assert tracker_file.exists()

    def test_record_play_with_bonus_numbers(self, temp_tracker):
        """Test recording PowerBall play with bonus numbers."""
        tickets = [[1, 10, 20, 30, 40]]
        bonus_numbers = [5]

        session_id = temp_tracker.record_play(
            game="powerball",
            tickets=tickets,
            total_cost=5.00,
            bonus_numbers=bonus_numbers
        )

        assert session_id is not None
        session = temp_tracker.sessions[0]
        assert session.tickets[0].get('bonus_number') == 5

    def test_get_stats_empty(self, temp_tracker):
        """Test getting stats with no plays."""
        from play_tracker import TrackerStats

        stats = temp_tracker.get_stats()

        assert isinstance(stats, TrackerStats)
        assert stats.total_played == 0
        assert stats.total_won == 0
        assert stats.total_tickets == 0

    def test_get_stats_with_plays(self, temp_tracker):
        """Test getting stats after plays."""
        # Record some plays
        temp_tracker.record_play(
            game="daily_lotto",
            tickets=[[1, 5, 12, 25, 33], [2, 8, 15, 22, 30]],
            total_cost=6.00
        )
        temp_tracker.record_play(
            game="daily_lotto",
            tickets=[[3, 10, 18, 28, 35]],
            total_cost=3.00
        )

        stats = temp_tracker.get_stats()

        assert stats.total_played == 9.00  # 6 + 3
        assert stats.total_tickets == 3
        assert stats.total_sessions == 2

    def test_get_recent_plays(self, temp_tracker):
        """Test getting recent plays."""
        # Record multiple plays
        for i in range(7):
            temp_tracker.record_play(
                game="daily_lotto",
                tickets=[[1, 2, 3, 4, 5]],
                total_cost=3.00
            )

        recent = temp_tracker.get_recent_plays(limit=5)

        assert len(recent) == 5

    def test_get_recent_plays_empty(self, temp_tracker):
        """Test getting recent plays when none exist."""
        recent = temp_tracker.get_recent_plays()
        assert recent == []

    def test_add_manual_play(self, temp_tracker):
        """Test adding a manual play entry."""
        session_id = temp_tracker.add_manual_play(
            game="daily_lotto",
            total_cost=50.00,
            num_tickets=10
        )

        assert session_id is not None
        assert "manual" in session_id

        stats = temp_tracker.get_stats()
        assert stats.total_played == 50.00
        assert stats.total_tickets == 10

    def test_add_manual_win(self, temp_tracker):
        """Test adding a manual win."""
        # First add a play
        temp_tracker.record_play(
            game="daily_lotto",
            tickets=[[1, 5, 12, 25, 33]],
            total_cost=3.00
        )

        # Then add a win
        result = temp_tracker.add_manual_win("daily_lotto", 50.00)

        assert result is True

        stats = temp_tracker.get_stats()
        assert stats.total_won == 50.00

    def test_add_manual_win_no_session(self, temp_tracker):
        """Test adding a manual win with no existing session."""
        result = temp_tracker.add_manual_win("daily_lotto", 100.00)

        assert result is True

        stats = temp_tracker.get_stats()
        assert stats.total_won == 100.00

    def test_profit_loss_calculation(self, temp_tracker):
        """Test profit/loss calculation."""
        # Play R50
        temp_tracker.record_play(
            game="daily_lotto",
            tickets=[[1, 2, 3, 4, 5]] * 10,
            total_cost=50.00
        )

        # Win R75
        temp_tracker.add_manual_win("daily_lotto", 75.00)

        stats = temp_tracker.get_stats()

        assert stats.profit_loss == 25.00  # 75 - 50

    def test_data_persistence(self, temp_tracker):
        """Test that data persists across tracker instances."""
        from play_tracker import PlayTracker

        # Record a play
        temp_tracker.record_play(
            game="daily_lotto",
            tickets=[[1, 5, 12, 25, 33]],
            total_cost=3.00
        )

        # Create new tracker with same data directory
        new_tracker = PlayTracker(data_dir=temp_tracker.data_dir)

        assert len(new_tracker.sessions) == 1


class TestPrizeStructure:
    """Tests for prize structure constants."""

    def test_daily_lotto_prizes(self):
        """Test Daily Lotto prize structure."""
        from play_tracker import PRIZE_STRUCTURE

        prizes = PRIZE_STRUCTURE['daily_lotto']

        assert prizes[5] == 'JACKPOT'
        assert prizes[4] == 350
        assert prizes[3] == 50
        assert prizes[2] == 15
        assert prizes[1] == 0
        assert prizes[0] == 0

    def test_powerball_prizes(self):
        """Test PowerBall prize structure."""
        from play_tracker import PRIZE_STRUCTURE

        prizes = PRIZE_STRUCTURE['powerball']

        assert prizes['5+1'] == 'JACKPOT'
        assert prizes['5+0'] == 500000
        assert prizes['0+1'] == 5
        assert prizes['0+0'] == 0


class TestWinningsCalculation:
    """Tests for winnings calculation."""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a PlayTracker with temporary data directory."""
        from play_tracker import PlayTracker

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        return PlayTracker(data_dir=str(data_dir))

    def test_calculate_winnings_3_match(self, tracker):
        """Test winnings for 3 matches."""
        winnings = tracker._calculate_winnings("daily_lotto", 3)
        assert winnings == 50

    def test_calculate_winnings_4_match(self, tracker):
        """Test winnings for 4 matches."""
        winnings = tracker._calculate_winnings("daily_lotto", 4)
        assert winnings == 350

    def test_calculate_winnings_jackpot(self, tracker):
        """Test winnings for jackpot (5 matches)."""
        from play_tracker import ESTIMATED_JACKPOTS

        winnings = tracker._calculate_winnings("daily_lotto", 5)
        assert winnings == ESTIMATED_JACKPOTS['daily_lotto']

    def test_calculate_winnings_no_match(self, tracker):
        """Test winnings for no matches."""
        winnings = tracker._calculate_winnings("daily_lotto", 0)
        assert winnings == 0

    def test_calculate_winnings_powerball_with_bonus(self, tracker):
        """Test PowerBall winnings with bonus match."""
        winnings = tracker._calculate_winnings("powerball", 3, bonus_match=True)
        assert winnings == 100  # 3+1


class TestTrackerStats:
    """Tests for TrackerStats dataclass."""

    def test_tracker_stats_creation(self):
        """Test creating TrackerStats instance."""
        from play_tracker import TrackerStats

        stats = TrackerStats(
            total_played=100.00,
            total_won=150.00,
            total_tickets=20,
            total_sessions=4,
            best_match=4,
            jackpots_won=0,
            win_rate=15.0,
            profit_loss=50.00,
            games_played={"daily_lotto": 15, "powerball": 5},
            streak=2
        )

        assert stats.total_played == 100.00
        assert stats.total_won == 150.00
        assert stats.profit_loss == 50.00
        assert stats.win_rate == 15.0


class TestPlaySession:
    """Tests for PlaySession dataclass."""

    def test_play_session_creation(self):
        """Test creating PlaySession instance."""
        from play_tracker import PlaySession

        session = PlaySession(
            session_id="daily_lotto_20251229_120000",
            game="daily_lotto",
            played_at="2025-12-29T12:00:00",
            draw_date="2025-12-29",
            tickets=[{"numbers": [1, 2, 3, 4, 5], "matches": 0}],
            total_cost=3.00,
            checked=False,
            total_matches={},
            total_winnings=0.0
        )

        assert session.game == "daily_lotto"
        assert session.total_cost == 3.00
        assert session.checked is False


class TestFormatStatsBanner:
    """Tests for stats banner formatting."""

    def test_format_stats_banner_profit(self):
        """Test banner formatting with profit."""
        from play_tracker import TrackerStats, format_stats_banner

        stats = TrackerStats(
            total_played=100.00,
            total_won=150.00,
            total_tickets=20,
            total_sessions=4,
            best_match=4,
            jackpots_won=0,
            win_rate=15.0,
            profit_loss=50.00,
            games_played={},
            streak=0
        )

        banner = format_stats_banner(stats)

        assert "R100" in banner or "100" in banner
        assert "R150" in banner or "150" in banner
        assert "+R50" in banner or "+50" in banner or "green" in banner

    def test_format_stats_banner_loss(self):
        """Test banner formatting with loss."""
        from play_tracker import TrackerStats, format_stats_banner

        stats = TrackerStats(
            total_played=100.00,
            total_won=25.00,
            total_tickets=20,
            total_sessions=4,
            best_match=2,
            jackpots_won=0,
            win_rate=5.0,
            profit_loss=-75.00,
            games_played={},
            streak=0
        )

        banner = format_stats_banner(stats)

        assert "R100" in banner or "100" in banner
        assert "red" in banner  # Loss should be red


class TestGetTracker:
    """Tests for get_tracker function."""

    def test_get_tracker_returns_instance(self):
        """Test that get_tracker returns a PlayTracker instance."""
        from play_tracker import get_tracker, PlayTracker

        tracker = get_tracker()

        assert isinstance(tracker, PlayTracker)
