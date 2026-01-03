"""
Backtesting framework for lottery prediction strategies.

Provides:
- Walk-forward backtesting
- Monte Carlo baseline simulations
- Bootstrap confidence intervals
- Statistical significance testing
- Performance metrics (hit rate, expected value, variance)
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime

import numpy as np
from scipy import stats as scipy_stats

from models import Draw, Prediction
from config import get_game, GameConfig


logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BacktestResult:
    """Results from a single backtest run."""
    strategy_name: str
    game: str
    total_predictions: int
    matches_distribution: Dict[int, int]  # {match_count: frequency}
    hit_rate_any: float  # % predictions with at least 1 match
    hit_rate_2plus: float  # % predictions with 2+ matches
    hit_rate_3plus: float  # % predictions with 3+ matches
    avg_matches: float
    expected_random: float  # Expected matches under random selection
    improvement_vs_random: float  # Percentage improvement
    p_value: float  # Statistical significance vs random
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    timestamp: datetime = field(default_factory=datetime.now)

    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if results are statistically significant."""
        return self.p_value < alpha

    def summary(self) -> str:
        """Generate a text summary of results."""
        sig = "YES" if self.is_significant() else "NO"
        return f"""
Backtest Results: {self.strategy_name}
Game: {self.game}
Predictions: {self.total_predictions}
Average Matches: {self.avg_matches:.3f}
Expected (Random): {self.expected_random:.3f}
Improvement: {self.improvement_vs_random:+.1f}%
Hit Rate (1+): {self.hit_rate_any:.1%}
Hit Rate (3+): {self.hit_rate_3plus:.1%}
P-Value: {self.p_value:.4f}
Significant: {sig}
"""


@dataclass
class MonteCarloBaseline:
    """Baseline statistics from Monte Carlo simulation."""
    game: str
    n_simulations: int
    distribution: Dict[int, float]  # {matches: probability}
    expected_matches: float
    std_matches: float
    hit_rate_any: float
    hit_rate_2plus: float
    hit_rate_3plus: float
    percentiles: Dict[int, float]  # {percentile: value}


# =============================================================================
# Backtesting Functions
# =============================================================================

def backtest_strategy(
    draws: List[Draw],
    predict_fn: Callable[[str, List[Draw]], Prediction],
    game: str,
    train_size: int = 30,
    test_size: int = 20,
) -> BacktestResult:
    """
    Walk-forward backtest: train on N draws, predict next, compare to actual.

    This simulates real-world usage where predictions are made based only on
    past data, then evaluated against actual outcomes.

    Args:
        draws: Historical draws (newest first)
        predict_fn: Prediction function to test (signature: (game, draws) -> Prediction)
        game: Game identifier
        train_size: Number of historical draws to use for each prediction
        test_size: Number of predictions to make

    Returns:
        BacktestResult with performance metrics
    """
    game_config = get_game(game)

    if len(draws) < train_size + test_size:
        raise ValueError(
            f"Insufficient data: need {train_size + test_size} draws, "
            f"have {len(draws)}"
        )

    logger.info(f"Starting backtest: {predict_fn.__name__} on {game}")
    logger.info(f"Train size: {train_size}, Test size: {test_size}")

    matches_distribution = Counter()
    total_matches = 0
    all_match_counts = []

    for i in range(test_size):
        # Training data: draws from i+1 to i+train_size+1 (skip the "future" draw)
        test_idx = i
        train_start = i + 1
        train_end = train_start + train_size

        train_draws = draws[train_start:train_end]
        actual_draw = draws[test_idx]

        try:
            # Generate prediction using only "past" data
            prediction = predict_fn(game, train_draws)

            # Count matches
            actual_set = set(actual_draw.main_numbers)
            predicted_set = set(prediction.main_numbers)
            match_count = len(actual_set & predicted_set)

            matches_distribution[match_count] += 1
            total_matches += match_count
            all_match_counts.append(match_count)

            logger.debug(
                f"Test {i+1}: Predicted {prediction.main_numbers}, "
                f"Actual {actual_draw.main_numbers}, Matches: {match_count}"
            )

        except Exception as e:
            logger.warning(f"Prediction failed for test {i+1}: {e}")
            matches_distribution[0] += 1
            all_match_counts.append(0)

    # Calculate statistics
    avg_matches = total_matches / test_size if test_size > 0 else 0

    hit_rate_any = sum(
        v for k, v in matches_distribution.items() if k >= 1
    ) / test_size if test_size > 0 else 0

    hit_rate_2plus = sum(
        v for k, v in matches_distribution.items() if k >= 2
    ) / test_size if test_size > 0 else 0

    hit_rate_3plus = sum(
        v for k, v in matches_distribution.items() if k >= 3
    ) / test_size if test_size > 0 else 0

    # Calculate expected matches under random selection (hypergeometric)
    n_range = game_config.main_range[1] - game_config.main_range[0] + 1
    n_pick = game_config.main_numbers
    expected_random = (n_pick * n_pick) / n_range

    improvement = ((avg_matches - expected_random) / expected_random * 100
                   if expected_random > 0 else 0)

    # Chi-squared test vs random baseline
    p_value = _calculate_p_value(
        matches_distribution, test_size, n_range, n_pick
    )

    # Bootstrap confidence interval
    ci = _bootstrap_confidence_interval(all_match_counts)

    result = BacktestResult(
        strategy_name=predict_fn.__name__,
        game=game,
        total_predictions=test_size,
        matches_distribution=dict(matches_distribution),
        hit_rate_any=hit_rate_any,
        hit_rate_2plus=hit_rate_2plus,
        hit_rate_3plus=hit_rate_3plus,
        avg_matches=avg_matches,
        expected_random=expected_random,
        improvement_vs_random=improvement,
        p_value=p_value,
        confidence_interval=ci,
    )

    logger.info(f"Backtest complete: avg={avg_matches:.3f}, p={p_value:.4f}")
    return result


