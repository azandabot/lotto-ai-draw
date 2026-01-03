"""
Lottery number predictions using AI or local statistical analysis.

Enhanced version with:
- Improved prompt engineering for GPT
- Pydantic validation for API responses
- Advanced statistical methods (chi-squared, autocorrelation, sum targeting)
- Retry logic with exponential backoff
"""

import os
import re
import json
import random
import time
import logging
from datetime import datetime
from typing import Optional, List
from collections import Counter

import numpy as np
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from models import Draw, Prediction
from config import GameConfig, get_game


load_dotenv()
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Validation
# =============================================================================

class PredictionResponse(BaseModel):
    """Pydantic model for validating GPT responses."""
    main_numbers: List[int]
    bonus_numbers: List[int] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    reasoning: str = ""
    disclaimer: str = "Lottery is random. No prediction method improves odds."

    @field_validator('main_numbers', 'bonus_numbers', mode='before')
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, (list, tuple)):
            return [int(x) for x in v]
        return v

    @field_validator('main_numbers', 'bonus_numbers')
    @classmethod
    def validate_positive(cls, v):
        return [x for x in v if isinstance(x, int) and x > 0]


# =============================================================================
# API Key Management
# =============================================================================

def has_api_key() -> bool:
    """Check if API key is configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    return api_key is not None and api_key != "your-api-key-here" and len(api_key) > 10


def get_client():
    """Get the OpenAI client."""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found. "
            "Please set it in your .env file or environment variables."
        )
    return OpenAI(api_key=api_key)


# =============================================================================
# Close Pair Analysis (Numbers within 1-3 of each other)
# =============================================================================

def count_close_pairs(numbers: List[int], max_gap: int = 3) -> int:
    """
    Count pairs of numbers that are within max_gap of each other.

    Args:
        numbers: List of numbers to analyze
        max_gap: Maximum difference to consider as a "close pair" (default 3)

    Returns:
        Count of close pairs found
    """
    sorted_nums = sorted(numbers)
    count = 0
    for i in range(len(sorted_nums) - 1):
        if sorted_nums[i + 1] - sorted_nums[i] <= max_gap:
            count += 1
    return count


def has_close_pair(numbers: List[int], max_gap: int = 3) -> bool:
    """Check if numbers contain at least one close pair."""
    return count_close_pairs(numbers, max_gap) >= 1


def get_close_pair_rate(draws: List[Draw], max_gap: int = 3) -> float:
    """
    Calculate the rate of draws that contain at least one close pair.

    Returns percentage of draws with close pairs.
    """
    if not draws:
        return 0.0

    draws_with_pairs = sum(1 for d in draws if has_close_pair(d.main_numbers, max_gap))
    return draws_with_pairs / len(draws)


def analyze_close_pair_pattern(draws: List[Draw], max_gap: int = 3) -> dict:
    """
    Comprehensive analysis of close pair patterns in historical data.

    Returns statistics about close pair occurrences.
    """
    if not draws:
        return {
            'rate': 0.0,
            'avg_pairs_per_draw': 0.0,
            'common_pair_gaps': {},
            'draws_analyzed': 0
        }

    pair_counts = []
    gap_counter = Counter()

    for d in draws:
        sorted_nums = sorted(d.main_numbers)
        pairs_in_draw = 0

        for i in range(len(sorted_nums) - 1):
            gap = sorted_nums[i + 1] - sorted_nums[i]
            if gap <= max_gap:
                pairs_in_draw += 1
                gap_counter[gap] += 1

        pair_counts.append(pairs_in_draw)

    return {
        'rate': sum(1 for c in pair_counts if c > 0) / len(draws),
        'avg_pairs_per_draw': sum(pair_counts) / len(draws),
        'common_pair_gaps': dict(gap_counter.most_common()),
        'draws_analyzed': len(draws)
    }


# =============================================================================
# Enhanced Statistics Computation
# =============================================================================

def compute_enhanced_stats(draws: List[Draw], game_config: GameConfig) -> dict:
    """
    Compute comprehensive statistics for prompt injection and local prediction.

    Metrics computed:
    - Frequency distribution (hot/cold numbers)
    - Sum statistics (mean, std)
    - Consecutive number rates
    - Pair co-occurrence
    - Overdue numbers
    - Chi-squared deviation from uniform
    - Positional frequency
    """
    if not draws:
        return {
            'hot_numbers': [],
            'cold_numbers': [],
            'avg_sum': 0,
            'sum_std': 0,
            'consecutive_rate': 0,
            'top_pairs': [],
            'overdue': [],
            'chi_squared': 0,
            'frequency': {},
            'recency': {},
            'pair_scores': {},
        }

    all_main = [n for d in draws for n in d.main_numbers]
    recent_main = [n for d in draws[:10] for n in d.main_numbers]
    num_range = range(game_config.main_range[0], game_config.main_range[1] + 1)

    # Frequency analysis
    freq = Counter(all_main)
    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)

    hot_numbers = [n for n, _ in sorted_freq[:10]]
    cold_numbers = [n for n, _ in sorted_freq[-10:]] if len(sorted_freq) > 10 else []

    # Sum statistics
    sums = [sum(d.main_numbers) for d in draws]
    avg_sum = float(np.mean(sums)) if sums else 0
    sum_std = float(np.std(sums)) if len(sums) > 1 else 0

    # Consecutive pairs rate
    consecutive_count = 0
    for d in draws:
        nums = sorted(d.main_numbers)
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consecutive_count += 1
    consecutive_rate = consecutive_count / len(draws) if draws else 0

    # Pair frequency analysis
    pairs_counter = Counter()
    for d in draws:
        nums = sorted(d.main_numbers)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                pairs_counter[(nums[i], nums[j])] += 1

    top_pairs = [f"{a}-{b}" for (a, b), _ in pairs_counter.most_common(10)]

    # Pair scores for individual numbers
    pair_scores = Counter()
    for (a, b), count in pairs_counter.most_common(50):
        pair_scores[a] += count
        pair_scores[b] += count

    # Overdue numbers
    recent_set = set(recent_main)
    all_nums = set(num_range)
    overdue = sorted([n for n in all_nums if n in freq and n not in recent_set])

    # Chi-squared statistic
    expected = len(all_main) / len(list(num_range)) if num_range else 1
    chi_squared = sum(
        ((freq.get(n, 0) - expected) ** 2) / expected
        for n in num_range
    ) if expected > 0 else 0

    # Recency (draws since last seen)
    last_seen = {}
    for i, d in enumerate(draws):
        for n in d.main_numbers:
            if n not in last_seen:
                last_seen[n] = i
    recency = {n: last_seen.get(n, len(draws)) for n in num_range}

    # Close pair analysis (numbers within 1-3 of each other)
    close_pair_stats = analyze_close_pair_pattern(draws, max_gap=3)

    return {
        'hot_numbers': hot_numbers,
        'cold_numbers': cold_numbers,
        'avg_sum': avg_sum,
        'sum_std': sum_std,
        'consecutive_rate': consecutive_rate,
        'top_pairs': top_pairs,
        'overdue': overdue,
        'chi_squared': chi_squared,
        'frequency': dict(freq),
        'recency': recency,
        'pair_scores': dict(pair_scores),
        'total_draws': len(draws),
        # Close pair pattern stats
        'close_pair_rate': close_pair_stats['rate'],
        'avg_close_pairs_per_draw': close_pair_stats['avg_pairs_per_draw'],
        'common_pair_gaps': close_pair_stats['common_pair_gaps'],
    }


# =============================================================================
# Improved Prompt Engineering
# =============================================================================

def build_prediction_prompt(game_config: GameConfig, draws: List[Draw], stats: dict) -> str:
    """
    Build a structured, token-efficient prompt for GPT.
    Uses condensed statistical encoding to maximize signal.
    """
    # Condensed historical data (last 20 draws only - saves tokens)
    history_compact = []
    for d in draws[:20]:
        nums_str = ','.join(map(str, d.main_numbers))
        bonus_str = f"+{','.join(map(str, d.bonus_numbers))}" if d.bonus_numbers else ""
        history_compact.append(f"{d.draw_date.strftime('%m/%d')}:{nums_str}{bonus_str}")

    # Calculate sum bounds
    sum_lower = stats['avg_sum'] - stats['sum_std'] if stats['sum_std'] else stats['avg_sum'] - 20
    sum_upper = stats['avg_sum'] + stats['sum_std'] if stats['sum_std'] else stats['avg_sum'] + 20

    prompt = f"""You are a lottery pattern analyst. Analyze South African {game_config.display_name} data and suggest numbers.

