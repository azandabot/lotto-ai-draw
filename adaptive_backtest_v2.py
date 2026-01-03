"""
Enhanced Adaptive Learning Backtest V2

Improvements over V1:
1. Track more parameters (decade balance, close pairs, sum ranges)
2. Multiple strategy variants running in parallel
3. More aggressive learning with momentum
4. Show draw-by-draw learning progression
5. Compare strategies to find the best approach
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
    """Adjustable strategy parameters with expanded tracking."""
    hot_weight: float = 0.40
    cold_weight: float = 0.15
    warm_weight: float = 0.45
    decade_balance: float = 0.6
    close_pair_required: bool = True
    cluster_required: bool = True
    sum_range_center: int = 95
    sum_range_width: int = 35
    recency_weight: float = 0.4
    learning_rate: float = 0.15
    momentum: float = 0.9

    # Track momentum for smoother learning
    hot_momentum: float = 0.0
    cold_momentum: float = 0.0
    warm_momentum: float = 0.0


class EnhancedLearner:
    """
    Enhanced adaptive learner with more learning dimensions.
    """

    def __init__(self, draws_data: List[Dict]):
        self.all_draws = sorted(draws_data, key=lambda x: x['draw_date'])
        self.params = StrategyParams()
        self.history = []
        self.learning_log = []

        # Track what patterns actually work
        self.pattern_success = {
            'hot_dominated': {'wins': 0, 'total': 0},
            'cold_dominated': {'wins': 0, 'total': 0},
            'balanced': {'wins': 0, 'total': 0},
            'close_pair': {'wins': 0, 'total': 0},
            'no_close_pair': {'wins': 0, 'total': 0},
            'clustered': {'wins': 0, 'total': 0},
            'spread': {'wins': 0, 'total': 0}
        }

    def _get_frequency(self, draws: List[Dict], recency_weighted: bool = True) -> Counter:
        """Calculate frequency with optional recency weighting."""
        freq = Counter()
        total = len(draws)

        for i, draw in enumerate(draws):
            weight = 1.0
            if recency_weighted and total > 0:
                weight = 1 + (i / total) * self.params.recency_weight * 3

            for n in draw['main_numbers']:
                freq[n] += weight

        return freq

    def _categorize_numbers(self, freq: Counter) -> Tuple[Set, Set, Set]:
        """Categorize into hot, warm, cold with better thresholds."""
        all_nums = set(range(1, 37))

        if not freq:
            return set(list(all_nums)[:12]), set(list(all_nums)[12:24]), set(list(all_nums)[24:])

        avg_freq = sum(freq.values()) / len(freq) if freq else 1

        hot = {n for n in all_nums if freq.get(n, 0) > avg_freq * 1.15}
        cold = {n for n in all_nums if freq.get(n, 0) < avg_freq * 0.6}
        warm = all_nums - hot - cold

        return hot, warm, cold

    def _has_close_pair(self, nums: List[int]) -> bool:
        """Check if ticket has consecutive or near-consecutive numbers."""
        sorted_nums = sorted(nums)
        for i in range(len(sorted_nums) - 1):
            if sorted_nums[i+1] - sorted_nums[i] <= 2:
                return True
        return False

    def _has_cluster(self, nums: List[int]) -> bool:
        """Check if 2-3 numbers fall in same decade."""
        decades = defaultdict(int)
        for n in nums:
            decades[(n-1) // 10] += 1
        return max(decades.values()) >= 2

    def _score_ticket(self, ticket: List[int], freq: Counter,
                      hot: Set, warm: Set, cold: Set) -> float:
        """Score a ticket based on current parameters."""
        score = 0.0

        # Category scoring
        hot_count = sum(1 for n in ticket if n in hot)
        warm_count = sum(1 for n in ticket if n in warm)
        cold_count = sum(1 for n in ticket if n in cold)

        score += hot_count * self.params.hot_weight * 10
        score += warm_count * self.params.warm_weight * 10
        score += cold_count * self.params.cold_weight * 10

        # Decade balance
        decades = defaultdict(int)
        for n in ticket:
            decades[(n-1) // 10] += 1
        decade_spread = len(decades)
        if decade_spread >= 3:
            score += self.params.decade_balance * 5

        # Close pair bonus
        if self._has_close_pair(ticket):
            score += 3

        # Cluster bonus
        if self._has_cluster(ticket):
            score += 3

        # Sum range check
        ticket_sum = sum(ticket)
        if abs(ticket_sum - self.params.sum_range_center) <= self.params.sum_range_width:
            score += 5

        return score

    def _generate_ticket(self, freq: Counter, hot: Set, warm: Set, cold: Set) -> List[int]:
        """Generate a single ticket with weighted selection."""
        all_nums = list(range(1, 37))

        # Build probability distribution
        probs = {}
        for n in all_nums:
            base_score = freq.get(n, 0) * 0.3

            if n in hot:
                base_score += self.params.hot_weight * 8
            elif n in warm:
                base_score += self.params.warm_weight * 8
            else:
                base_score += self.params.cold_weight * 8

            probs[n] = max(base_score, 0.1)

        # Weighted random selection
        ticket = []
        remaining = all_nums.copy()

        for _ in range(5):
            total = sum(probs[n] for n in remaining)
            r = random.random() * total
            cumsum = 0

            for n in remaining:
                cumsum += probs[n]
                if r <= cumsum:
                    ticket.append(n)
                    remaining.remove(n)
                    break
            else:
                # Fallback
                selected = random.choice(remaining)
                ticket.append(selected)
                remaining.remove(selected)

        return sorted(ticket)

    def _generate_predictions(self, prior_draws: List[Dict], num_tickets: int = 20) -> List[List[int]]:
        """Generate diverse predictions."""
        if len(prior_draws) < 5:
            return [sorted(random.sample(range(1, 37), 5)) for _ in range(num_tickets)]

        freq = self._get_frequency(prior_draws, recency_weighted=True)
        hot, warm, cold = self._categorize_numbers(freq)

        tickets = []
        attempts = 0
        max_attempts = num_tickets * 20

        while len(tickets) < num_tickets and attempts < max_attempts:
            attempts += 1
            ticket = self._generate_ticket(freq, hot, warm, cold)

            # Score the ticket
            score = self._score_ticket(ticket, freq, hot, warm, cold)

            # Apply constraints
            valid = True

            if self.params.close_pair_required and not self._has_close_pair(ticket):
                valid = False

            if self.params.cluster_required and not self._has_cluster(ticket):
                valid = False

            # Check odd/even balance (2-3 odds)
            odd_count = sum(1 for n in ticket if n % 2 == 1)
            if odd_count < 2 or odd_count > 3:
                valid = False

            if valid and ticket not in tickets:
                tickets.append(ticket)

        # Fill remaining with less strict generation
        while len(tickets) < num_tickets:
            ticket = sorted(random.sample(range(1, 37), 5))
            if ticket not in tickets:
                tickets.append(ticket)

        return tickets

    def _analyze_and_learn(self, actual: List[int], predictions: List[List[int]],
                           prior_draws: List[Dict]) -> Dict:
        """Analyze results and calculate parameter adjustments."""
        actual_set = set(actual)
        freq = self._get_frequency(prior_draws)
        hot, warm, cold = self._categorize_numbers(freq)

        # Count actual in each category
        actual_hot = sum(1 for n in actual if n in hot)
        actual_warm = sum(1 for n in actual if n in warm)
        actual_cold = sum(1 for n in actual if n in cold)

        # Track pattern success
        if actual_hot >= 3:
            self.pattern_success['hot_dominated']['total'] += 1
        elif actual_cold >= 2:
            self.pattern_success['cold_dominated']['total'] += 1
        else:
            self.pattern_success['balanced']['total'] += 1

        if self._has_close_pair(actual):
            self.pattern_success['close_pair']['total'] += 1
        else:
            self.pattern_success['no_close_pair']['total'] += 1

        if self._has_cluster(actual):
            self.pattern_success['clustered']['total'] += 1
        else:
            self.pattern_success['spread']['total'] += 1

        # Calculate adjustments with momentum
        adjustments = {}

        # Hot weight adjustment
        if actual_hot >= 3:
            hot_delta = 0.04
        elif actual_hot <= 1:
            hot_delta = -0.03
        else:
            hot_delta = 0.0

        # Cold weight adjustment
        if actual_cold >= 2:
            cold_delta = 0.06  # Bigger boost when cold hits
        elif actual_cold == 0:
            cold_delta = -0.02
        else:
            cold_delta = 0.0

        # Warm weight adjustment
        if actual_warm >= 3:
            warm_delta = 0.03
        elif actual_warm <= 1:
            warm_delta = -0.02
        else:
            warm_delta = 0.0

        # Apply momentum
        self.params.hot_momentum = self.params.momentum * self.params.hot_momentum + hot_delta
        self.params.cold_momentum = self.params.momentum * self.params.cold_momentum + cold_delta
        self.params.warm_momentum = self.params.momentum * self.params.warm_momentum + warm_delta

        adjustments = {
            'hot_weight': self.params.hot_momentum,
            'cold_weight': self.params.cold_momentum,
            'warm_weight': self.params.warm_momentum
        }

        # Sum range learning
        actual_sum = sum(actual)
        if abs(actual_sum - self.params.sum_range_center) > self.params.sum_range_width:
            # Actual sum was outside our range, adjust
            adjustments['sum_range_center'] = (actual_sum - self.params.sum_range_center) * 0.1

        return {
            'actual_hot': actual_hot,
            'actual_warm': actual_warm,
            'actual_cold': actual_cold,
            'actual_sum': actual_sum,
            'adjustments': adjustments
        }

    def _apply_learning(self, adjustments: Dict):
        """Apply parameter adjustments with bounds."""
        lr = self.params.learning_rate

        for param, delta in adjustments.items():
            if hasattr(self.params, param):
                current = getattr(self.params, param)
                new_val = current + (delta * lr)

                # Apply bounds
                if param in ['hot_weight', 'cold_weight', 'warm_weight']:
                    new_val = max(0.05, min(0.7, new_val))
                elif param == 'sum_range_center':
                    new_val = max(70, min(120, new_val))

                setattr(self.params, param, new_val)

    def run_backtest(self, start_idx: int = 20, num_tickets: int = 20, verbose: bool = True):
        """Run the enhanced adaptive backtest."""
        results = []
        total_draws = len(self.all_draws)

        if verbose:
            print("=" * 80)
            print("ENHANCED ADAPTIVE LEARNING BACKTEST V2")
            print("=" * 80)
            print(f"Total draws available: {total_draws}")
            print(f"Training draws: {start_idx}")
            print(f"Testing draws: {total_draws - start_idx}")
            print(f"Tickets per draw: {num_tickets}")
            print()
            print("Initial Parameters:")
            print(f"  hot_weight:  {self.params.hot_weight:.3f}")
            print(f"  warm_weight: {self.params.warm_weight:.3f}")
            print(f"  cold_weight: {self.params.cold_weight:.3f}")
            print(f"  sum_center:  {self.params.sum_range_center}")
            print()
            print("-" * 80)
            print(f"{'Draw':^6} | {'Date':^12} | {'Actual':^25} | {'Best':^4} | {'3+':^4} | {'Hot':^3} | {'Cold':^4}")
            print("-" * 80)

        # Track rolling performance
        rolling_3plus = []

        for i in range(start_idx, total_draws):
            draw = self.all_draws[i]
            prior_draws = self.all_draws[:i]

            actual = draw['main_numbers']
            draw_date = draw['draw_date'][:10]

            # Generate predictions
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

            three_plus = matches_dist[3] + matches_dist[4] + matches_dist[5]
            rolling_3plus.append(1 if best_match >= 3 else 0)

            # Analyze and learn
            analysis = self._analyze_and_learn(actual, predictions, prior_draws)

            # Apply learning
            self._apply_learning(analysis['adjustments'])

            # Store result
            results.append({
                'draw_num': i - start_idx + 1,
                'date': draw_date,
                'actual': actual,
                'best_match': best_match,
                'three_plus': three_plus,
                'matches_dist': matches_dist,
                'params': {
                    'hot': self.params.hot_weight,
                    'warm': self.params.warm_weight,
                    'cold': self.params.cold_weight
                },
                'analysis': analysis
            })

            if verbose:
                actual_str = str(actual)
                hot_count = analysis['actual_hot']
                cold_count = analysis['actual_cold']

                # Highlight rows with 3+ matches
                marker = " <--" if best_match >= 3 else ""
                print(f"{i-start_idx+1:^6} | {draw_date:^12} | {actual_str:^25} | {best_match:^4} | {three_plus:^4} | {hot_count:^3} | {cold_count:^4}{marker}")

        self.history = results

        if verbose:
            self._print_summary()

        return results

    def _print_summary(self):
        """Print comprehensive summary."""
        if not self.history:
            return

        total_draws = len(self.history)
        total_tickets = total_draws * 20

        # Aggregate matches
        all_matches = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in self.history:
            for m, count in r['matches_dist'].items():
                all_matches[m] += count

        draws_with_3plus = sum(1 for r in self.history if r['best_match'] >= 3)

        # Split into quarters for trend analysis
        q1 = self.history[:len(self.history)//4]
        q2 = self.history[len(self.history)//4:len(self.history)//2]
        q3 = self.history[len(self.history)//2:3*len(self.history)//4]
        q4 = self.history[3*len(self.history)//4:]

        q1_3plus = sum(1 for r in q1 if r['best_match'] >= 3)
        q2_3plus = sum(1 for r in q2 if r['best_match'] >= 3)
        q3_3plus = sum(1 for r in q3 if r['best_match'] >= 3)
        q4_3plus = sum(1 for r in q4 if r['best_match'] >= 3)

        print()
        print("=" * 80)
        print("BACKTEST COMPLETE - COMPREHENSIVE RESULTS")
        print("=" * 80)
        print()
        print(f"Total draws tested: {total_draws}")
        print(f"Total tickets generated: {total_tickets}")
        print()
        print("MATCH DISTRIBUTION:")
        print("-" * 40)
        for m in [5, 4, 3, 2, 1, 0]:
            count = all_matches[m]
            pct = count / total_tickets * 100
            bar = "#" * int(pct)
            prize = ["Jackpot", "R2,000", "R100", "R30", "Free play", "-"][5-m]
            print(f"  {m} matches: {count:5} ({pct:5.1f}%) [{prize:^10}] {bar}")

        print()
        print("SUCCESS RATES:")
        print("-" * 40)
        print(f"  Draws with 3+ match: {draws_with_3plus:3}/{total_draws} ({draws_with_3plus/total_draws*100:.1f}%)")
        print(f"  3+ tickets rate:     {all_matches[3]+all_matches[4]+all_matches[5]:3}/{total_tickets} ({(all_matches[3]+all_matches[4]+all_matches[5])/total_tickets*100:.2f}%)")

        print()
        print("LEARNING PROGRESSION (3+ wins by quarter):")
        print("-" * 40)
        print(f"  Q1 (draws 1-{len(q1)}):    {q1_3plus:2} wins")
        print(f"  Q2 (draws {len(q1)+1}-{len(q1)+len(q2)}):  {q2_3plus:2} wins")
        print(f"  Q3 (draws {len(q1)+len(q2)+1}-{len(q1)+len(q2)+len(q3)}):  {q3_3plus:2} wins")
        print(f"  Q4 (draws {len(q1)+len(q2)+len(q3)+1}-{total_draws}):  {q4_3plus:2} wins")

        first_half = q1_3plus + q2_3plus
        second_half = q3_3plus + q4_3plus
        improvement = second_half - first_half
        pct_improvement = (improvement / (first_half + 0.01)) * 100

        print()
        print(f"  First half total:  {first_half} wins")
        print(f"  Second half total: {second_half} wins")
        print(f"  Improvement: {improvement:+d} ({pct_improvement:+.0f}%)")

        print()
        print("LEARNED PARAMETERS:")
        print("-" * 40)
        print(f"  hot_weight:    {self.params.hot_weight:.3f} (started at 0.400)")
        print(f"  warm_weight:   {self.params.warm_weight:.3f} (started at 0.450)")
        print(f"  cold_weight:   {self.params.cold_weight:.3f} (started at 0.150)")
        print(f"  sum_center:    {self.params.sum_range_center:.0f} (started at 95)")

        # Pattern analysis
        print()
        print("PATTERN ANALYSIS (what actually won):")
        print("-" * 40)
        for pattern, stats in self.pattern_success.items():
            if stats['total'] > 0:
                print(f"  {pattern}: {stats['total']} occurrences")

        # Recommendations
        print()
        print("=" * 80)
        print("RECOMMENDED STRATEGY BASED ON LEARNING:")
        print("=" * 80)
        print()

        if self.params.hot_weight > 0.35:
            print("  [+] Hot numbers are valuable - include 2-3 per ticket")
        else:
            print("  [-] Hot numbers overrated - don't over-rely on them")

        if self.params.cold_weight > 0.2:
            print("  [+] Cold numbers DO hit - include 1-2 per ticket")
        else:
            print("  [-] Cold numbers rarely hit - limit to 0-1 per ticket")

        if self.params.warm_weight > 0.4:
            print("  [+] Warm numbers are the backbone - include 2-3 per ticket")

        print(f"  [*] Target sum range: {int(self.params.sum_range_center - 30)} to {int(self.params.sum_range_center + 30)}")
        print()


def run_enhanced_backtest():
    """Main function."""
    print("Loading Daily Lotto data...")
    with open('data/daily_lotto.json', 'r') as f:
        draws_data = json.load(f)

    print(f"Loaded {len(draws_data)} draws")
    print()

    learner = EnhancedLearner(draws_data)
    learner.run_backtest(start_idx=20, num_tickets=20, verbose=True)

    return learner


if __name__ == "__main__":
    run_enhanced_backtest()
