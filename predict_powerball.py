"""
PowerBall Prediction Based on Forensic Findings
================================================
Generates predictions using:
1. Historical frequency patterns
2. Time-based analysis (month/day patterns)
3. Overdue numbers (recency)
4. Pair co-occurrence patterns
5. Forensic anomalies detected
"""

import sys
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Tuple
import numpy as np

sys.path.insert(0, r"C:\Users\judah\Documents\azanda.tech\lotto-ai-draw")

from models import Draw
from fetcher import fetch_extended_history_sync
from config import get_game

def analyze_powerball_for_prediction():
    """Deep analysis of PowerBall for today's prediction."""

    print("="*70)
    print("POWERBALL PREDICTION ANALYSIS")
    print(f"Date: {datetime.now().strftime('%A, %d %B %Y')}")
    print("="*70)

    # Fetch data
    print("\nFetching PowerBall historical data...")
    result = fetch_extended_history_sync("powerball", target_days=1095)
    draws = result[0] if isinstance(result, tuple) else result

    if not draws:
        print("ERROR: Could not fetch PowerBall data")
        return

    print(f"Loaded {len(draws)} draws for analysis")

    game_config = get_game("powerball")
    main_range = list(range(1, 51))  # PowerBall main: 1-50
    bonus_range = list(range(1, 21))  # PowerBall bonus: 1-20

    # =========================================================================
    # ANALYSIS 1: Overall Frequency
    # =========================================================================
    print("\n" + "-"*70)
    print("ANALYSIS 1: OVERALL FREQUENCY (Hot/Cold Numbers)")
    print("-"*70)

    all_main = [n for d in draws for n in d.main_numbers]
    all_bonus = [n for d in draws for n in d.bonus_numbers]

    main_freq = Counter(all_main)
    bonus_freq = Counter(all_bonus)

    # Sort by frequency
    hot_main = main_freq.most_common(15)
    cold_main = main_freq.most_common()[:-16:-1]  # Bottom 15

    print("\nHOT MAIN NUMBERS (most frequent):")
    for i, (num, count) in enumerate(hot_main[:10], 1):
        expected = len(all_main) / 50
        dev = (count - expected) / expected * 100
        print(f"  {i:2d}. Number {num:2d}: {count:3d} times ({dev:+.1f}%)")

    print("\nCOLD MAIN NUMBERS (least frequent):")
    for i, (num, count) in enumerate(cold_main[:10], 1):
        expected = len(all_main) / 50
        dev = (count - expected) / expected * 100
        print(f"  {i:2d}. Number {num:2d}: {count:3d} times ({dev:+.1f}%)")

    if bonus_freq:
        hot_bonus = bonus_freq.most_common(5)
        print("\nHOT POWERBALL NUMBERS:")
        for num, count in hot_bonus:
            print(f"  PowerBall {num:2d}: {count:3d} times")

    # =========================================================================
    # ANALYSIS 2: Recency (Overdue Numbers)
    # =========================================================================
    print("\n" + "-"*70)
    print("ANALYSIS 2: OVERDUE NUMBERS (Due to Appear)")
    print("-"*70)

    last_seen_main = {}
    last_seen_bonus = {}

    for i, d in enumerate(draws):
        for num in d.main_numbers:
            if num not in last_seen_main:
                last_seen_main[num] = i
        for num in d.bonus_numbers:
            if num not in last_seen_bonus:
                last_seen_bonus[num] = i

    # Fill in numbers never seen
    for n in main_range:
        if n not in last_seen_main:
            last_seen_main[n] = len(draws)

    overdue_main = sorted(last_seen_main.items(), key=lambda x: x[1], reverse=True)

    print("\nMOST OVERDUE MAIN NUMBERS:")
    for i, (num, draws_ago) in enumerate(overdue_main[:15], 1):
        print(f"  {i:2d}. Number {num:2d}: {draws_ago} draws since last appearance")

    # =========================================================================
    # ANALYSIS 3: Day-of-Week Patterns
    # =========================================================================
    print("\n" + "-"*70)
    print("ANALYSIS 3: DAY-OF-WEEK PATTERNS")
    print("-"*70)

    today_dow = datetime.now().weekday()
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # PowerBall draws on Tuesday and Friday
    print(f"\nToday is {dow_names[today_dow]}")

    # Analyze numbers that appear on Tuesdays and Fridays
    dow_freq = defaultdict(Counter)
    for d in draws:
        dow = d.draw_date.weekday()
        for n in d.main_numbers:
            dow_freq[dow][n] += 1

    # Find hot numbers for draw days (Tuesday=1, Friday=4)
    draw_days = [1, 4]  # Tuesday and Friday

    for day in draw_days:
        if day in dow_freq:
            print(f"\nHot numbers on {dow_names[day]}s:")
            day_hot = dow_freq[day].most_common(10)
            for num, count in day_hot:
                print(f"  Number {num:2d}: {count} times")

    # =========================================================================
    # ANALYSIS 4: December Patterns (Seasonal)
    # =========================================================================
    print("\n" + "-"*70)
    print("ANALYSIS 4: DECEMBER PATTERNS (Seasonal Analysis)")
    print("-"*70)

    december_draws = [d for d in draws if d.draw_date.month == 12]
    print(f"\nDecember draws in dataset: {len(december_draws)}")

    if december_draws:
        dec_nums = [n for d in december_draws for n in d.main_numbers]
        dec_freq = Counter(dec_nums)
        dec_hot = dec_freq.most_common(15)

        print("\nHot numbers in DECEMBER:")
        for i, (num, count) in enumerate(dec_hot, 1):
            print(f"  {i:2d}. Number {num:2d}: {count} times in December")

    # =========================================================================
    # ANALYSIS 5: Recent Trend (Last 30 Draws)
    # =========================================================================
    print("\n" + "-"*70)
    print("ANALYSIS 5: RECENT TREND (Last 30 Draws)")
    print("-"*70)

    recent_draws = draws[:30]
    recent_nums = [n for d in recent_draws for n in d.main_numbers]
    recent_freq = Counter(recent_nums)
    recent_hot = recent_freq.most_common(15)

    print("\nHot numbers in LAST 30 DRAWS:")
    for i, (num, count) in enumerate(recent_hot, 1):
        print(f"  {i:2d}. Number {num:2d}: {count} times recently")

    # =========================================================================
    # ANALYSIS 6: Pair Co-occurrence
    # =========================================================================
    print("\n" + "-"*70)
    print("ANALYSIS 6: STRONG PAIR PATTERNS")
    print("-"*70)

    pair_counts = Counter()
    for d in draws:
        nums = sorted(d.main_numbers)
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                pair_counts[(nums[i], nums[j])] += 1

    top_pairs = pair_counts.most_common(20)
    print("\nMost frequent pairs:")
    for (a, b), count in top_pairs[:10]:
        print(f"  {a:2d}-{b:2d}: appeared together {count} times")

    # Numbers that appear in many top pairs
    pair_member_freq = Counter()
    for (a, b), count in top_pairs[:30]:
        pair_member_freq[a] += count
        pair_member_freq[b] += count

    print("\nNumbers with strongest pair connections:")
    for num, score in pair_member_freq.most_common(10):
        print(f"  Number {num:2d}: pair strength score = {score}")

    # =========================================================================
    # GENERATE PREDICTIONS
    # =========================================================================
    print("\n" + "="*70)
    print("POWERBALL PREDICTIONS FOR TODAY")
    print("="*70)

    # Build weighted scores for each number
    scores = {n: 0.0 for n in main_range}

    # Factor 1: Overall frequency (weight: 2.0)
    total_main = len(all_main)
    for n in main_range:
        freq = main_freq.get(n, 0)
        scores[n] += (freq / total_main * 50) * 2.0

    # Factor 2: Recency/Overdue (weight: 1.5)
    max_overdue = max(last_seen_main.values())
    for n, overdue in last_seen_main.items():
        scores[n] += (overdue / max_overdue) * 1.5

    # Factor 3: December pattern (weight: 1.0)
    if december_draws:
        dec_total = len(dec_nums)
        for n in main_range:
            dec_f = dec_freq.get(n, 0)
            scores[n] += (dec_f / dec_total * 50) * 1.0

    # Factor 4: Recent trend (weight: 1.5)
    recent_total = len(recent_nums)
    for n in main_range:
        rec_f = recent_freq.get(n, 0)
        scores[n] += (rec_f / recent_total * 50) * 1.5

    # Factor 5: Pair strength (weight: 0.5)
    max_pair_score = max(pair_member_freq.values()) if pair_member_freq else 1
    for n, pscore in pair_member_freq.items():
        scores[n] += (pscore / max_pair_score) * 0.5

    # Sort by score
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Top candidates
    top_candidates = [n for n, _ in sorted_scores[:20]]

    # Generate multiple prediction sets
    rng = np.random.default_rng(int(datetime.now().timestamp()))

    print("\n" + "-"*70)
    print("PREDICTION SET 1: HOT NUMBERS FOCUS")
    print("-"*70)
    print("(Based on most frequent numbers)")

    # Use top frequency numbers
    hot_set = sorted([n for n, _ in hot_main[:8]])
    hot_selection = sorted(rng.choice(hot_set, size=5, replace=False).tolist())

    # Hot PowerBall
    hot_pb = hot_bonus[0][0] if hot_bonus else rng.choice(bonus_range)

    print(f"\n  MAIN NUMBERS: {' - '.join(f'{n:02d}' for n in hot_selection)}")
    print(f"  POWERBALL:    {hot_pb:02d}")
    print(f"  Sum: {sum(hot_selection)}")

    print("\n" + "-"*70)
    print("PREDICTION SET 2: OVERDUE NUMBERS FOCUS")
    print("-"*70)
    print("(Based on numbers due to appear)")

    # Use overdue numbers
    overdue_nums = [n for n, _ in overdue_main[:10]]
    overdue_selection = sorted(rng.choice(overdue_nums, size=5, replace=False).tolist())

    # Overdue PowerBall
    overdue_bonus = sorted(last_seen_bonus.items(), key=lambda x: x[1], reverse=True)
    overdue_pb = overdue_bonus[0][0] if overdue_bonus else rng.choice(bonus_range)

    print(f"\n  MAIN NUMBERS: {' - '.join(f'{n:02d}' for n in overdue_selection)}")
    print(f"  POWERBALL:    {overdue_pb:02d}")
    print(f"  Sum: {sum(overdue_selection)}")

    print("\n" + "-"*70)
    print("PREDICTION SET 3: DECEMBER SEASONAL")
    print("-"*70)
    print("(Based on December historical patterns)")

    # Use December hot numbers
    dec_hot_nums = [n for n, _ in dec_hot[:10]] if dec_hot else top_candidates[:10]
    dec_selection = sorted(rng.choice(dec_hot_nums, size=5, replace=False).tolist())

    print(f"\n  MAIN NUMBERS: {' - '.join(f'{n:02d}' for n in dec_selection)}")
    print(f"  POWERBALL:    {hot_pb:02d}")
    print(f"  Sum: {sum(dec_selection)}")

    print("\n" + "-"*70)
    print("PREDICTION SET 4: BALANCED WEIGHTED")
    print("-"*70)
    print("(Combining all factors with statistical weighting)")

    # Use weighted sampling from top candidates
    weights = np.array([scores[n] for n in top_candidates])
    weights = weights / weights.sum()

    balanced_selection = sorted(rng.choice(
        top_candidates,
        size=5,
        replace=False,
        p=weights
    ).tolist())

    # Weighted PowerBall
    if bonus_freq:
        pb_weights = np.array([bonus_freq.get(n, 1) for n in bonus_range])
        pb_weights = pb_weights / pb_weights.sum()
        balanced_pb = int(rng.choice(bonus_range, p=pb_weights))
    else:
        balanced_pb = hot_pb

    print(f"\n  MAIN NUMBERS: {' - '.join(f'{n:02d}' for n in balanced_selection)}")
    print(f"  POWERBALL:    {balanced_pb:02d}")
    print(f"  Sum: {sum(balanced_selection)}")

    print("\n" + "-"*70)
    print("PREDICTION SET 5: PAIR-OPTIMIZED")
    print("-"*70)
    print("(Including numbers with strong pair relationships)")

    # Start with numbers that have strong pairs
    pair_nums = [n for n, _ in pair_member_freq.most_common(15)]

    # Select ensuring some pairs are included
    pair_selection = []
    available = pair_nums.copy()

    # Add first number
    first = rng.choice(available)
    pair_selection.append(first)
    available.remove(first)

    # Add numbers that pair well with first
    for (a, b), _ in top_pairs:
        if a == first and b in available and len(pair_selection) < 5:
            pair_selection.append(b)
            available.remove(b)
        elif b == first and a in available and len(pair_selection) < 5:
            pair_selection.append(a)
            available.remove(a)

    # Fill remaining
    while len(pair_selection) < 5 and available:
        next_num = rng.choice(available)
        pair_selection.append(next_num)
        available.remove(next_num)

    pair_selection = sorted(pair_selection)

    print(f"\n  MAIN NUMBERS: {' - '.join(f'{n:02d}' for n in pair_selection)}")
    print(f"  POWERBALL:    {balanced_pb:02d}")
    print(f"  Sum: {sum(pair_selection)}")

    # =========================================================================
    # FINAL RECOMMENDATION
    # =========================================================================
    print("\n" + "="*70)
    print("FINAL RECOMMENDATION")
    print("="*70)

    # Create consensus from all sets
    all_predictions = [hot_selection, overdue_selection, dec_selection, balanced_selection, pair_selection]
    all_nums = [n for pred in all_predictions for n in pred]
    consensus_freq = Counter(all_nums)

    # Numbers appearing in multiple predictions
    consensus_nums = [n for n, count in consensus_freq.most_common() if count >= 2]

    print("\nNUMBERS APPEARING IN MULTIPLE PREDICTIONS:")
    for n, count in consensus_freq.most_common(10):
        if count >= 2:
            print(f"  Number {n:2d}: appears in {count}/5 prediction sets")

    # Final picks
    if len(consensus_nums) >= 5:
        final_main = sorted(consensus_nums[:5])
    else:
        final_main = balanced_selection

    print("\n" + "*"*70)
    print("*  PRIMARY PREDICTION FOR TODAY'S POWERBALL")
    print("*"*70)
    print(f"*")
    print(f"*  MAIN NUMBERS: {' - '.join(f'{n:02d}' for n in final_main)}")
    print(f"*  POWERBALL:    {balanced_pb:02d}")
    print(f"*")
    print(f"*  Sum: {sum(final_main)} (typical range: 100-155)")
    print("*"*70)

    print("\n" + "="*70)
    print("ALL 5 PREDICTION SETS SUMMARY")
    print("="*70)
    print(f"\n  SET 1 (Hot):      {' - '.join(f'{n:02d}' for n in hot_selection)}  PB: {hot_pb:02d}")
    print(f"  SET 2 (Overdue):  {' - '.join(f'{n:02d}' for n in overdue_selection)}  PB: {overdue_pb:02d}")
    print(f"  SET 3 (December): {' - '.join(f'{n:02d}' for n in dec_selection)}  PB: {hot_pb:02d}")
    print(f"  SET 4 (Balanced): {' - '.join(f'{n:02d}' for n in balanced_selection)}  PB: {balanced_pb:02d}")
    print(f"  SET 5 (Pairs):    {' - '.join(f'{n:02d}' for n in pair_selection)}  PB: {balanced_pb:02d}")

    print("\n" + "-"*70)
    print("DISCLAIMER: This is for entertainment only. Lottery outcomes are")
    print("random (or should be). No prediction system can guarantee wins.")
    print("-"*70)

    return {
        "hot": (hot_selection, hot_pb),
        "overdue": (overdue_selection, overdue_pb),
        "december": (dec_selection, hot_pb),
        "balanced": (balanced_selection, balanced_pb),
        "pairs": (pair_selection, balanced_pb),
        "primary": (final_main, balanced_pb),
    }


if __name__ == "__main__":
    analyze_powerball_for_prediction()