GAME RULES:
- Pick {game_config.main_numbers} main numbers from {game_config.main_range[0]}-{game_config.main_range[1]}
{f"- Pick {game_config.bonus_numbers} PowerBall from {game_config.bonus_range[0]}-{game_config.bonus_range[1]}" if game_config.bonus_numbers else ""}

HISTORICAL DATA (date:numbers format, last 20 draws):
{chr(10).join(history_compact)}

STATISTICS ({stats.get('total_draws', 0)} total draws analyzed):
- Hot numbers (most frequent): {stats['hot_numbers'][:10]}
- Cold numbers (least frequent): {stats['cold_numbers'][:10]}
- Average sum: {stats['avg_sum']:.0f} (std: {stats['sum_std']:.1f})
- Target sum range: {sum_lower:.0f} to {sum_upper:.0f}
- Consecutive pairs per draw: {stats['consecutive_rate']:.2f}
- Top co-occurring pairs: {stats['top_pairs'][:5]}
- Overdue numbers (not in last 10 draws): {stats['overdue'][:10]}

CRITICAL PATTERN - CLOSE PAIRS:
- {stats.get('close_pair_rate', 0.85):.0%} of historical draws contain at least ONE "close pair" (two numbers within 1-3 of each other)
- Average close pairs per draw: {stats.get('avg_close_pairs_per_draw', 1.2):.1f}
- Most common gaps: {stats.get('common_pair_gaps', {1: 'consecutive', 2: 'near', 3: 'close'})}
- THIS IS A STRONG PATTERN: Your prediction MUST include at least one close pair!