def _calculate_p_value(
    observed_dist: Dict[int, int],
    n_tests: int,
    n_range: int,
    n_pick: int
) -> float:
    """Calculate p-value using chi-squared test against hypergeometric baseline."""
    try:
        # Build observed frequency array
        observed = [observed_dist.get(k, 0) for k in range(n_pick + 1)]

        # Calculate expected frequencies under hypergeometric distribution
        expected = []
        for k in range(n_pick + 1):
            prob = scipy_stats.hypergeom.pmf(k, n_range, n_pick, n_pick)
            expected.append(prob * n_tests)

        # Ensure no zero expected values (combine small categories if needed)
        expected = [max(e, 0.5) for e in expected]

        # Chi-squared test
        chi2, p_value = scipy_stats.chisquare(observed, expected)
        return float(p_value)

    except Exception as e:
        logger.warning(f"P-value calculation failed: {e}")
        return 1.0


def _bootstrap_confidence_interval(
    match_counts: List[int],
    n_bootstrap: int = 1000,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """Calculate bootstrap confidence interval for mean matches."""
    if len(match_counts) < 2:
        return (0.0, 0.0)

    try:
        bootstrap_means = []
        n = len(match_counts)

        for _ in range(n_bootstrap):
            sample = np.random.choice(match_counts, size=n, replace=True)
            bootstrap_means.append(np.mean(sample))

        alpha = 1 - confidence
        lower = float(np.percentile(bootstrap_means, alpha / 2 * 100))
        upper = float(np.percentile(bootstrap_means, (1 - alpha / 2) * 100))

        return (lower, upper)

    except Exception as e:
        logger.warning(f"Bootstrap CI calculation failed: {e}")
        return (0.0, 0.0)


# =============================================================================
# Monte Carlo Simulation
# =============================================================================

def monte_carlo_baseline(
    game: str,
    n_simulations: int = 10000
) -> MonteCarloBaseline:
    """
    Monte Carlo simulation of random selection hit rates.
    Establishes baseline for comparison.

    Args:
        game: Game identifier
        n_simulations: Number of simulations to run

    Returns:
        MonteCarloBaseline with distribution statistics
    """
    game_config = get_game(game)
    n_range = game_config.main_range[1] - game_config.main_range[0] + 1
    n_pick = game_config.main_numbers

    logger.info(f"Running Monte Carlo baseline: {n_simulations} simulations")

    matches_distribution = Counter()
    all_matches = []

    for _ in range(n_simulations):
        # Random "actual" draw
        actual = set(np.random.choice(
            range(1, n_range + 1), n_pick, replace=False
        ))
        # Random prediction
        predicted = set(np.random.choice(
            range(1, n_range + 1), n_pick, replace=False
        ))

        matches = len(actual & predicted)
        matches_distribution[matches] += 1
        all_matches.append(matches)

    # Convert to probabilities
    distribution = {
        k: v / n_simulations
        for k, v in matches_distribution.items()
    }

    # Calculate statistics
    expected_matches = np.mean(all_matches)
    std_matches = np.std(all_matches)

    hit_rate_any = sum(
        v for k, v in distribution.items() if k >= 1
    )
    hit_rate_2plus = sum(
        v for k, v in distribution.items() if k >= 2
    )
    hit_rate_3plus = sum(
        v for k, v in distribution.items() if k >= 3
    )

    # Percentiles
    percentiles = {
        p: float(np.percentile(all_matches, p))
        for p in [5, 25, 50, 75, 95]
    }

    logger.info(f"Monte Carlo complete: expected={expected_matches:.3f}")

    return MonteCarloBaseline(
        game=game,
        n_simulations=n_simulations,
        distribution=distribution,
        expected_matches=float(expected_matches),
        std_matches=float(std_matches),
        hit_rate_any=hit_rate_any,
        hit_rate_2plus=hit_rate_2plus,
        hit_rate_3plus=hit_rate_3plus,
        percentiles=percentiles,
    )


# =============================================================================
# Comparison Functions
# =============================================================================

def compare_strategies(
    draws: List[Draw],
    strategies: Dict[str, Callable],
    game: str,
    train_size: int = 30,
    test_size: int = 20,
) -> Dict[str, BacktestResult]:
    """
    Compare multiple prediction strategies.

    Args:
        draws: Historical draws
        strategies: Dict of {name: predict_function}
        game: Game identifier
        train_size: Training window size
        test_size: Number of test predictions

    Returns:
        Dict of {strategy_name: BacktestResult}
    """
    results = {}

    for name, predict_fn in strategies.items():
        logger.info(f"Testing strategy: {name}")
        try:
            result = backtest_strategy(
                draws, predict_fn, game, train_size, test_size
            )
            result.strategy_name = name  # Override function name
            results[name] = result
        except Exception as e:
            logger.error(f"Strategy {name} failed: {e}")

    return results


def calculate_expected_value(
    result: BacktestResult,
    prize_structure: Dict[int, float],
    ticket_cost: float = 5.0
) -> float:
    """
    Calculate expected value per ticket based on backtest results.

    Args:
        result: Backtest results
        prize_structure: Dict of {matches: prize_amount}
        ticket_cost: Cost per ticket (default R5 for SA Lotto)

    Returns:
        Expected value per ticket (negative = expected loss)
    """
    total_predictions = result.total_predictions
    if total_predictions == 0:
        return -ticket_cost

    expected_winnings = sum(
        (count / total_predictions) * prize_structure.get(matches, 0)
        for matches, count in result.matches_distribution.items()
    )

    return expected_winnings - ticket_cost


# =============================================================================
# Utility Functions
# =============================================================================

def generate_random_prediction(game: str, draws: List[Draw]) -> Prediction:
    """Generate a purely random prediction for baseline comparison."""
    from predictor import _generate_random_prediction
    game_config = get_game(game)
    return _generate_random_prediction(game, game_config, "Random baseline")


def theoretical_match_probabilities(game: str) -> Dict[int, float]:
    """
    Calculate theoretical probability of matching k numbers.
    Uses hypergeometric distribution.
    """
    game_config = get_game(game)
    N = game_config.main_range[1] - game_config.main_range[0] + 1  # Total numbers
    K = game_config.main_numbers  # Numbers drawn
    n = game_config.main_numbers  # Numbers picked

    probs = {}
    for k in range(K + 1):
        probs[k] = float(scipy_stats.hypergeom.pmf(k, N, K, n))

    return probs
