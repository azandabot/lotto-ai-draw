"""
Data models for lottery draws and predictions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


@dataclass
class Draw:
    """Represents a single lottery draw result."""
    game: str
    draw_number: int
    draw_date: datetime
    main_numbers: list[int]
    bonus_numbers: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "game": self.game,
            "draw_number": self.draw_number,
            "draw_date": self.draw_date.isoformat(),
            "main_numbers": self.main_numbers,
            "bonus_numbers": self.bonus_numbers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Draw":
        """Create from dictionary."""
        return cls(
            game=data["game"],
            draw_number=data["draw_number"],
            draw_date=datetime.fromisoformat(data["draw_date"]),
            main_numbers=data["main_numbers"],
            bonus_numbers=data.get("bonus_numbers", []),
        )

    def format_numbers(self) -> str:
        """Format numbers for display."""
        main = " - ".join(str(n).zfill(2) for n in sorted(self.main_numbers))
        if self.bonus_numbers:
            bonus = " + ".join(str(n).zfill(2) for n in self.bonus_numbers)
            return f"{main} | PB: {bonus}"
        return main


@dataclass
class Prediction:
    """Represents an AI-generated prediction."""
    game: str
    main_numbers: list[int]
    bonus_numbers: list[int] = field(default_factory=list)
    reasoning: str = ""
    confidence_note: str = ""
    generated_at: datetime = field(default_factory=datetime.now)

    def format_numbers(self) -> str:
        """Format numbers for display."""
        main = " - ".join(str(n).zfill(2) for n in sorted(self.main_numbers))
        if self.bonus_numbers:
            bonus = " + ".join(str(n).zfill(2) for n in self.bonus_numbers)
            return f"{main} | PB: {bonus}"
        return main


@dataclass
class NumberStats:
    """Statistics for a single number."""
    number: int
    frequency: int
    last_drawn: Optional[datetime] = None
    days_since_drawn: Optional[int] = None

    @property
    def is_hot(self) -> bool:
        """Number drawn frequently (above average)."""
        return self.frequency > 0 and (self.days_since_drawn or 999) < 30

    @property
    def is_cold(self) -> bool:
        """Number not drawn recently."""
        return self.days_since_drawn is not None and self.days_since_drawn > 60
