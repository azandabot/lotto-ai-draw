"""
Unit tests for storage.py - Local JSON storage.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from models import Draw


class TestStorageFunctions:
    """Tests for storage module functions."""

    @pytest.fixture(autouse=True)
    def setup_temp_storage(self, tmp_path, monkeypatch):
        """Set up temporary storage directory for each test."""
        self.temp_data_dir = tmp_path / "data"
        self.temp_data_dir.mkdir()

        # Patch the DATA_DIR in storage module
        import storage
        monkeypatch.setattr(storage, "DATA_DIR", self.temp_data_dir)

        yield

    def test_save_and_load_draws(self, sample_draw):
        """Test saving and loading draws."""
        import storage

        # Save the draw
        storage.save_draws("daily_lotto", [sample_draw])

        # Load it back
        loaded = storage.load_draws("daily_lotto")

        assert len(loaded) == 1
        assert loaded[0].game == sample_draw.game
        assert loaded[0].draw_number == sample_draw.draw_number
        assert loaded[0].main_numbers == sample_draw.main_numbers

    def test_save_multiple_draws(self, sample_draws_list):
        """Test saving multiple draws."""
        import storage

        # Save all draws
        storage.save_draws("daily_lotto", sample_draws_list[:10])

        # Load them back
        loaded = storage.load_draws("daily_lotto")

        assert len(loaded) == 10

    def test_load_draws_with_limit(self, sample_draws_list):
        """Test loading draws with limit parameter."""
        import storage

        storage.save_draws("daily_lotto", sample_draws_list)
        loaded = storage.load_draws("daily_lotto", limit=5)

        assert len(loaded) == 5

    def test_load_draws_empty_game(self):
        """Test loading draws for a game with no data."""
        import storage

        loaded = storage.load_draws("nonexistent_game")
        assert loaded == []

    def test_save_draws_creates_directory(self, tmp_path, monkeypatch):
        """Test that save_draws creates data directory if it doesn't exist."""
        import storage

        new_data_dir = tmp_path / "new_data_dir"
        monkeypatch.setattr(storage, "DATA_DIR", new_data_dir)

        draw = Draw(
            game="test",
            draw_number=1,
            draw_date=datetime.now(),
            main_numbers=[1, 2, 3, 4, 5],
            bonus_numbers=[]
        )

        storage.save_draws("test", [draw])

        assert new_data_dir.exists()

    def test_save_draws_deduplication_by_date(self, sample_draw):
        """Test that duplicate draws (same date) are not saved twice."""
        import storage

        # Save the same draw twice
        storage.save_draws("daily_lotto", [sample_draw])
        storage.save_draws("daily_lotto", [sample_draw])

        loaded = storage.load_draws("daily_lotto")
        assert len(loaded) == 1

    def test_save_draws_different_dates(self, create_draw):
        """Test that draws with different dates are both saved."""
        import storage

        draw1 = create_draw(draw_date=datetime(2025, 12, 29))
        draw2 = create_draw(draw_date=datetime(2025, 12, 28))

        storage.save_draws("daily_lotto", [draw1])
        storage.save_draws("daily_lotto", [draw2])

        loaded = storage.load_draws("daily_lotto")
        assert len(loaded) == 2

    def test_draws_sorted_by_date_newest_first(self, create_draw):
        """Test that draws are sorted by date (newest first)."""
        import storage

        # Create draws with different dates (older first)
        old_draw = create_draw(draw_date=datetime(2025, 12, 1))
        new_draw = create_draw(draw_date=datetime(2025, 12, 29))

        storage.save_draws("daily_lotto", [old_draw, new_draw])

        loaded = storage.load_draws("daily_lotto")

        assert loaded[0].draw_date > loaded[1].draw_date

    def test_get_latest_draw(self, sample_draws_list):
        """Test getting the most recent draw."""
        import storage

        storage.save_draws("daily_lotto", sample_draws_list)
        latest = storage.get_latest_draw("daily_lotto")

        assert latest is not None
        # The first draw in sample_draws_list has the most recent date
        assert latest.draw_number == sample_draws_list[0].draw_number

    def test_get_latest_draw_empty(self):
        """Test get_latest_draw when no draws exist."""
        import storage

        latest = storage.get_latest_draw("nonexistent_game")
        assert latest is None

    def test_get_draw_count(self, sample_draws_list):
        """Test counting stored draws."""
        import storage

        storage.save_draws("daily_lotto", sample_draws_list[:20])
        count = storage.get_draw_count("daily_lotto")

        assert count == 20

    def test_get_draw_count_empty(self):
        """Test count when no draws exist."""
        import storage

        count = storage.get_draw_count("nonexistent_game")
        assert count == 0

    def test_clear_draws(self, sample_draws_list):
        """Test clearing all draws for a game."""
        import storage

        storage.save_draws("daily_lotto", sample_draws_list)
        assert storage.get_draw_count("daily_lotto") > 0

        storage.clear_draws("daily_lotto")

        assert storage.get_draw_count("daily_lotto") == 0

    def test_clear_draws_nonexistent_game(self):
        """Test clearing draws for a game that doesn't exist."""
        import storage

        # Should not raise an error
        storage.clear_draws("nonexistent_game")

    def test_get_all_stored_games(self, sample_draw, sample_powerball_draw):
        """Test getting list of games with stored data."""
        import storage

        storage.save_draws("daily_lotto", [sample_draw])
        storage.save_draws("powerball", [sample_powerball_draw])

        games = storage.get_all_stored_games()

        assert "daily_lotto" in games
        assert "powerball" in games

    def test_get_all_stored_games_empty(self):
        """Test get_all_stored_games when no data exists."""
        import storage

        games = storage.get_all_stored_games()
        assert games == []

    def test_storage_file_format(self, sample_draw):
        """Test that storage file is valid JSON."""
        import storage

        storage.save_draws("daily_lotto", [sample_draw])

        file_path = self.temp_data_dir / "daily_lotto.json"
        assert file_path.exists()

        with open(file_path, "r") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["game"] == "daily_lotto"

    def test_storage_preserves_all_fields(self, sample_powerball_draw):
        """Test that all draw fields are preserved in storage."""
        import storage

        storage.save_draws("powerball", [sample_powerball_draw])
        loaded = storage.load_draws("powerball")

        assert len(loaded) == 1
        loaded_draw = loaded[0]

        assert loaded_draw.game == sample_powerball_draw.game
        assert loaded_draw.draw_number == sample_powerball_draw.draw_number
        assert loaded_draw.main_numbers == sample_powerball_draw.main_numbers
        assert loaded_draw.bonus_numbers == sample_powerball_draw.bonus_numbers


