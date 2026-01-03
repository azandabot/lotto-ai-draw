"""
Strategy Comparison Backtest

Compares:
1. OLD strategy (hot-focused, 30% hot)
2. NEW strategy (warm-focused, 55% warm)
3. PURE RANDOM (baseline)

Run on the same 71 draws to see which performs better.
"""

import json
import random
from collections import Counter, defaultdict
from typing import List, Set


def load_data():
    with open('data/daily_lotto.json', 'r') as f:
        return sorted(json.load(f), key=lambda x: x['draw_date'])


def categorize_numbers(draws: List[dict]) -> tuple:
    """Get hot, warm, cold from a set of draws."""
    freq = Counter()
    for draw in draws:
        for n in draw['main_numbers']:
            freq[n] += 1

    all_nums = set(range(1, 37))

    if not freq:
        return set(), all_nums, set()

    avg_freq = sum(freq.values()) / len(freq)

    hot = {n for n in all_nums if freq.get(n, 0) > avg_freq * 1.15}
    cold = {n for n in all_nums if freq.get(n, 0) < avg_freq * 0.6}
    warm = all_nums - hot - cold

    return hot, warm, cold


def has_close_pair(nums: List[int]) -> bool:
    sorted_nums = sorted(nums)
    for i in range(len(sorted_nums) - 1):
        if sorted_nums[i+1] - sorted_nums[i] <= 2:
            return True
    return False