TASK:
1. Identify 2-3 statistical patterns in the data
2. Select numbers balancing hot/cold/overdue factors
3. Ensure the sum of main numbers is within the target range ({sum_lower:.0f}-{sum_upper:.0f})
4. **IMPORTANT: Include at least 1 close pair (two numbers within 1-3 of each other)** - this pattern appears in {stats.get('close_pair_rate', 0.85):.0%} of draws!

IMPORTANT: Respond ONLY with valid JSON matching this exact structure:
{{
  "main_numbers": [exactly {game_config.main_numbers} integers between {game_config.main_range[0]} and {game_config.main_range[1]}],
  {f'"bonus_numbers": [exactly {game_config.bonus_numbers} integers between {game_config.bonus_range[0]} and {game_config.bonus_range[1]}],' if game_config.bonus_numbers else ''}
  "patterns": ["pattern 1 description", "pattern 2 description"],
  "reasoning": "Brief explanation of number selection (1-2 sentences)",
  "disclaimer": "Lottery draws are random. Past results do not influence future outcomes."
}}"""

    return prompt


# =============================================================================
# GPT-Based Prediction with Retry Logic
# =============================================================================

def predict_numbers(
    game: str,
    draws: List[Draw],
    max_retries: int = 3,
    temperature: float = 0.3
) -> Prediction:
    """
    Query OpenAI GPT with structured prompt and robust error handling.

    Args:
        game: Game identifier
        draws: Historical draw data
        max_retries: Number of retry attempts on failure
        temperature: GPT temperature (0.0-1.0, lower = more consistent)

    Returns:
        Prediction object with numbers and reasoning
    """
    game_config = get_game(game)
    client = get_client()

    # Compute statistics
    stats = compute_enhanced_stats(draws, game_config)
    prompt = build_prediction_prompt(game_config, draws, stats)

    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(f"GPT prediction attempt {attempt + 1}/{max_retries} for {game}")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=temperature,
                max_tokens=512,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a statistical analyst. Always respond with valid JSON only. No markdown, no code blocks, just pure JSON."
                    },
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.choices[0].message.content
            logger.debug(f"GPT response: {response_text[:500]}...")

            # Parse and validate with Pydantic
            result = PredictionResponse.model_validate_json(response_text)

            # Range validation
            main_numbers = [
                n for n in result.main_numbers
                if game_config.main_range[0] <= n <= game_config.main_range[1]
            ][:game_config.main_numbers]

            bonus_numbers = []
            if game_config.bonus_numbers and result.bonus_numbers:
                bonus_numbers = [
                    n for n in result.bonus_numbers
                    if game_config.bonus_range[0] <= n <= game_config.bonus_range[1]
                ][:game_config.bonus_numbers]

            # Validate we got enough numbers
            if len(main_numbers) < game_config.main_numbers:
                raise ValueError(f"Insufficient valid numbers: got {len(main_numbers)}, need {game_config.main_numbers}")

            if game_config.bonus_numbers and len(bonus_numbers) < game_config.bonus_numbers:
                raise ValueError(f"Insufficient bonus numbers: got {len(bonus_numbers)}, need {game_config.bonus_numbers}")

            # Build reasoning with patterns
            patterns_str = ', '.join(result.patterns) if result.patterns else 'No specific patterns identified'
            reasoning = f"**Patterns Identified:** {patterns_str}\n\n{result.reasoning}"

            logger.info(f"GPT prediction successful: {main_numbers}")

            return Prediction(
                game=game,
                main_numbers=sorted(main_numbers),
                bonus_numbers=bonus_numbers,
                reasoning=reasoning,
                confidence_note=result.disclaimer,
            )

        except Exception as e:
            last_error = e
            logger.warning(f"GPT prediction attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                continue

    # All retries failed - fallback to local prediction
    logger.error(f"All GPT attempts failed, falling back to local prediction. Last error: {last_error}")
    fallback = predict_numbers_local(game, draws)
    fallback.reasoning = f"**Note:** AI prediction failed ({last_error}). Using local statistical analysis.\n\n{fallback.reasoning}"
    return fallback


# =============================================================================
# Enhanced Local Statistical Prediction
# =============================================================================

def predict_numbers_local(game: str, draws: List[Draw]) -> Prediction:
    """
    Advanced statistical prediction using multiple weighted factors.

    Factors:
    1. Frequency (hot numbers) - weight: 2.5
    2. Recency (due numbers) - weight: 1.5
    3. Pair co-occurrence - weight: 1.0
    4. Chi-squared deviation - weight: 1.0
    5. Sum distribution targeting
    6. Mid-range bias - weight: 0.5

    Selection uses Monte Carlo sampling with sum constraints.
    """
    game_config = get_game(game)

    if len(draws) < 5:
        return _generate_random_prediction(
            game, game_config,
            "Insufficient historical data (< 5 draws). Using random selection."
        )

    # Compute comprehensive statistics
    stats = compute_enhanced_stats(draws, game_config)

    num_range = list(range(game_config.main_range[0], game_config.main_range[1] + 1))
    freq = stats['frequency']
    recency = stats['recency']
    pair_scores = stats['pair_scores']

    # Normalize frequency scores
    max_freq = max(freq.values()) if freq else 1
    freq_scores = {n: freq.get(n, 0) / max_freq for n in num_range}

    # Normalize recency scores (higher = more overdue)
    max_recency = len(draws)
    recency_scores = {n: recency.get(n, max_recency) / max_recency for n in num_range}

    # Normalize pair scores
    max_pair = max(pair_scores.values()) if pair_scores else 1
    pair_norm_scores = {n: pair_scores.get(n, 0) / max_pair for n in num_range}

    # Chi-squared deviation scores (favor numbers below expected frequency)
    expected = len([n for d in draws for n in d.main_numbers]) / len(num_range) if num_range else 1
    chi_scores = {}
    for n in num_range:
        observed = freq.get(n, 0)
        if observed < expected:
            chi_scores[n] = 1.0  # Boost underrepresented
        else:
            chi_scores[n] = 0.5  # Slight penalty for overrepresented

    # Combine weights
    weights = {}
    for n in num_range:
        # Mid-range bias
        mid = (game_config.main_range[0] + game_config.main_range[1]) / 2
        distance_from_mid = abs(n - mid) / mid
        mid_bias = (1 - distance_from_mid) * 0.5

        weights[n] = (
            freq_scores.get(n, 0) * 2.5 +      # Frequency: strongest signal
            recency_scores.get(n, 0) * 1.5 +   # Recency: moderate
            pair_norm_scores.get(n, 0) * 1.0 + # Pairs: moderate
            chi_scores.get(n, 0.5) * 1.0 +     # Chi-squared: moderate
            mid_bias +                          # Mid-range bias
            0.5                                 # Base weight
        )

    # Target sum constraint
    target_sum = stats['avg_sum']
    sum_std = stats['sum_std'] if stats['sum_std'] > 0 else 20

    # Monte Carlo sampling with sum targeting AND close pair requirement
    best_selection = None
    best_score = float('-inf')

    candidates = list(num_range)
    weight_values = np.array([weights[n] for n in candidates])
    probs = weight_values / weight_values.sum()

    # Close pair rate from historical data - this is a critical pattern
    close_pair_rate = stats.get('close_pair_rate', 0.85)
    require_close_pair = close_pair_rate >= 0.7  # Require if pattern appears 70%+ of the time

    for _ in range(2000):  # Increased iterations to find good close-pair selections
        try:
            selection = np.random.choice(
                candidates,
                size=game_config.main_numbers,
                replace=False,
                p=probs
            )

            selection_list = sorted(selection.tolist())
            selection_sum = sum(selection_list)
            sum_diff = abs(selection_sum - target_sum)

            # Check for close pairs (numbers within 1-3 of each other)
            has_pair = has_close_pair(selection_list, max_gap=3)
            close_pair_count = count_close_pairs(selection_list, max_gap=3)

            # Skip if we require close pairs but don't have any
            if require_close_pair and not has_pair:
                continue

            # Score the selection:
            # - Reward being close to target sum
            # - Reward having 1-2 close pairs (matches historical average of ~1.3)
            # - Penalize having too many close pairs (too clustered)
            sum_score = max(0, sum_std * 2 - sum_diff)  # Higher is better

            # Target 1-2 close pairs (historical avg is ~1.3)
            if close_pair_count == 0:
                pair_bonus = -20  # Penalty for no close pairs
            elif close_pair_count <= 2:
                pair_bonus = 15  # Good: matches historical pattern
            else:
                pair_bonus = 15 - (close_pair_count - 2) * 5  # Penalty for too clustered

            total_score = sum_score + pair_bonus

            # Accept if within 1.5 std of target and better than current best
            if sum_diff < sum_std * 1.5 and total_score > best_score:
                best_selection = selection_list
                best_score = total_score

        except ValueError:
            continue

    # Fallback with guaranteed close pair injection if no valid selection found
    if best_selection is None:
        sorted_by_weight = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        base_selection = [n for n, _ in sorted_by_weight[:game_config.main_numbers]]

        # Inject a close pair if not present
        if not has_close_pair(base_selection, max_gap=3):
            # Find highest weighted number and add a neighbor within 3
            best_num = base_selection[0]
            neighbors = [best_num + d for d in [-3, -2, -1, 1, 2, 3]
                        if game_config.main_range[0] <= best_num + d <= game_config.main_range[1]
                        and best_num + d not in base_selection]
            if neighbors:
                # Replace lowest weighted number with a neighbor
                base_selection[-1] = random.choice(neighbors)

        best_selection = sorted(base_selection)

    # Bonus numbers (PowerBall)
    bonus_numbers = []
    if game_config.bonus_numbers and game_config.bonus_range:
        all_bonus = [n for d in draws for n in d.bonus_numbers]
        bonus_range = list(range(game_config.bonus_range[0], game_config.bonus_range[1] + 1))

        if all_bonus:
            bonus_freq = Counter(all_bonus)
            bonus_weights = np.array([bonus_freq.get(n, 0) + 1 for n in bonus_range])
            bonus_probs = bonus_weights / bonus_weights.sum()

            bonus_numbers = np.random.choice(
                bonus_range,
                size=game_config.bonus_numbers,
                replace=False,
                p=bonus_probs
            ).tolist()
        else:
            bonus_numbers = random.sample(bonus_range, game_config.bonus_numbers)

    # Build detailed reasoning
    hot_5 = stats['hot_numbers'][:5]
    cold_5 = stats['cold_numbers'][:5]
    close_pairs_in_selection = count_close_pairs(best_selection, max_gap=3)

    reasoning = f"""**Statistical Analysis** ({stats['total_draws']} draws analyzed)