class TestStorageEdgeCases:
    """Edge case tests for storage module."""

    @pytest.fixture(autouse=True)
    def setup_temp_storage(self, tmp_path, monkeypatch):
        """Set up temporary storage directory."""
        self.temp_data_dir = tmp_path / "data"
        self.temp_data_dir.mkdir()

        import storage
        monkeypatch.setattr(storage, "DATA_DIR", self.temp_data_dir)

    def test_load_corrupted_json(self):
        """Test handling of corrupted JSON file."""
        import storage

        # Create a corrupted JSON file
        file_path = self.temp_data_dir / "corrupted.json"
        with open(file_path, "w") as f:
            f.write("{ invalid json }")

        # Should raise an error or return empty list
        with pytest.raises(json.JSONDecodeError):
            storage.load_draws("corrupted")

    def test_save_empty_list(self):
        """Test saving an empty list of draws."""
        import storage

        storage.save_draws("daily_lotto", [])

        # File should not be created for empty list
        # Or if it is, it should contain empty list
        loaded = storage.load_draws("daily_lotto")
        assert loaded == []

    def test_multiple_games_isolation(self, create_draw):
        """Test that different games have isolated storage."""
        import storage

        daily_draw = create_draw(game="daily_lotto", main_numbers=[1, 2, 3, 4, 5])
        lotto_draw = create_draw(game="lotto", main_numbers=[1, 2, 3, 4, 5, 6])

        storage.save_draws("daily_lotto", [daily_draw])
        storage.save_draws("lotto", [lotto_draw])

        daily_loaded = storage.load_draws("daily_lotto")
        lotto_loaded = storage.load_draws("lotto")

        assert len(daily_loaded) == 1
        assert len(lotto_loaded) == 1
        assert daily_loaded[0].game == "daily_lotto"
        assert lotto_loaded[0].game == "lotto"
