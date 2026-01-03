"""
Play Tracker Module - Track lottery plays and winnings

Tracks:
- All tickets played through the app
- Checks results automatically when app loads
- Calculates winnings based on matches
- Maintains running totals for display
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

import storage


# Prize structures for each game (approximate values)
PRIZE_STRUCTURE = {
    'daily_lotto': {
        5: 'JACKPOT',  # Variable jackpot
        4: 350,       # Variable (parimutuel) - typically R250-R500
        3: 50,        # Fixed
        2: 15,        # Fixed
        1: 0,
        0: 0
    },
    'lotto': {
        6: 'JACKPOT',
        5: 5000,
        4: 150,
        3: 50,
        2: 20,
        1: 0,
        0: 0
    },
    'lotto_plus_1': {
        6: 'JACKPOT',
        5: 3000,
        4: 100,
        3: 25,
        2: 10,
        1: 0,
        0: 0
    },
    'lotto_plus_2': {
        6: 'JACKPOT',
        5: 2000,
        4: 75,
        3: 20,
        2: 5,
        1: 0,
        0: 0
    },
    'powerball': {
        '5+1': 'JACKPOT',
        '5+0': 500000,
        '4+1': 5000,
        '4+0': 500,
        '3+1': 100,
        '3+0': 20,
        '2+1': 15,
        '1+1': 10,
        '0+1': 5,
        '0+0': 0
    },
    'powerball_plus': {
        '5+1': 'JACKPOT',
        '5+0': 100000,
        '4+1': 2500,
        '4+0': 250,
        '3+1': 50,
        '3+0': 10,
        '2+1': 10,
        '1+1': 5,
        '0+1': 5,
        '0+0': 0
    }
}

# Estimated jackpot values (for display purposes)
ESTIMATED_JACKPOTS = {
    'daily_lotto': 400000,
    'lotto': 5000000,
    'lotto_plus_1': 2000000,
    'lotto_plus_2': 1000000,
    'powerball': 50000000,
    'powerball_plus': 10000000
}


@dataclass
class PlayedTicket:
    """Represents a single played ticket."""
    game: str
    numbers: List[int]
    bonus_number: Optional[int]  # For Powerball
    played_date: str
    draw_date: str  # Target draw date
    cost: float
    checked: bool = False
    matches: int = 0
    bonus_match: bool = False
    winnings: float = 0.0


@dataclass
class PlaySession:
    """Represents a play session (batch of tickets)."""
    session_id: str
    game: str
    played_at: str
    draw_date: str
    tickets: List[Dict]
    total_cost: float
    checked: bool = False
    total_matches: Dict[int, int] = None  # matches -> count
    total_winnings: float = 0.0


@dataclass
class TrackerStats:
    """Overall tracker statistics."""
    total_played: float
    total_won: float
    total_tickets: int
    total_sessions: int
    best_match: int
    jackpots_won: int
    win_rate: float  # % of tickets that won something
    profit_loss: float
    games_played: Dict[str, int]
    streak: int  # Current winning/losing streak


class PlayTracker:
    """Tracks all plays and calculates winnings."""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.data_dir = data_dir
        self.tracker_file = os.path.join(data_dir, 'play_tracker.json')
        self.sessions: List[PlaySession] = []
        self._load_data()

    def _load_data(self):
        """Load existing tracker data."""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
                    self.sessions = []
                    for s in data.get('sessions', []):
                        session = PlaySession(
                            session_id=s['session_id'],
                            game=s['game'],
                            played_at=s['played_at'],
                            draw_date=s['draw_date'],
                            tickets=s['tickets'],
                            total_cost=s['total_cost'],
                            checked=s.get('checked', False),
                            total_matches=s.get('total_matches', {}),
                            total_winnings=s.get('total_winnings', 0.0)
                        )
                        self.sessions.append(session)
            except (json.JSONDecodeError, KeyError):
                self.sessions = []

    def _save_data(self):
        """Save tracker data to file."""
        os.makedirs(self.data_dir, exist_ok=True)
        data = {
            'sessions': [
                {
                    'session_id': s.session_id,
                    'game': s.game,
                    'played_at': s.played_at,
                    'draw_date': s.draw_date,
                    'tickets': s.tickets,
                    'total_cost': s.total_cost,
                    'checked': s.checked,
                    'total_matches': s.total_matches or {},
                    'total_winnings': s.total_winnings
                }
                for s in self.sessions
            ],
            'last_updated': datetime.now().isoformat()
        }
        with open(self.tracker_file, 'w') as f:
            json.dump(data, f, indent=2)

    def record_play(self, game: str, tickets: List[List[int]],
                   total_cost: float, bonus_numbers: List[int] = None) -> str:
        """
        Record a new play session.

        Returns: session_id
        """
        session_id = f"{game}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine draw date (next draw after today)
        draw_date = self._get_next_draw_date(game)

        # Create ticket records
        ticket_records = []
        for i, nums in enumerate(tickets):
            ticket = {
                'numbers': nums,
                'bonus_number': bonus_numbers[i] if bonus_numbers and i < len(bonus_numbers) else None,
                'matches': 0,
                'bonus_match': False,
                'winnings': 0.0
            }
            ticket_records.append(ticket)

        session = PlaySession(
            session_id=session_id,
            game=game,
            played_at=datetime.now().isoformat(),
            draw_date=draw_date,
            tickets=ticket_records,
            total_cost=total_cost,
            checked=False,
            total_matches={},
            total_winnings=0.0
        )

        self.sessions.append(session)
        self._save_data()

        return session_id

    def _get_next_draw_date(self, game: str) -> str:
        """Get the next draw date for a game."""
        # For simplicity, use today or tomorrow
        today = datetime.now()
        return today.strftime('%Y-%m-%d')

    def check_results(self) -> Dict[str, any]:
        """
        Check all unchecked sessions against actual results.

        Returns summary of new winnings found.
        """
        new_winnings = 0.0
        sessions_checked = 0
        winning_tickets = 0

        for session in self.sessions:
            if session.checked:
                continue

            # Get actual draw results
            draws = storage.load_draws(session.game, limit=10)
            if not draws:
                continue

            # Find matching draw by date
            session_date = session.draw_date
            matching_draw = None
            for draw in draws:
                draw_date_str = draw.draw_date.strftime('%Y-%m-%d')
                if draw_date_str == session_date:
                    matching_draw = draw
                    break

            # If no exact match, check if any draw is after the play date
            if not matching_draw:
                played_at = datetime.fromisoformat(session.played_at)
                for draw in draws:
                    if draw.draw_date >= played_at:
                        matching_draw = draw
                        break

            if not matching_draw:
                continue

            # Check each ticket
            session_winnings = 0.0
            match_counts = defaultdict(int)

            for ticket in session.tickets:
                ticket_nums = set(ticket['numbers'])
                draw_nums = set(matching_draw.main_numbers)

                matches = len(ticket_nums & draw_nums)
                ticket['matches'] = matches
                match_counts[matches] += 1

                # Check bonus for Powerball
                bonus_match = False
                if matching_draw.bonus_numbers and ticket.get('bonus_number'):
                    bonus_match = ticket['bonus_number'] in matching_draw.bonus_numbers
                    ticket['bonus_match'] = bonus_match

                # Calculate winnings
                winnings = self._calculate_winnings(session.game, matches, bonus_match)
                ticket['winnings'] = winnings
                session_winnings += winnings

                if winnings > 0:
                    winning_tickets += 1

            session.total_matches = dict(match_counts)
            session.total_winnings = session_winnings
            session.checked = True
            new_winnings += session_winnings
            sessions_checked += 1

        self._save_data()

        return {
            'sessions_checked': sessions_checked,
            'new_winnings': new_winnings,
            'winning_tickets': winning_tickets
        }

    def _calculate_winnings(self, game: str, matches: int, bonus_match: bool = False) -> float:
        """Calculate winnings based on matches."""
        prizes = PRIZE_STRUCTURE.get(game, PRIZE_STRUCTURE['daily_lotto'])

        # Handle Powerball-style games
        if game in ['powerball', 'powerball_plus']:
            key = f"{matches}+{1 if bonus_match else 0}"
            prize = prizes.get(key, 0)
            if prize == 'JACKPOT':
                return ESTIMATED_JACKPOTS.get(game, 1000000)
            return prize

        # Regular games
        prize = prizes.get(matches, 0)
        if prize == 'JACKPOT':
            return ESTIMATED_JACKPOTS.get(game, 100000)
        return prize

    def get_stats(self) -> TrackerStats:
        """Get overall tracker statistics."""
        total_played = sum(s.total_cost for s in self.sessions)
        total_won = sum(s.total_winnings for s in self.sessions)
        total_tickets = sum(len(s.tickets) for s in self.sessions)

        # Count games played
        games_played = defaultdict(int)
        for s in self.sessions:
            games_played[s.game] += len(s.tickets)

        # Find best match
        best_match = 0
        for s in self.sessions:
            for ticket in s.tickets:
                if ticket.get('matches', 0) > best_match:
                    best_match = ticket['matches']

        # Count jackpots (5+ for daily lotto, 6 for lotto, etc.)
        jackpots_won = 0
        for s in self.sessions:
            for ticket in s.tickets:
                matches = ticket.get('matches', 0)
                if s.game == 'daily_lotto' and matches == 5:
                    jackpots_won += 1
                elif s.game in ['lotto', 'lotto_plus_1', 'lotto_plus_2'] and matches == 6:
                    jackpots_won += 1
                elif s.game in ['powerball', 'powerball_plus'] and matches == 5 and ticket.get('bonus_match'):
                    jackpots_won += 1

        # Calculate win rate
        winning_tickets = sum(
            1 for s in self.sessions
            for t in s.tickets
            if t.get('winnings', 0) > 0
        )
        win_rate = (winning_tickets / total_tickets * 100) if total_tickets > 0 else 0

        # Calculate streak (simplified)
        streak = 0

        return TrackerStats(
            total_played=total_played,
            total_won=total_won,
            total_tickets=total_tickets,
            total_sessions=len(self.sessions),
            best_match=best_match,
            jackpots_won=jackpots_won,
            win_rate=win_rate,
            profit_loss=total_won - total_played,
            games_played=dict(games_played),
            streak=streak
        )

    def get_recent_plays(self, limit: int = 5) -> List[PlaySession]:
        """Get most recent play sessions."""
        return sorted(self.sessions, key=lambda s: s.played_at, reverse=True)[:limit]

    def add_manual_play(self, game: str, total_cost: float, num_tickets: int):
        """Add a manual play entry (for plays made outside the app)."""
        session_id = f"{game}_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create dummy tickets
        tickets = [{'numbers': [], 'matches': 0, 'winnings': 0.0} for _ in range(num_tickets)]

        session = PlaySession(
            session_id=session_id,
            game=game,
            played_at=datetime.now().isoformat(),
            draw_date=datetime.now().strftime('%Y-%m-%d'),
            tickets=tickets,
            total_cost=total_cost,
            checked=True,  # Manual entries are pre-checked
            total_matches={},
            total_winnings=0.0
        )

        self.sessions.append(session)
        self._save_data()

        return session_id

    def add_manual_win(self, game: str, amount: float):
        """Record a manual win (for wins not auto-detected)."""
        # Find most recent session for this game and add winnings
        for session in reversed(self.sessions):
            if session.game == game:
                session.total_winnings += amount
                self._save_data()
                return True

        # If no session found, create a dummy one
        session_id = f"{game}_win_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = PlaySession(
            session_id=session_id,
            game=game,
            played_at=datetime.now().isoformat(),
            draw_date=datetime.now().strftime('%Y-%m-%d'),
            tickets=[],
            total_cost=0.0,
            checked=True,
            total_matches={},
            total_winnings=amount
        )
        self.sessions.append(session)
        self._save_data()
        return True


def get_tracker() -> PlayTracker:
    """Get the global tracker instance."""
    return PlayTracker()


def format_stats_banner(stats: TrackerStats) -> str:
    """Format stats for display in banner."""
    profit_color = "green" if stats.profit_loss >= 0 else "red"
    profit_sign = "+" if stats.profit_loss >= 0 else ""

    lines = [
        f"[bold cyan]Played:[/bold cyan] [white]R{stats.total_played:,.2f}[/white]",
        f"[bold green]Won:[/bold green] [white]R{stats.total_won:,.2f}[/white]",
        f"[bold {profit_color}]P/L:[/bold {profit_color}] [{profit_color}]{profit_sign}R{stats.profit_loss:,.2f}[/{profit_color}]",
        f"[dim]Tickets: {stats.total_tickets} | Best: {stats.best_match} matches[/dim]"
    ]

    return " | ".join(lines[:3]) + f"\n{lines[3]}"