def has_cluster(nums: List[int]) -> bool:
    decades = defaultdict(int)
    for n in nums:
        decades[(n-1) // 10] += 1
    return max(decades.values()) >= 2


def is_balanced(nums: List[int]) -> bool:
    if len(set(nums)) != len(nums):
        return False
    if not has_close_pair(nums):
        return False
    if not has_cluster(nums):
        return False
    odd_count = sum(1 for n in nums if n % 2 == 1)
    if odd_count < 2 or odd_count > 3:
        return False
    return True


def generate_old_strategy(prior_draws: List[dict], num_tickets: int = 20) -> List[List[int]]:
    """OLD strategy: 30% hot-focused."""
    hot, warm, cold = categorize_numbers(prior_draws)
    hot_list = list(hot)[:5]
    warm_list = list(warm)
    all_nums = list(range(1, 37))

    tickets = []
    attempts = 0

    # 30% hot-focused
    hot_target = int(num_tickets * 0.30)
    while len(tickets) < hot_target and attempts < 500:
        attempts += 1
        if len(hot_list) >= 3 and len(warm_list) >= 2:
            pick = sorted(random.sample(hot_list, 3) + random.sample(warm_list, 2))
            if pick not in tickets and is_balanced(pick):
                tickets.append(pick)

    # Fill rest with random balanced
    while len(tickets) < num_tickets and attempts < 1000:
        attempts += 1
        pick = sorted(random.sample(all_nums, 5))
        if pick not in tickets and is_balanced(pick):
            tickets.append(pick)

    return tickets


def generate_new_strategy(prior_draws: List[dict], num_tickets: int = 20) -> List[List[int]]:
    """NEW strategy: 55% warm-focused (backtest-optimized)."""
    hot, warm, cold = categorize_numbers(prior_draws)
    hot_list = list(hot)[:5]
    warm_list = list(warm)
    all_nums = list(range(1, 37))

    tickets = []
    attempts = 0

    # Only 10% hot-focused now
    hot_target = int(num_tickets * 0.10)
    while len(tickets) < hot_target and attempts < 500:
        attempts += 1
        if len(hot_list) >= 2 and len(warm_list) >= 3:
            pick = sorted(random.sample(hot_list, 2) + random.sample(warm_list, 3))
            if pick not in tickets and is_balanced(pick):
                tickets.append(pick)

    # 55% warm-focused (THE KEY!)
    warm_target = int(num_tickets * 0.55) + len(tickets)
    while len(tickets) < warm_target and attempts < 1000:
        attempts += 1
        if len(warm_list) >= 4:
            warm_pick = random.sample(warm_list, 4)
            remaining = [n for n in all_nums if n not in warm_pick]
            pick = sorted(warm_pick + random.sample(remaining, 1))
            if pick not in tickets and is_balanced(pick):
                tickets.append(pick)

    # Fill rest with random
    while len(tickets) < num_tickets and attempts < 1500:
        attempts += 1
        pick = sorted(random.sample(all_nums, 5))
        if pick not in tickets and is_balanced(pick):
            tickets.append(pick)

    return tickets


def generate_pure_random(num_tickets: int = 20) -> List[List[int]]:
    """Pure random - baseline."""
    tickets = []
    attempts = 0
    all_nums = list(range(1, 37))

    while len(tickets) < num_tickets and attempts < 1000:
        attempts += 1
        pick = sorted(random.sample(all_nums, 5))
        if pick not in tickets and is_balanced(pick):
            tickets.append(pick)

    return tickets


def run_comparison():
    """Run the comparison backtest."""
    draws = load_data()

    print("=" * 80)
    print("STRATEGY COMPARISON BACKTEST")
    print("=" * 80)
    print()
    print("Comparing 3 strategies on 71 draws with 20 tickets each:")
    print("  1. OLD Strategy (30% hot-focused)")
    print("  2. NEW Strategy (55% warm-focused) <- Backtest optimized")
    print("  3. Pure Random (baseline)")
    print()

    results = {
        'old': {'3+': 0, 'matches': {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
        'new': {'3+': 0, 'matches': {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
        'random': {'3+': 0, 'matches': {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}
    }

    start_idx = 20
    num_draws = len(draws) - start_idx

    print("-" * 80)
    print(f"{'Draw':^6} | {'OLD Best':^10} | {'NEW Best':^10} | {'RND Best':^10} | {'Actual':^25}")
    print("-" * 80)

    for i in range(start_idx, len(draws)):
        draw = draws[i]
        prior = draws[:i]
        actual = set(draw['main_numbers'])
        date = draw['draw_date'][:10]

        # Generate tickets with each strategy
        old_tickets = generate_old_strategy(prior, 20)
        new_tickets = generate_new_strategy(prior, 20)
        random_tickets = generate_pure_random(20)

        # Calculate matches
        for name, tickets in [('old', old_tickets), ('new', new_tickets), ('random', random_tickets)]:
            best = 0
            for ticket in tickets:
                m = len(set(ticket) & actual)
                results[name]['matches'][m] += 1
                if m > best:
                    best = m
            if best >= 3:
                results[name]['3+'] += 1

        # Get best for each
        old_best = max(len(set(t) & actual) for t in old_tickets)
        new_best = max(len(set(t) & actual) for t in new_tickets)
        rnd_best = max(len(set(t) & actual) for t in random_tickets)

        # Highlight wins
        old_mark = " ***" if old_best >= 3 else ""
        new_mark = " ***" if new_best >= 3 else ""
        rnd_mark = " ***" if rnd_best >= 3 else ""

        print(f"{i-start_idx+1:^6} | {old_best}{old_mark:^9} | {new_best}{new_mark:^9} | {rnd_best}{rnd_mark:^9} | {draw['main_numbers']}")

    # Summary
    print()
    print("=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print()

    total_tickets = num_draws * 20

    for name, label in [('old', 'OLD (30% hot)'), ('new', 'NEW (55% warm)'), ('random', 'Pure Random')]:
        print(f"{label}:")
        print(f"  Draws with 3+ match: {results[name]['3+']} / {num_draws} ({results[name]['3+']/num_draws*100:.1f}%)")
        three_plus = results[name]['matches'][3] + results[name]['matches'][4] + results[name]['matches'][5]
        print(f"  Total 3+ tickets:    {three_plus} / {total_tickets} ({three_plus/total_tickets*100:.2f}%)")
        print()

    # Winner determination
    old_rate = results['old']['3+'] / num_draws
    new_rate = results['new']['3+'] / num_draws
    rnd_rate = results['random']['3+'] / num_draws

    print("=" * 80)
    print("CONCLUSION:")
    print("=" * 80)

    if new_rate > old_rate and new_rate > rnd_rate:
        improvement = (new_rate - old_rate) / old_rate * 100 if old_rate > 0 else 0
        print(f"  NEW strategy WINS! {improvement:.1f}% better than OLD")
    elif old_rate > new_rate and old_rate > rnd_rate:
        print(f"  OLD strategy wins (unexpected!)")
    elif rnd_rate >= old_rate and rnd_rate >= new_rate:
        print(f"  RANDOM matches or beats both strategies!")
        print(f"  (This proves the lottery is truly random)")
    else:
        print(f"  Results are too close to call")

    print()
    print("KEY INSIGHT: If random performs similarly, no strategy beats pure chance.")
    print("The lottery is designed to be unpredictable!")


if __name__ == "__main__":
    run_comparison()
