"""
Game configurations for South African National Lottery games.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameConfig:
    """Configuration for a lottery game."""
    name: str
    display_name: str
    main_numbers: int
    main_range: tuple[int, int]  # (min, max)
    bonus_numbers: int = 0
    bonus_range: Optional[tuple[int, int]] = None
    draw_days: list[str] = None

    def __post_init__(self):
        if self.draw_days is None:
            self.draw_days = []


# South African National Lottery Games
GAMES = {
    "lotto": GameConfig(
        name="lotto",
        display_name="LOTTO",
        main_numbers=6,
        main_range=(1, 58),
        draw_days=["Wednesday", "Saturday"]
    ),
    "lotto_plus_1": GameConfig(
        name="lotto_plus_1",
        display_name="LOTTO PLUS 1",
        main_numbers=6,
        main_range=(1, 58),
        draw_days=["Wednesday", "Saturday"]
    ),
    "lotto_plus_2": GameConfig(
        name="lotto_plus_2",
        display_name="LOTTO PLUS 2",
        main_numbers=6,
        main_range=(1, 58),
        draw_days=["Wednesday", "Saturday"]
    ),
    "powerball": GameConfig(
        name="powerball",
        display_name="PowerBall",
        main_numbers=5,
        main_range=(1, 50),
        bonus_numbers=1,
        bonus_range=(1, 20),
        draw_days=["Tuesday", "Friday"]
    ),
    "powerball_plus": GameConfig(
        name="powerball_plus",
        display_name="PowerBall PLUS",
        main_numbers=5,
        main_range=(1, 50),
        bonus_numbers=1,
        bonus_range=(1, 20),
        draw_days=["Tuesday", "Friday"]
    ),
    "daily_lotto": GameConfig(
        name="daily_lotto",
        display_name="Daily Lotto",
        main_numbers=5,
        main_range=(1, 36),
        draw_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ),
}


def get_game(name: str) -> GameConfig:
    """Get a game configuration by name."""
    if name not in GAMES:
        raise ValueError(f"Unknown game: {name}. Available: {list(GAMES.keys())}")
    return GAMES[name]


def list_games() -> list[GameConfig]:
    """Get all available games."""
    return list(GAMES.values())
