"""
Adaptive Learning Backtest System

Simulates neural network-like learning:
1. Start with initial strategy parameters
2. Generate predictions for each draw using only prior data
3. Compare to actual results
4. Adjust parameters based on what worked/failed
5. Track improvement over iterations

This shows the strategy "learning" from mistakes.
"""

import json
import random
from collections import Counter, defaultdict
from itertools import combinations
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StrategyParams:
    """Adjustable strategy parameters (like neural net weights)."""
    hot_weight: float = 0.5        # Weight for hot numbers (0-1)
    cold_weight: float = 0.2       # Weight for cold numbers (0-1)
    warm_weight: float = 0.3       # Weight for warm numbers (0-1)
    decade_balance: float = 0.5    # How much to enforce decade spread (0-1)
    odd_even_strict: bool = True   # Enforce 2-3 odd/even balance
    recency_weight: float = 0.3    # Weight recent draws more (0-1)
    sum_range_width: int = 30      # +/- from average sum
    consecutive_required: bool = True  # Require close pairs
    learning_rate: float = 0.1     # How fast to adjust (like neural net)


@dataclass
class DrawResult:
    """Result of predicting a single draw."""
    draw_date: str
    actual_numbers: List[int]
    predicted_tickets: List[List[int]]
    best_match: int
    matches_distribution: Dict[int, int]
    params_used: Dict
    insights: List[str] = field(default_factory=list)


