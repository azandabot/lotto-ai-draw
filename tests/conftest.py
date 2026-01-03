"""
Pytest fixtures and configuration for SA Lotto AI Predictor tests.
"""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Draw, Prediction, NumberStats
from config import GameConfig, GAMES


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_draw():
    """Create a sample Daily Lotto draw."""
    return Draw(
        game="daily_lotto",
        draw_number=1234,
        draw_date=datetime(2025, 12, 29, 21, 0, 0),
        main_numbers=[5, 12, 18, 25, 33],
        bonus_numbers=[]
    )


@pytest.fixture
def sample_powerball_draw():
    """Create a sample PowerBall draw with bonus number."""
    return Draw(
        game="powerball",
        draw_number=5678,
        draw_date=datetime(2025, 12, 27, 21, 0, 0),
        main_numbers=[7, 15, 23, 38, 45],
        bonus_numbers=[12]
    )


@pytest.fixture
def sample_lotto_draw():
    """Create a sample LOTTO draw."""
    return Draw(
        game="lotto",
        draw_number=2500,
        draw_date=datetime(2025, 12, 28, 21, 0, 0),
        main_numbers=[3, 14, 27, 35, 42, 51],
        bonus_numbers=[]
    )


@pytest.fixture
def sample_draws_list():
    """Create a list of sample Daily Lotto draws for testing."""
    base_date = datetime(2025, 12, 29)
    draws = []

    # Create 50 draws with varied numbers
    number_sets = [
        [1, 5, 12, 25, 33],
        [2, 8, 15, 22, 30],
        [3, 10, 18, 28, 35],
        [4, 11, 17, 24, 31],
        [5, 12, 19, 26, 34],
        [6, 13, 20, 27, 32],
        [7, 14, 21, 28, 36],
        [1, 8, 16, 23, 29],
        [2, 9, 17, 25, 33],
        [3, 11, 18, 26, 34],
    ]

    for i in range(50):
        draws.append(Draw(
            game="daily_lotto",
            draw_number=1000 + i,
            draw_date=base_date - timedelta(days=i),
            main_numbers=number_sets[i % len(number_sets)].copy(),
            bonus_numbers=[]
        ))

    return draws


@pytest.fixture
def sample_prediction():
    """Create a sample prediction."""
    return Prediction(
        game="daily_lotto",
        main_numbers=[5, 12, 18, 25, 33],
        bonus_numbers=[],
        reasoning="Test prediction based on hot numbers",
        confidence_note="For entertainment only"
    )


@pytest.fixture
def sample_powerball_prediction():
    """Create a sample PowerBall prediction with bonus."""
    return Prediction(
        game="powerball",
        main_numbers=[7, 15, 23, 38, 45],
        bonus_numbers=[12],
        reasoning="Test PowerBall prediction",
        confidence_note="For entertainment only"
    )


# =============================================================================
# Game Configuration Fixtures
# =============================================================================

@pytest.fixture
def daily_lotto_config():
    """Get Daily Lotto game configuration."""
    return GAMES["daily_lotto"]


@pytest.fixture
def powerball_config():
    """Get PowerBall game configuration."""
    return GAMES["powerball"]


@pytest.fixture
def lotto_config():
    """Get LOTTO game configuration."""
    return GAMES["lotto"]


@pytest.fixture
def all_game_configs():
    """Get all game configurations."""
    return GAMES


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for storage tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


# =============================================================================
# Number Stats Fixtures
# =============================================================================

@pytest.fixture
def hot_number_stats():
    """Create stats for a hot number."""
    return NumberStats(
        number=12,
        frequency=25,
        last_drawn=datetime.now() - timedelta(days=3),
        days_since_drawn=3
    )


@pytest.fixture
def cold_number_stats():
    """Create stats for a cold number."""
    return NumberStats(
        number=36,
        frequency=5,
        last_drawn=datetime.now() - timedelta(days=90),
        days_since_drawn=90
    )


# =============================================================================
# Helper Functions
# =============================================================================

@pytest.fixture
def create_draw():
    """Factory fixture to create draws with custom parameters."""
    def _create_draw(
        game="daily_lotto",
        draw_number=1,
        draw_date=None,
        main_numbers=None,
        bonus_numbers=None
    ):
        return Draw(
            game=game,
            draw_number=draw_number,
            draw_date=draw_date or datetime.now(),
            main_numbers=main_numbers or [1, 2, 3, 4, 5],
            bonus_numbers=bonus_numbers or []
        )
    return _create_draw


@pytest.fixture
def create_draws_with_pattern():
    """Factory fixture to create draws with specific number patterns."""
    def _create_draws(pattern_numbers, count=10):
        draws = []
        base_date = datetime.now()
        for i in range(count):
            draws.append(Draw(
                game="daily_lotto",
                draw_number=i,
                draw_date=base_date - timedelta(days=i),
                main_numbers=pattern_numbers.copy(),
                bonus_numbers=[]
            ))
        return draws
    return _create_draws