| Metric | Value |
|--------|-------|
| Hot Numbers | {', '.join(map(str, hot_5))} |
| Cold Numbers | {', '.join(map(str, cold_5))} |
| Target Sum | {target_sum:.0f} +/- {sum_std:.0f} |
| Selection Sum | {sum(best_selection)} |
| Close Pairs in Selection | {close_pairs_in_selection} |
| Historical Close Pair Rate | {stats.get('close_pair_rate', 0):.0%} of draws |
| Top Pairs | {', '.join(stats['top_pairs'][:3])} |

**CLOSE PAIR PATTERN APPLIED:** {stats.get('close_pair_rate', 0):.0%} of historical draws contain numbers within 1-3 of each other. This selection includes {close_pairs_in_selection} close pair(s).

**Methodology:** Weighted Monte Carlo sampling combining:
- **Close pair enforcement** (observed in {stats.get('close_pair_rate', 0):.0%} of draws)
- Frequency analysis (hot numbers weighted 2.5x)
- Recency analysis (overdue numbers weighted 1.5x)
- Pair co-occurrence patterns (1.0x)
- Chi-squared deviation from uniform (1.0x)
- Sum constraint targeting historical mean"""

    return Prediction(
        game=game,
        main_numbers=best_selection,
        bonus_numbers=bonus_numbers,
        reasoning=reasoning,
        confidence_note="Statistical patterns do NOT improve odds. Lottery draws are independent random events. Play responsibly."
    )


def _generate_random_prediction(game: str, game_config: GameConfig, reason: str) -> Prediction:
    """Generate a purely random prediction as fallback."""
    main_numbers = sorted(random.sample(
        range(game_config.main_range[0], game_config.main_range[1] + 1),
        game_config.main_numbers
    ))

    bonus_numbers = []
    if game_config.bonus_numbers and game_config.bonus_range:
        bonus_numbers = random.sample(
            range(game_config.bonus_range[0], game_config.bonus_range[1] + 1),
            game_config.bonus_numbers
        )

    return Prediction(
        game=game,
        main_numbers=main_numbers,
        bonus_numbers=bonus_numbers,
        reasoning=reason,
        confidence_note="Random selection. Lottery is random - play responsibly!"
    )


# =============================================================================
# Pattern Analysis (Non-Prediction)
# =============================================================================

def analyze_patterns(draws: List[Draw]) -> dict:
    """Analyze patterns in historical draws for display purposes."""
    if not draws:
        return {"error": "No historical data available"}

    all_main = [n for d in draws for n in d.main_numbers]

    # Frequency analysis
    freq = Counter(all_main)
    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)

    # Consecutive numbers analysis
    consecutive_count = 0
    for draw in draws:
        nums = sorted(draw.main_numbers)
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consecutive_count += 1

    # Sum analysis
    sums = [sum(d.main_numbers) for d in draws]
    avg_sum = sum(sums) / len(sums) if sums else 0

    return {
        "total_draws": len(draws),
        "most_frequent": sorted_freq[:10],
        "least_frequent": sorted_freq[-10:] if len(sorted_freq) > 10 else sorted_freq,
        "average_sum": round(avg_sum, 1),
        "consecutive_pairs_per_draw": round(consecutive_count / len(draws), 2) if draws else 0,
    }


# =============================================================================
# Advanced Analysis with Full JSON Schema Output
# =============================================================================

def run_advanced_analysis(game: str, draws: List[Draw], seed: Optional[int] = None) -> dict:
    """
    Run comprehensive statistical analysis and return JSON schema compliant output.

    This function implements the full analysis pipeline:
    1. Statistical tests (chi-squared, entropy, KL divergence)
    2. Co-occurrence and mutual information analysis
    3. Inferred generative model
    4. Predictions (3-number, 4-number, lucky number)
    5. Backtesting with Monte Carlo simulations

    Args:
        game: Game identifier
        draws: Historical draw data
        seed: Optional RNG seed for reproducibility

    Returns:
        Dictionary matching the required JSON schema
    """
    try:
        from analyzer import LotteryAnalyzer, AnalysisResult

        analyzer = LotteryAnalyzer(game, draws, rng_seed=seed)
        result = analyzer.run_full_analysis()
        return result.to_dict()

    except ImportError as e:
        logger.error(f"Analyzer module not available: {e}")
        # Fallback to basic prediction
        return _basic_analysis_fallback(game, draws)

    except Exception as e:
        logger.error(f"Advanced analysis failed: {e}")
        return _basic_analysis_fallback(game, draws)


def _basic_analysis_fallback(game: str, draws: List[Draw]) -> dict:
    """Fallback when advanced analyzer is not available."""
    from datetime import datetime

    game_config = get_game(game)
    stats = compute_enhanced_stats(draws, game_config)

    # Simple predictions from hot numbers
    hot = stats['hot_numbers'][:10]
    three_numbers = sorted(hot[:3]) if len(hot) >= 3 else list(range(1, 4))
    four_numbers = sorted(hot[:4]) if len(hot) >= 4 else list(range(1, 5))

    # Lucky number
    if game_config.bonus_range:
        lucky = random.randint(game_config.bonus_range[0], game_config.bonus_range[1])
    else:
        lucky = random.randint(game_config.main_range[0], game_config.main_range[1])

    return {
        "game": game,
        "coverage_days": len(draws),
        "coverage_percent": round(len(draws) / 730 * 100, 1),
        "inferred_model": {
            "type": "categorical",
            "summary": f"Basic frequency model from {len(draws)} draws (fallback mode)",
            "confidence": 0.5,
            "model_parameters": {
                "top_10_probabilities": [
                    {"number": n, "probability": stats['frequency'].get(n, 0) / max(sum(stats['frequency'].values()), 1)}
                    for n in hot[:10]
                ]
            }
        },
        "predictions": {
            "three_numbers": three_numbers,
            "four_numbers": four_numbers,
            "lucky_number": lucky,
            "top_candidates_main": [{"num": n, "score": 0.1} for n in hot[:10]],
            "top_candidates_lucky": [{"num": n, "score": 0.1} for n in range(1, 11)]
        },
        "backtest": {
            "last_100_hit_rate_main_top3": 0.0,
            "ci_hit_rate_main_top3": [0.0, 0.0],
            "random_baseline_hit_rate": 0.0,
            "simulations": 0,
            "note": "Backtest unavailable in fallback mode"
        },
        "reasoning": f"Fallback analysis based on {len(draws)} draws. Hot numbers: {hot[:5]}",
        "disclaimer": "Entertainment only — probabilistic analysis. No guaranteed outcomes. Do not take financial risks based on this output.",
        "generated_at": datetime.now().isoformat(),
        "data_sources": ["local storage"],
        "audit_notes": "Running in fallback mode - advanced analyzer unavailable"
    }


def format_analysis_for_cli(analysis: dict) -> str:
    """Format analysis result for CLI display."""
    pred = analysis.get('predictions', {})
    model = analysis.get('inferred_model', {})
    backtest = analysis.get('backtest', {})

    output = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    ADVANCED STATISTICAL ANALYSIS                      ║
╚══════════════════════════════════════════════════════════════════════╝

📊 DATA COVERAGE
   • Draws analyzed: {analysis.get('coverage_days', 0)}
   • Coverage: {analysis.get('coverage_percent', 0):.1f}% of 2-year target
   • Sources: {', '.join(analysis.get('data_sources', ['N/A']))}

🔬 INFERRED MODEL
   • Type: {model.get('type', 'unknown').upper()}
   • Confidence: {model.get('confidence', 0):.1%}
   • {model.get('summary', 'No summary available')}

🎯 PREDICTIONS
   ┌─────────────────────────────────────────┐
   │  3-Number Set:  {' - '.join(f'{n:02d}' for n in pred.get('three_numbers', []))}               │
   │  4-Number Set:  {' - '.join(f'{n:02d}' for n in pred.get('four_numbers', []))}          │
   │  Lucky Number:  {pred.get('lucky_number', 0):02d}                         │
   └─────────────────────────────────────────┘

📈 TOP CANDIDATES (Main Numbers)
   {_format_top_candidates(pred.get('top_candidates_main', []))}

🎰 BACKTEST RESULTS (Last 100 Draws)
   • Hit Rate (Top 3): {backtest.get('last_100_hit_rate_main_top3', 0):.1%}
   • 95% CI: [{backtest.get('ci_hit_rate_main_top3', [0,0])[0]:.1%}, {backtest.get('ci_hit_rate_main_top3', [0,0])[1]:.1%}]
   • Random Baseline: {backtest.get('random_baseline_hit_rate', 0):.1%}
   • Monte Carlo Sims: {backtest.get('simulations', 0):,}

💡 REASONING
{analysis.get('reasoning', 'No reasoning available')}

⚠️  DISCLAIMER
{analysis.get('disclaimer', 'Entertainment only.')}

Generated: {analysis.get('generated_at', 'N/A')}
"""
    return output


def _format_top_candidates(candidates: List[dict]) -> str:
    """Format top candidates list."""
    if not candidates:
        return "   No candidates available"

    lines = []
    for i, c in enumerate(candidates[:5], 1):
        bar = '█' * int(c.get('score', 0) * 50)
        lines.append(f"   {i}. #{c.get('num', 0):02d} [{bar:<25}] {c.get('score', 0):.4f}")

    return '\n'.join(lines)