class AdaptiveLearner:
    """
    Learns optimal lottery strategy through iterative backtesting.

    Like a neural network:
    - Forward pass: Generate predictions
    - Compare to actual: Calculate "loss" (missed matches)
    - Backward pass: Adjust parameters based on what worked
    """

    def __init__(self, draws_data: List[Dict]):
        # Sort draws oldest first for chronological learning
        self.all_draws = sorted(draws_data, key=lambda x: x['draw_date'])
        self.params = StrategyParams()
        self.history: List[DrawResult] = []
        self.learning_log: List[str] = []

    def _get_frequency(self, draws: List[Dict]) -> Counter:
        """Calculate frequency from a set of draws."""
        freq = Counter()
        for draw in draws:
            for n in draw['main_numbers']:
                freq[n] += 1
        return freq

    def _get_recency_weighted_freq(self, draws: List[Dict]) -> Counter:
        """Recent draws weighted more heavily."""
        freq = Counter()
        total = len(draws)
        for i, draw in enumerate(draws):
            # More recent = higher weight
            weight = 1 + (i / total) * self.params.recency_weight * 2
            for n in draw['main_numbers']:
                freq[n] += weight
        return freq

    def _categorize_numbers(self, freq: Counter) -> Tuple[List, List, List]:
        """Categorize into hot, warm, cold based on frequency."""
        all_nums = list(range(1, 37))

        if not freq:
            return all_nums[:12], all_nums[12:24], all_nums[24:]

        avg_freq = sum(freq.values()) / len(freq) if freq else 1

        hot = [n for n in all_nums if freq.get(n, 0) > avg_freq * 1.2]
        cold = [n for n in all_nums if freq.get(n, 0) < avg_freq * 0.5]
        warm = [n for n in all_nums if n not in hot and n not in cold]

        return hot, warm, cold

    def _score_number(self, n: int, freq: Counter, hot: List, warm: List, cold: List) -> float:
        """Score a number based on current parameters."""
        score = 0.0

        if n in hot:
            score += self.params.hot_weight * 10
        elif n in warm:
            score += self.params.warm_weight * 10
        elif n in cold:
            score += self.params.cold_weight * 10

        # Add frequency component
        score += freq.get(n, 0) * 0.5

        return score

    def _generate_ticket(self, freq: Counter, hot: List, warm: List, cold: List) -> List[int]:
        """Generate a single ticket based on current parameters."""
        all_nums = list(range(1, 37))

        # Score all numbers
        scores = {n: self._score_number(n, freq, hot, warm, cold) for n in all_nums}

        # Build ticket
        ticket = []

        # Select based on weighted probabilities
        remaining = all_nums.copy()

        for _ in range(5):
            if not remaining:
                break

            # Calculate selection probabilities
            total_score = sum(scores.get(n, 1) for n in remaining)
            if total_score == 0:
                total_score = len(remaining)

            probs = [scores.get(n, 1) / total_score for n in remaining]

            # Weighted random selection
            r = random.random()
            cumsum = 0
            selected = remaining[0]
            for n, p in zip(remaining, probs):
                cumsum += p
                if r <= cumsum:
                    selected = n
                    break

            ticket.append(selected)
            remaining.remove(selected)

        # Apply constraints
        ticket = sorted(ticket)

        # Check odd/even balance
        if self.params.odd_even_strict:
            odd_count = sum(1 for n in ticket if n % 2 == 1)
            if odd_count < 2 or odd_count > 3:
                # Try to fix
                return self._generate_ticket(freq, hot, warm, cold)

        return ticket

    def _generate_predictions(self, prior_draws: List[Dict], num_tickets: int = 20) -> List[List[int]]:
        """Generate prediction tickets using only prior data."""
        if len(prior_draws) < 5:
            # Not enough data, use random
            tickets = []
            for _ in range(num_tickets):
                ticket = sorted(random.sample(range(1, 37), 5))
                tickets.append(ticket)
            return tickets

        # Use recency-weighted frequency
        freq = self._get_recency_weighted_freq(prior_draws)
        hot, warm, cold = self._categorize_numbers(freq)

        tickets = []
        attempts = 0
        max_attempts = num_tickets * 10

        while len(tickets) < num_tickets and attempts < max_attempts:
            attempts += 1
            ticket = self._generate_ticket(freq, hot, warm, cold)

            if ticket not in tickets:
                tickets.append(ticket)

        return tickets

    def _analyze_result(self, actual: List[int], predictions: List[List[int]],
                        prior_draws: List[Dict]) -> Dict:
        """Analyze what we got right/wrong."""
        actual_set = set(actual)

        freq = self._get_frequency(prior_draws)
        hot, warm, cold = self._categorize_numbers(freq)

        insights = []

        # How many actual numbers were hot/warm/cold?
        actual_hot = [n for n in actual if n in hot]
        actual_warm = [n for n in actual if n in warm]
        actual_cold = [n for n in actual if n in cold]

        insights.append(f"Actual breakdown: {len(actual_hot)} hot, {len(actual_warm)} warm, {len(actual_cold)} cold")

        # Did we have good coverage?
        coverage = {}
        for n in actual:
            count = sum(1 for t in predictions if n in t)
            coverage[n] = count

        avg_coverage = sum(coverage.values()) / 5
        insights.append(f"Avg coverage of winning nums: {avg_coverage:.1f}/20 tickets")

        # What should we adjust?
        adjustments = {}

        if len(actual_cold) >= 2:
            adjustments['cold_weight'] = 0.05  # Increase cold weight
            insights.append("LEARN: More cold numbers hit -> increase cold_weight")
        elif len(actual_cold) == 0:
            adjustments['cold_weight'] = -0.02
            insights.append("LEARN: No cold numbers hit -> decrease cold_weight slightly")

        if len(actual_hot) >= 3:
            adjustments['hot_weight'] = 0.03
            insights.append("LEARN: Hot numbers dominated -> increase hot_weight")
        elif len(actual_hot) == 0:
            adjustments['hot_weight'] = -0.05
            insights.append("LEARN: No hot numbers hit -> decrease hot_weight")

        return {
            'insights': insights,
            'adjustments': adjustments,
            'actual_hot': len(actual_hot),
            'actual_warm': len(actual_warm),
            'actual_cold': len(actual_cold),
            'coverage': coverage
        }

    def _apply_learning(self, adjustments: Dict):
        """Apply parameter adjustments (like updating neural net weights)."""
        lr = self.params.learning_rate

        for param, delta in adjustments.items():
            if hasattr(self.params, param):
                current = getattr(self.params, param)
                new_val = current + (delta * lr)
                # Clamp to valid range
                new_val = max(0.05, min(0.8, new_val))
                setattr(self.params, param, new_val)
                self.learning_log.append(f"  Adjusted {param}: {current:.3f} -> {new_val:.3f}")

    def run_backtest(self, start_idx: int = 20, num_tickets: int = 20, verbose: bool = True):
        """
        Run the adaptive backtest.

        Args:
            start_idx: Start from this draw (need prior data)
            num_tickets: Tickets to generate per draw
            verbose: Print progress
        """
        results = []

        total_draws = len(self.all_draws)

        if verbose:
            print("=" * 75)
            print("ADAPTIVE LEARNING BACKTEST")
            print("=" * 75)
            print(f"Total draws: {total_draws}")
            print(f"Starting from draw #{start_idx} (using {start_idx} prior draws for training)")
            print(f"Tickets per draw: {num_tickets}")
            print()
            print("Initial parameters:")
            print(f"  hot_weight: {self.params.hot_weight}")
            print(f"  cold_weight: {self.params.cold_weight}")
            print(f"  warm_weight: {self.params.warm_weight}")
            print()

        for i in range(start_idx, total_draws):
            draw = self.all_draws[i]
            prior_draws = self.all_draws[:i]

            actual = draw['main_numbers']
            draw_date = draw['draw_date'][:10]

            # Generate predictions using only prior data
            predictions = self._generate_predictions(prior_draws, num_tickets)

            # Calculate matches
            actual_set = set(actual)
            matches_dist = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            best_match = 0

            for ticket in predictions:
                m = len(set(ticket) & actual_set)
                matches_dist[m] += 1
                if m > best_match:
                    best_match = m

            # Analyze and learn
            analysis = self._analyze_result(actual, predictions, prior_draws)

            # Record result
            result = DrawResult(
                draw_date=draw_date,
                actual_numbers=actual,
                predicted_tickets=predictions,
                best_match=best_match,
                matches_distribution=matches_dist,
                params_used={
                    'hot_weight': self.params.hot_weight,
                    'cold_weight': self.params.cold_weight,
                    'warm_weight': self.params.warm_weight
                },
                insights=analysis['insights']
            )
            results.append(result)

            # Apply learning
            self._apply_learning(analysis['adjustments'])

            if verbose and (i - start_idx) % 10 == 0:
                print(f"Draw {i-start_idx+1}/{total_draws-start_idx}: {draw_date} | "
                      f"Best: {best_match} | 3+: {matches_dist[3]+matches_dist[4]+matches_dist[5]} tickets")

        self.history = results
        return results

    def get_summary(self) -> Dict:
        """Get summary statistics of the backtest."""
        if not self.history:
            return {}

        total_tickets = sum(sum(r.matches_distribution.values()) for r in self.history)

        all_matches = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in self.history:
            for m, count in r.matches_distribution.items():
                all_matches[m] += count

        draws_with_3plus = sum(1 for r in self.history if r.best_match >= 3)
        draws_with_2plus = sum(1 for r in self.history if r.best_match >= 2)

        # Track improvement over time
        first_half = self.history[:len(self.history)//2]
        second_half = self.history[len(self.history)//2:]

        first_3plus = sum(1 for r in first_half if r.best_match >= 3)
        second_3plus = sum(1 for r in second_half if r.best_match >= 3)

        return {
            'total_draws': len(self.history),
            'total_tickets': total_tickets,
            'matches_distribution': all_matches,
            'draws_with_3plus': draws_with_3plus,
            'draws_with_2plus': draws_with_2plus,
            'three_plus_rate': all_matches[3] + all_matches[4] + all_matches[5],
            'two_plus_rate': sum(all_matches[i] for i in [2,3,4,5]),
            'first_half_3plus': first_3plus,
            'second_half_3plus': second_3plus,
            'improvement': second_3plus - first_3plus,
            'final_params': {
                'hot_weight': self.params.hot_weight,
                'cold_weight': self.params.cold_weight,
                'warm_weight': self.params.warm_weight
            }
        }

    def print_report(self):
        """Print a detailed report of the backtest."""
        summary = self.get_summary()

        print()
        print("=" * 75)
        print("BACKTEST COMPLETE - RESULTS")
        print("=" * 75)
        print()
        print(f"Draws tested: {summary['total_draws']}")
        print(f"Total tickets: {summary['total_tickets']}")
        print()
        print("Match Distribution:")
        for m in [5, 4, 3, 2, 1, 0]:
            count = summary['matches_distribution'][m]
            pct = count / summary['total_tickets'] * 100
            bar = "#" * int(pct)
            print(f"  {m} matches: {count:4} ({pct:5.1f}%) {bar}")

        print()
        print(f"Draws with 3+ match ticket: {summary['draws_with_3plus']}/{summary['total_draws']} "
              f"({summary['draws_with_3plus']/summary['total_draws']*100:.1f}%)")
        print(f"Draws with 2+ match ticket: {summary['draws_with_2plus']}/{summary['total_draws']} "
              f"({summary['draws_with_2plus']/summary['total_draws']*100:.1f}%)")

        print()
        print("LEARNING PROGRESS:")
        print(f"  First half 3+ wins: {summary['first_half_3plus']}")
        print(f"  Second half 3+ wins: {summary['second_half_3plus']}")
        print(f"  Improvement: {summary['improvement']:+d} ({'+' if summary['improvement'] >= 0 else ''}"
              f"{(summary['second_half_3plus']-summary['first_half_3plus'])/(summary['first_half_3plus']+0.01)*100:.0f}%)")

        print()
        print("LEARNED PARAMETERS:")
        for param, value in summary['final_params'].items():
            print(f"  {param}: {value:.3f}")


def run_adaptive_backtest():
    """Main function to run the adaptive backtest."""
    with open('data/daily_lotto.json', 'r') as f:
        draws_data = json.load(f)

    learner = AdaptiveLearner(draws_data)
    learner.run_backtest(start_idx=20, num_tickets=20, verbose=True)
    learner.print_report()

    return learner


if __name__ == "__main__":
    run_adaptive_backtest()
