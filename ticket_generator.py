"""
Ticket Generator Module - Selbee-Style Wheeling Strategy

Generates optimized lottery tickets based on:
1. Historical pattern analysis (decade clustering, close pairs)
2. Hot/cold number analysis
3. Systematic wheeling for maximum coverage
4. Budget-aware ticket generation

Inspired by Jerry & Marge Selbee's volume + expected value strategy.
"""

import json
import random
from collections import Counter
from itertools import combinations
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

import storage
from config import get_game, GAMES


@dataclass
class TicketBatch:
    """Represents a batch of tickets for a game."""
    game: str
    tickets: List[List[int]]
    cost_per_ticket: float
    admin_fee_per_batch: float
    batch_size: int
    total_cost: float
    strategy_summary: str
    hot_numbers: List[int]
    coverage_stats: Dict[str, int]
    generated_at: datetime


class TicketGenerator:
    """Generates optimized lottery tickets using Selbee-style strategies."""

    # Game-specific settings
    GAME_SETTINGS = {
        'daily_lotto': {
            'cost_per_ticket': 3.00,
            'admin_fee': 2.90,
            'batch_size': 5,
            'main_range': (1, 36),
            'pick_count': 5,
            'has_bonus': False
        },
        'lotto': {
            'cost_per_ticket': 5.00,
            'admin_fee': 2.90,
            'batch_size': 5,
            'main_range': (1, 52),
            'pick_count': 6,
            'has_bonus': False
        },
        'lotto_plus_1': {
            'cost_per_ticket': 2.50,
            'admin_fee': 2.90,
            'batch_size': 5,
            'main_range': (1, 52),
            'pick_count': 6,
            'has_bonus': False
        },
        'lotto_plus_2': {
            'cost_per_ticket': 2.50,
            'admin_fee': 2.90,
            'batch_size': 5,
            'main_range': (1, 52),
            'pick_count': 6,
            'has_bonus': False
        },
        'powerball': {
            'cost_per_ticket': 5.00,
            'admin_fee': 2.90,
            'batch_size': 5,
            'main_range': (1, 50),
            'pick_count': 5,
            'bonus_range': (1, 20),
            'has_bonus': True
        },
        'powerball_plus': {
            'cost_per_ticket': 2.50,
            'admin_fee': 2.90,
            'batch_size': 5,
            'main_range': (1, 50),
            'pick_count': 5,
            'bonus_range': (1, 20),
            'has_bonus': True
        }
    }

    def __init__(self, game: str):
        self.game = game
        self.settings = self.GAME_SETTINGS.get(game, self.GAME_SETTINGS['daily_lotto'])
        self.draws = storage.load_draws(game)
        self.hot_numbers = []
        self.very_hot_numbers = []
        self.cold_numbers = []
        self.decade_clusters = {}

        if self.draws:
            self._analyze_patterns()

    def _analyze_patterns(self):
        """Analyze historical data for patterns."""
        if not self.draws:
            return

        # Count frequency
        freq = Counter()
        for draw in self.draws:
            for n in draw.main_numbers:
                freq[n] += 1

        # Determine hot/cold thresholds
        if freq:
            values = list(freq.values())
            avg_freq = sum(values) / len(values)

            # Very hot: top 5 most frequent
            sorted_by_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            self.very_hot_numbers = [n for n, _ in sorted_by_freq[:5]]

            # Hot: above average frequency
            self.hot_numbers = [n for n, f in freq.items() if f >= avg_freq]

            # Cold: never appeared or appeared only once
            min_n, max_n = self.settings['main_range']
            all_nums = set(range(min_n, max_n + 1))
            appeared = set(freq.keys())
            self.cold_numbers = list(all_nums - appeared)
            self.cold_numbers.extend([n for n, f in freq.items() if f == 1])

        # Analyze decade clustering
        self._analyze_decade_clusters()

    def _analyze_decade_clusters(self):
        """Analyze which decades cluster most often."""
        cluster_counts = Counter()

        for draw in self.draws:
            decades = Counter()
            for n in draw.main_numbers:
                decade = self._get_decade(n)
                decades[decade] += 1

            # Find which decade has the cluster
            for decade, count in decades.items():
                if count >= 2:
                    cluster_counts[decade] += 1

        self.decade_clusters = dict(cluster_counts)

    def _get_decade(self, n: int) -> str:
        """Get decade label for a number."""
        if n <= 9:
            return '1-9'
        elif n <= 19:
            return '10-19'
        elif n <= 29:
            return '20-29'
        elif n <= 39:
            return '30-39'
        elif n <= 49:
            return '40-49'
        else:
            return '50+'

    def _get_numbers_in_decade(self, decade: str) -> List[int]:
        """Get all valid numbers in a decade."""
        min_n, max_n = self.settings['main_range']

        ranges = {
            '1-9': (1, 9),
            '10-19': (10, 19),
            '20-29': (20, 29),
            '30-39': (30, 39),
            '40-49': (40, 49),
            '50+': (50, 59)
        }

        start, end = ranges.get(decade, (1, 9))
        return [n for n in range(max(start, min_n), min(end, max_n) + 1)
                if n not in self.cold_numbers or random.random() < 0.1]  # Occasionally include cold

    def _has_close_pair(self, nums: List[int]) -> bool:
        """Check if numbers have a close pair (gap <= 3)."""
        sorted_nums = sorted(nums)
        return any(sorted_nums[i+1] - sorted_nums[i] <= 3
                   for i in range(len(sorted_nums) - 1))

    def _has_cluster(self, nums: List[int]) -> bool:
        """Check if numbers have 2+ in same decade."""
        decades = Counter(self._get_decade(n) for n in nums)
        return max(decades.values()) >= 2

    def _count_hot(self, nums: List[int]) -> int:
        """Count how many hot numbers are in the pick."""
        return sum(1 for n in nums if n in self.hot_numbers)

    def _is_valid_pick(self, nums: List[int]) -> bool:
        """Validate a pick follows our patterns."""
        if len(set(nums)) != len(nums):  # No duplicates
            return False
        if not self._has_close_pair(nums):
            return False
        if not self._has_cluster(nums):
            return False
        if self._count_hot(nums) < 2:
            return False
        return True

    def calculate_tickets_for_budget(self, budget: float) -> Tuple[int, int, float, float]:
        """
        Calculate how many tickets can be purchased with given budget.

        Returns: (num_batches, total_tickets, total_cost, remaining)
        """
        cost_per_batch = (self.settings['batch_size'] * self.settings['cost_per_ticket']
                         + self.settings['admin_fee'])

        num_batches = int(budget // cost_per_batch)
        total_tickets = num_batches * self.settings['batch_size']
        total_cost = num_batches * cost_per_batch
        remaining = budget - total_cost

        return num_batches, total_tickets, total_cost, remaining

    def _check_odd_even_balance(self, nums: List[int]) -> bool:
        """Check if numbers have good odd/even balance (2-3 of each)."""
        odd_count = sum(1 for n in nums if n % 2 == 1)
        return 2 <= odd_count <= 3

    def _check_low_high_balance(self, nums: List[int]) -> bool:
        """Check if numbers have reasonable low/high balance."""
        mid = (self.settings['main_range'][1] + 1) // 2
        low_count = sum(1 for n in nums if n <= mid)
        return 1 <= low_count <= 4  # At least 1 low and 1 high

    def _is_balanced_pick(self, nums: List[int]) -> bool:
        """Check if pick is well-balanced across multiple dimensions."""
        if len(set(nums)) != len(nums):  # No duplicates
            return False
        if not self._has_close_pair(nums):
            return False
        if not self._has_cluster(nums):
            return False
        if not self._check_odd_even_balance(nums):
            return False
        if not self._check_low_high_balance(nums):
            return False
        return True

    def generate_wheeled_tickets(self, num_tickets: int) -> List[List[int]]:
        """
        Generate tickets using the WINNING strategy (R305.80 win!).

        THIS STRATEGY WON US MONEY:
        1. ~30% tickets: Hot number focused (3 hot + 2 warm)
        2. ~30% tickets: Mixed hot + warm (2 hot + 2 warm + 1 any)
        3. ~25% tickets: Include cold numbers (1-2 cold + 2 hot + rest)
        4. ~15% tickets: Random for coverage

        All tickets must pass:
        - Odd/even balance (2-3 of each)
        - Low/high balance
        - Decade clustering
        - Close pair requirement
        """
        picks = []
        pick_count = self.settings['pick_count']
        min_n, max_n = self.settings['main_range']
        all_nums = list(range(min_n, max_n + 1))

        # If no data, generate balanced random picks
        if not self.draws or not self.very_hot_numbers:
            while len(picks) < num_tickets:
                pick = sorted(random.sample(all_nums, pick_count))
                if pick not in picks and self._is_balanced_pick(pick):
                    picks.append(pick)
            return picks

        # Categorize numbers
        core_hot = self.very_hot_numbers[:5]  # Top 5 most frequent
        warm = [n for n in self.hot_numbers if n not in core_hot][:10]
        cold = self.cold_numbers[:10] if self.cold_numbers else []
        medium = [n for n in all_nums if n not in core_hot and n not in cold]

        # WHEEL 1: Hot-focused (~30% of tickets) - THE WINNING APPROACH
        hot_target = int(num_tickets * 0.30)
        attempts = 0
        while len(picks) < hot_target and attempts < 1000:
            attempts += 1
            if len(core_hot) >= 3 and len(medium) >= 2:
                # 3 hot + 2 from medium/warm
                hot_pick = random.sample(core_hot, 3)
                other_pick = random.sample(medium, 2)
                pick = sorted(hot_pick + other_pick)
                if pick not in picks and self._is_balanced_pick(pick):
                    picks.append(pick)

        # WHEEL 2: Mixed hot + warm (~30% of tickets)
        mixed_target = int(num_tickets * 0.30) + len(picks)
        attempts = 0
        while len(picks) < mixed_target and attempts < 1000:
            attempts += 1
            if len(core_hot) >= 2 and len(warm) >= 2:
                # 2 hot + 2 warm + 1 any
                hot_pick = random.sample(core_hot, 2)
                warm_pick = random.sample(warm, 2)
                remaining = [n for n in all_nums if n not in hot_pick and n not in warm_pick]
                if remaining:
                    other = random.sample(remaining, 1)
                    pick = sorted(hot_pick + warm_pick + other)
                    if pick not in picks and self._is_balanced_pick(pick):
                        picks.append(pick)

        # WHEEL 3: Cold number inclusion (~25% of tickets)
        cold_target = int(num_tickets * 0.25) + len(picks)
        attempts = 0
        while len(picks) < cold_target and attempts < 1000:
            attempts += 1
            if len(cold) >= 1 and len(core_hot) >= 2:
                # 1-2 cold + 2 hot + rest from anywhere
                cold_count = random.choice([1, 2]) if len(cold) >= 2 else 1
                cold_pick = random.sample(cold, cold_count)
                hot_pick = random.sample(core_hot, 2)
                remaining = [n for n in all_nums if n not in cold_pick and n not in hot_pick]
                needed = pick_count - len(cold_pick) - len(hot_pick)
                if len(remaining) >= needed:
                    other = random.sample(remaining, needed)
                    pick = sorted(cold_pick + hot_pick + other)
                    if pick not in picks and self._is_balanced_pick(pick):
                        picks.append(pick)

        # WHEEL 4: Random for coverage (~15% of tickets)
        attempts = 0
        while len(picks) < num_tickets and attempts < 1000:
            attempts += 1
            pick = sorted(random.sample(all_nums, pick_count))
            if pick not in picks and self._is_balanced_pick(pick):
                picks.append(pick)

        return picks[:num_tickets]

    def generate_for_budget(self, budget: float) -> Optional[TicketBatch]:
        """
        Generate optimized tickets for a given budget.

        Returns a TicketBatch with all tickets and metadata.
        """
        num_batches, total_tickets, total_cost, remaining = self.calculate_tickets_for_budget(budget)

        if total_tickets == 0:
            return None

        # Generate wheeled tickets
        tickets = self.generate_wheeled_tickets(total_tickets)

        # Calculate coverage stats
        coverage = Counter()
        for ticket in tickets:
            for n in ticket:
                coverage[n] += 1

        # Get top covered numbers
        top_coverage = dict(coverage.most_common(10))

        # Build strategy summary
        strategy = self._build_strategy_summary(tickets, total_tickets)

        return TicketBatch(
            game=self.game,
            tickets=tickets,
            cost_per_ticket=self.settings['cost_per_ticket'],
            admin_fee_per_batch=self.settings['admin_fee'],
            batch_size=self.settings['batch_size'],
            total_cost=total_cost,
            strategy_summary=strategy,
            hot_numbers=self.very_hot_numbers,
            coverage_stats=top_coverage,
            generated_at=datetime.now()
        )

    def _build_strategy_summary(self, tickets: List[List[int]], total: int) -> str:
        """Build a summary of the strategy used."""
        lines = [
            "WINNING STRATEGY v4.0",
            "(This strategy won us R305.80!)",
            "",
            "DISTRIBUTION:",
            "- ~30% hot-focused (3 hot + 2 warm)",
            "- ~30% mixed (2 hot + 2 warm + 1 any)",
            "- ~25% include cold numbers",
            "- ~15% random for coverage",
            "",
            "ALL TICKETS PASS:",
            "- Odd/Even balance: 2-3 of each",
            "- Decade clustering: 2+ in same decade",
            "- Close pairs: numbers within gap of 3",
            "- Low/High balance",
            "",
            f"Hot numbers: {self.very_hot_numbers[:5]}",
            f"Cold numbers: {self.cold_numbers[:5]}",
            "",
            "Let's get this money!"
        ]
        return "\n".join(lines)

    def format_tickets_for_display(self, batch: TicketBatch) -> str:
        """Format tickets for terminal display."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"{self.game.upper().replace('_', ' ')} - BUDGET PLAY")
        lines.append(f"Total: {len(batch.tickets)} tickets | Cost: R{batch.total_cost:.2f}")
        lines.append("=" * 60)
        lines.append("")

        # Group into batches
        batch_num = 0
        for i in range(0, len(batch.tickets), batch.batch_size):
            batch_num += 1
            batch_cost = (batch.batch_size * batch.cost_per_ticket) + batch.admin_fee_per_batch
            lines.append(f"BATCH {batch_num} (R{batch_cost:.2f}):")
            lines.append("-" * 30)

            for j, ticket in enumerate(batch.tickets[i:i + batch.batch_size]):
                ticket_num = i + j + 1
                formatted = "-".join(f"{n:02d}" for n in ticket)
                lines.append(f"  {ticket_num:2}. {formatted}")

            lines.append("")

        return "\n".join(lines)

    def save_tickets_to_file(self, batch: TicketBatch, filepath: str):
        """Save tickets to a text file."""
        content = []
        content.append(f"{self.game.upper().replace('_', ' ')} - SELBEE STRATEGY")
        content.append(f"Date: {batch.generated_at.strftime('%Y-%m-%d')}")
        content.append(f"Budget: R{batch.total_cost:.2f} ({len(batch.tickets)} tickets)")
        content.append("=" * 50)
        content.append("")

        # Tickets by batch
        batch_num = 0
        for i in range(0, len(batch.tickets), batch.batch_size):
            batch_num += 1
            batch_cost = (batch.batch_size * batch.cost_per_ticket) + batch.admin_fee_per_batch
            content.append(f"BATCH {batch_num} (R{batch_cost:.2f}):")
            content.append("-" * 30)

            for j, ticket in enumerate(batch.tickets[i:i + batch.batch_size]):
                ticket_num = i + j + 1
                formatted = "-".join(f"{n:02d}" for n in ticket)
                content.append(f"{ticket_num:2}. {formatted}")

            content.append("")

        content.append("=" * 50)
        content.append("STRATEGY APPLIED:")
        content.append("=" * 50)
        content.append(batch.strategy_summary)
        content.append("")
        content.append("HOT NUMBERS COVERAGE:")
        for n, count in sorted(batch.coverage_stats.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(batch.tickets) * 100
            content.append(f"  {n}: in {count} tickets ({pct:.0f}%)")
        content.append("")
        content.append("GOOD LUCK!")

        with open(filepath, 'w') as f:
            f.write("\n".join(content))


def generate_tickets_for_budget(game: str, budget: float) -> Optional[TicketBatch]:
    """
    Convenience function to generate tickets for a budget.

    Args:
        game: Game name (e.g., 'daily_lotto', 'powerball')
        budget: Budget in Rands

    Returns:
        TicketBatch with generated tickets or None if budget too low
    """
    generator = TicketGenerator(game)
    return generator.generate_for_budget(budget)
