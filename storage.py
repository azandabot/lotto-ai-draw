"""
Local JSON storage for historical draw data.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from models import Draw


DATA_DIR = Path(__file__).parent / "data"


def _get_file_path(game: str) -> Path:
    """Get the storage file path for a game."""
    return DATA_DIR / f"{game}.json"


def save_draws(game: str, draws: list[Draw]) -> None:
    """Save draws to local storage."""
    DATA_DIR.mkdir(exist_ok=True)
    file_path = _get_file_path(game)

    # Load existing draws
    existing = load_draws(game)
    # Use date for deduplication (draw numbers may not always be available)
    existing_dates = {d.draw_date.date() for d in existing}

    # Add new draws (avoid duplicates by date)
    for draw in draws:
        if draw.draw_date.date() not in existing_dates:
            existing.append(draw)
            existing_dates.add(draw.draw_date.date())

    # Sort by date (newest first)
    existing.sort(key=lambda d: d.draw_date, reverse=True)

    # Save to file
    data = [d.to_dict() for d in existing]
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def load_draws(game: str, limit: Optional[int] = None) -> list[Draw]:
    """Load draws from local storage."""
    file_path = _get_file_path(game)

    if not file_path.exists():
        return []

    with open(file_path, "r") as f:
        data = json.load(f)

    draws = [Draw.from_dict(d) for d in data]

    if limit:
        return draws[:limit]
    return draws


def get_latest_draw(game: str) -> Optional[Draw]:
    """Get the most recent draw for a game."""
    draws = load_draws(game, limit=1)
    return draws[0] if draws else None


def get_draw_count(game: str) -> int:
    """Get the total number of stored draws for a game."""
    return len(load_draws(game))


def clear_draws(game: str) -> None:
    """Clear all stored draws for a game."""
    file_path = _get_file_path(game)
    if file_path.exists():
        file_path.unlink()


def get_all_stored_games() -> list[str]:
    """Get list of games that have stored data."""
    games = []
    for file_path in DATA_DIR.glob("*.json"):
        games.append(file_path.stem)
    return games
