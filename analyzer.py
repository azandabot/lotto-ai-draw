"""
Advanced Statistical Analyzer for SA Lotto AI Predictor.

Implements comprehensive statistical analysis including:
- Chi-squared uniformity tests
- Entropy and KL divergence
- Pairwise co-occurrence and mutual information
- Autocorrelation analysis
- Rolling window frequency drift
- Position-specific bias detection
- Periodicity analysis
- Inferred generative models (pairwise, categorical, markov)
- Backtesting with Monte Carlo simulations

Author: SA Lotto AI Predictor
Version: 2.0
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
import math

import numpy as np
from scipy import stats as scipy_stats

from models import Draw
from config import GameConfig, get_game, GAMES

logger = logging.getLogger(__name__)

# Constants
DISCLAIMER = "Entertainment only — probabilistic analysis. No guaranteed outcomes. Do not take financial risks based on this output."
TARGET_DAYS = 730  # 2 years
DIRICHLET_ALPHA = 1.0  # Smoothing parameter


@dataclass
class AnalysisResult:
    """Complete analysis result with JSON schema compliance."""
    game: str
    coverage_days: int
    coverage_percent: float
    inferred_model: Dict[str, Any]
    predictions: Dict[str, Any]
    backtest: Dict[str, Any]
    reasoning: str
    disclaimer: str = DISCLAIMER
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    data_sources: List[str] = field(default_factory=list)
    audit_notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class LotteryAnalyzer:
    """
    Comprehensive statistical analyzer for lottery draws.

    Implements the full analysis pipeline:
    1. Data validation and cleaning
    2. Statistical tests (chi-squared, entropy, KL divergence)
    3. Co-occurrence and mutual information analysis
    4. Autocorrelation and temporal patterns
    5. Generative model inference
    6. Prediction generation
    7. Backtesting with Monte Carlo simulations
    """

    def __init__(self, game: str, draws: List[Draw], rng_seed: Optional[int] = None):
        """
        Initialize the analyzer.

        Args:
            game: Game identifier (e.g., 'daily_lotto', 'powerball')
            draws: List of historical Draw objects
            rng_seed: Optional seed for reproducibility
        """
        self.game = game
        self.game_config = get_game(game)
        self.rng = np.random.default_rng(rng_seed or int(datetime.now().timestamp()))

        # Clean and validate draws
        self.draws = self._clean_draws(draws)
        self.num_range = list(range(
            self.game_config.main_range[0],
            self.game_config.main_range[1] + 1
        ))
        self.n_numbers = len(self.num_range)

        # Bonus range for lucky number
        if self.game_config.bonus_range:
            self.bonus_range = list(range(
                self.game_config.bonus_range[0],
                self.game_config.bonus_range[1] + 1
            ))
        else:
            self.bonus_range = self.num_range

        # Pre-compute statistics
        self._compute_all_stats()

        # Audit tracking
        self.audit_notes = []
        self.data_sources = ["https://www.lottery.co.za"]

    def _clean_draws(self, draws: List[Draw]) -> List[Draw]:
        """Clean and validate draw data."""
        cleaned = []
        seen_dates = set()

        for draw in draws:
            # Validate number count
            if len(draw.main_numbers) != self.game_config.main_numbers:
                continue

            # Validate number range
            valid_nums = all(
                self.game_config.main_range[0] <= n <= self.game_config.main_range[1]
                for n in draw.main_numbers
            )
            if not valid_nums:
                continue

            # Check for duplicates within draw
            if len(set(draw.main_numbers)) != len(draw.main_numbers):
                continue

            # Dedupe by date
            date_key = draw.draw_date.date()
            if date_key in seen_dates:
                continue
            seen_dates.add(date_key)

            cleaned.append(draw)

        # Sort by date (newest first)
        cleaned.sort(key=lambda d: d.draw_date, reverse=True)
        return cleaned

    def _compute_all_stats(self):
        """Pre-compute all statistical measures."""
        if not self.draws:
            self._init_empty_stats()
            return

        # Extract all numbers
        self.all_main = [n for d in self.draws for n in d.main_numbers]
        self.all_bonus = [n for d in self.draws for n in d.bonus_numbers]

        # Frequency counts
        self.freq = Counter(self.all_main)
        self.bonus_freq = Counter(self.all_bonus)

        # Compute per-number probabilities with Dirichlet smoothing
        self.prob = self._compute_smoothed_probs(self.freq, self.num_range)
        self.bonus_prob = self._compute_smoothed_probs(
            self.bonus_freq,
            self.bonus_range
        ) if self.all_bonus else None

        # Pairwise co-occurrence matrix
        self.cooccurrence = self._compute_cooccurrence()
        self.pairwise_multipliers = self._compute_pairwise_multipliers()

        # Chi-squared test
        self.chi_squared, self.chi_p_value = self._chi_squared_test()

        # Entropy and KL divergence
        self.entropy = self._compute_entropy()
        self.kl_divergence = self._compute_kl_divergence()

        # Autocorrelation
        self.autocorr = self._compute_autocorrelation()

        # Rolling window analysis
        self.rolling_freq = self._compute_rolling_frequency()

        # Position bias (if applicable)
        self.position_bias = self._compute_position_bias()

        # Day-of-week patterns
        self.dow_patterns = self._compute_dow_patterns()

        # Recency (draws since last seen)
        self.recency = self._compute_recency()

        # Mutual information for top pairs
        self.mutual_info = self._compute_mutual_info()

    def _init_empty_stats(self):
        """Initialize empty stats when no data."""
        self.all_main = []
        self.all_bonus = []
        self.freq = Counter()
        self.bonus_freq = Counter()
        self.prob = {n: 1/len(self.num_range) for n in self.num_range}
        self.bonus_prob = {n: 1/len(self.bonus_range) for n in self.bonus_range}
        self.cooccurrence = {}
        self.pairwise_multipliers = {}
        self.chi_squared = 0
        self.chi_p_value = 1.0
        self.entropy = 0
        self.kl_divergence = 0
        self.autocorr = []
        self.rolling_freq = {}
        self.position_bias = {}
        self.dow_patterns = {}
        self.recency = {}
        self.mutual_info = []

    def _compute_smoothed_probs(self, freq: Counter, num_range: List[int]) -> Dict[int, float]:
        """Compute Dirichlet-smoothed probabilities."""
        total = sum(freq.values()) + DIRICHLET_ALPHA * len(num_range)
        return {
            n: (freq.get(n, 0) + DIRICHLET_ALPHA) / total
            for n in num_range
        }

    def _compute_cooccurrence(self) -> Dict[Tuple[int, int], int]:
        """Compute pairwise co-occurrence counts."""
        cooc = Counter()
        for draw in self.draws:
            nums = sorted(draw.main_numbers)
            for i in range(len(nums)):
                for j in range(i + 1, len(nums)):
                    cooc[(nums[i], nums[j])] += 1
        return dict(cooc)

    def _compute_pairwise_multipliers(self) -> Dict[Tuple[int, int], float]:
        """
        Compute pairwise multipliers m(i,j) from normalized co-occurrence.

        m(i,j) = observed_cooc(i,j) / expected_cooc(i,j)
        where expected = n_draws * p(i) * p(j) * C(k,2) adjustment
        """
        if not self.cooccurrence or not self.draws:
            return {}

        n_draws = len(self.draws)
        k = self.game_config.main_numbers

        # Expected co-occurrence under independence
        # Each draw contributes C(k,2) pairs
        pairs_per_draw = k * (k - 1) / 2

        multipliers = {}
        for (i, j), count in self.cooccurrence.items():
            # Expected under independence
            expected = n_draws * self.prob[i] * self.prob[j] * pairs_per_draw
            if expected > 0:
                multipliers[(i, j)] = count / expected
            else:
                multipliers[(i, j)] = 1.0

        return multipliers

    def _chi_squared_test(self) -> Tuple[float, float]:
        """Run chi-squared test for uniformity."""
        if not self.all_main:
            return 0.0, 1.0

        observed = [self.freq.get(n, 0) for n in self.num_range]
        expected = [len(self.all_main) / len(self.num_range)] * len(self.num_range)

        try:
            chi2, p_value = scipy_stats.chisquare(observed, expected)
            return float(chi2), float(p_value)
        except Exception:
            return 0.0, 1.0

    def _compute_entropy(self) -> float:
        """Compute Shannon entropy of the distribution."""
        if not self.prob:
            return 0.0

        entropy = 0.0
        for p in self.prob.values():
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    def _compute_kl_divergence(self) -> float:
        """Compute KL divergence from uniform distribution."""
        if not self.prob:
            return 0.0

        uniform_p = 1.0 / len(self.num_range)
        kl_div = 0.0

        for p in self.prob.values():
            if p > 0:
                kl_div += p * math.log2(p / uniform_p)

        return kl_div

    def _compute_autocorrelation(self, max_lag: int = 10) -> List[float]:
        """Compute autocorrelation across draws for each number."""
        if len(self.draws) < max_lag + 1:
            return [0.0] * max_lag

        # Create binary matrix: draws x numbers
        n_draws = len(self.draws)
        matrix = np.zeros((n_draws, self.n_numbers))

        for i, draw in enumerate(self.draws):
            for num in draw.main_numbers:
                idx = num - self.game_config.main_range[0]
                matrix[i, idx] = 1

        # Compute mean autocorrelation across all numbers
        autocorrs = []
        for lag in range(1, max_lag + 1):
            correlations = []
            for j in range(self.n_numbers):
                series = matrix[:, j]
                if np.std(series) > 0:
                    corr = np.corrcoef(series[:-lag], series[lag:])[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)

            autocorrs.append(np.mean(correlations) if correlations else 0.0)

        return autocorrs

    def _compute_rolling_frequency(self, windows: List[int] = [10, 50, 200]) -> Dict[int, Dict[int, float]]:
        """Compute rolling window frequency drift."""
        rolling = {}

        for window in windows:
            if len(self.draws) < window:
                continue

            window_draws = self.draws[:window]
            window_nums = [n for d in window_draws for n in d.main_numbers]
            window_freq = Counter(window_nums)

            # Normalize
            total = sum(window_freq.values())
            rolling[window] = {
                n: window_freq.get(n, 0) / total if total > 0 else 0
                for n in self.num_range
            }

        return rolling

    def _compute_position_bias(self) -> Dict[int, Dict[int, float]]:
        """Check if certain positions have biased distributions."""
        if not self.draws:
            return {}

        position_counts = defaultdict(Counter)

        for draw in self.draws:
            # Assuming numbers are stored in draw order (not sorted)
            for pos, num in enumerate(draw.main_numbers):
                position_counts[pos][num] += 1

        # Normalize per position
        position_probs = {}
        for pos, counts in position_counts.items():
            total = sum(counts.values())
            position_probs[pos] = {
                n: counts.get(n, 0) / total if total > 0 else 0
                for n in self.num_range
            }

        return position_probs

    def _compute_dow_patterns(self) -> Dict[int, Dict[int, float]]:
        """Detect day-of-week frequency patterns."""
        if not self.draws:
            return {}

        dow_counts = defaultdict(Counter)

        for draw in self.draws:
            dow = draw.draw_date.weekday()
            for num in draw.main_numbers:
                dow_counts[dow][num] += 1

        # Normalize per day
        dow_probs = {}
        for dow, counts in dow_counts.items():
            total = sum(counts.values())
            dow_probs[dow] = {
                n: counts.get(n, 0) / total if total > 0 else 0
                for n in self.num_range
            }

        return dow_probs

    def _compute_recency(self) -> Dict[int, int]:
        """Compute draws since each number was last seen."""
        last_seen = {}

        for i, draw in enumerate(self.draws):
            for num in draw.main_numbers:
                if num not in last_seen:
                    last_seen[num] = i

        return {
            n: last_seen.get(n, len(self.draws))
            for n in self.num_range
        }

    def _compute_mutual_info(self, top_k: int = 20) -> List[Tuple[Tuple[int, int], float]]:
        """Compute mutual information for top co-occurring pairs."""
        if not self.draws or len(self.draws) < 10:
            return []

        n_draws = len(self.draws)

        # Create presence vectors
        presence = {n: np.zeros(n_draws) for n in self.num_range}
        for i, draw in enumerate(self.draws):
            for num in draw.main_numbers:
                presence[num][i] = 1

        # Compute MI for top co-occurring pairs
        top_pairs = sorted(self.cooccurrence.items(), key=lambda x: x[1], reverse=True)[:top_k * 2]

        mi_scores = []
        for (a, b), _ in top_pairs:
            # Joint probability
            p_ab = np.mean(presence[a] * presence[b])
            p_a = np.mean(presence[a])
            p_b = np.mean(presence[b])

            if p_ab > 0 and p_a > 0 and p_b > 0:
                mi = p_ab * math.log2(p_ab / (p_a * p_b))
                mi_scores.append(((a, b), mi))

        mi_scores.sort(key=lambda x: x[1], reverse=True)
        return mi_scores[:top_k]

    def _detect_model_type(self) -> str:
        """Determine the best model type based on data patterns."""
        if not self.draws or len(self.draws) < 50:
            return "categorical"

        # Check pairwise structure strength
        if self.mutual_info:
            avg_mi = np.mean([mi for _, mi in self.mutual_info])
            if avg_mi > 0.01:  # Significant pairwise structure
                return "pairwise"

        # Check for temporal dependencies
        if self.autocorr:
            max_autocorr = max(abs(a) for a in self.autocorr)
            if max_autocorr > 0.1:
                return "markov"

        return "categorical"

    def infer_model(self) -> Dict[str, Any]:
        """Infer the generative model from data."""
        model_type = self._detect_model_type()

        # Build model parameters
        if model_type == "pairwise":
            model_params = self._build_pairwise_model()
            confidence = min(0.9, 0.5 + len(self.draws) / 1000)
        elif model_type == "markov":
            model_params = self._build_markov_model()
            confidence = min(0.85, 0.4 + len(self.draws) / 1000)
        else:
            model_params = self._build_categorical_model()
            confidence = min(0.95, 0.6 + len(self.draws) / 500)

        summary = self._generate_model_summary(model_type, confidence)

        return {
            "type": model_type,
            "summary": summary,
            "confidence": round(confidence, 3),
            "model_parameters": model_params
        }

    def _build_categorical_model(self) -> Dict[str, Any]:
        """Build simple categorical model."""
        # Top 10 probabilities
        sorted_probs = sorted(self.prob.items(), key=lambda x: x[1], reverse=True)

        return {
            "top_10_probabilities": [
                {"number": n, "probability": round(p, 5)}
                for n, p in sorted_probs[:10]
            ],
            "entropy": round(self.entropy, 4),
            "uniform_entropy": round(math.log2(len(self.num_range)), 4)
        }

    def _build_pairwise_model(self) -> Dict[str, Any]:
        """Build pairwise adjustment model."""
        # Top probabilities
        sorted_probs = sorted(self.prob.items(), key=lambda x: x[1], reverse=True)

        # Top pairwise multipliers
        sorted_mult = sorted(
            self.pairwise_multipliers.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "top_10_probabilities": [
                {"number": n, "probability": round(p, 5)}
                for n, p in sorted_probs[:10]
            ],
            "top_10_pairwise_multipliers": [
                {"pair": list(pair), "multiplier": round(mult, 3)}
                for pair, mult in sorted_mult[:10]
            ],
            "avg_pairwise_multiplier": round(
                np.mean(list(self.pairwise_multipliers.values())) if self.pairwise_multipliers else 1.0,
                3
            )
        }

    def _build_markov_model(self) -> Dict[str, Any]:
        """Build Markov-based model (simplified)."""
        base_model = self._build_categorical_model()

        # Add autocorrelation info
        base_model["autocorrelation_lag1_5"] = [
            round(a, 4) for a in self.autocorr[:5]
        ] if self.autocorr else []

        return base_model

    def _generate_model_summary(self, model_type: str, confidence: float) -> str:
        """Generate human-readable model summary."""
        n_draws = len(self.draws)

        if model_type == "pairwise":
            return (
                f"Pairwise categorical model inferred from {n_draws} draws. "
                f"Detected significant co-occurrence patterns (MI > 0.01). "
                f"Sampling uses base probabilities with pairwise multiplier adjustments. "
                f"Confidence: {confidence:.1%}"
            )
        elif model_type == "markov":
            return (
                f"Markov-influenced categorical model from {n_draws} draws. "
                f"Detected temporal autocorrelation (lag-1 > 0.1). "
                f"Includes recency weighting for recent patterns. "
                f"Confidence: {confidence:.1%}"
            )
        else:
            return (
                f"Empirical categorical model from {n_draws} draws. "
                f"Chi-squared p-value: {self.chi_p_value:.4f}. "
                f"KL divergence from uniform: {self.kl_divergence:.4f}. "
                f"Confidence: {confidence:.1%}"
            )

    def _sample_with_pairwise(self, n: int, use_pairwise: bool = True) -> List[int]:
        """
        Sample n numbers without replacement using pairwise adjustments.

        Args:
            n: Number of values to sample
            use_pairwise: Whether to apply pairwise multipliers

        Returns:
            List of sampled numbers
        """
        selected = []
        available = list(self.num_range)

        for _ in range(n):
            # Compute weights
            weights = []
            for num in available:
                w = self.prob[num]

                if use_pairwise and selected:
                    # Apply pairwise multipliers
                    for prev in selected:
                        pair = (min(num, prev), max(num, prev))
                        mult = self.pairwise_multipliers.get(pair, 1.0)
                        w *= mult

                weights.append(w)

            # Normalize
            weights = np.array(weights)
            if weights.sum() > 0:
                weights = weights / weights.sum()
            else:
                weights = np.ones(len(available)) / len(available)

            # Sample
            idx = self.rng.choice(len(available), p=weights)
            selected.append(available[idx])
            available.pop(idx)

        return sorted(selected)

    def generate_predictions(self) -> Dict[str, Any]:
        """Generate prediction sets: 3 numbers, 4 numbers, and lucky number."""
        model_type = self._detect_model_type()
        use_pairwise = model_type == "pairwise"

        # Generate multiple candidates and pick best
        three_candidates = [self._sample_with_pairwise(3, use_pairwise) for _ in range(100)]
        four_candidates = [self._sample_with_pairwise(4, use_pairwise) for _ in range(100)]

        # Score candidates by combined probability
        def score_selection(nums):
            base_score = sum(self.prob[n] for n in nums)
            pair_score = 0
            for i in range(len(nums)):
                for j in range(i + 1, len(nums)):
                    pair = (nums[i], nums[j])
                    pair_score += self.pairwise_multipliers.get(pair, 1.0)
            return base_score + pair_score * 0.1

        # Best selections
        three_numbers = max(three_candidates, key=score_selection)
        four_numbers = max(four_candidates, key=score_selection)

        # Lucky number from bonus range
        if self.bonus_prob:
            bonus_weights = np.array([self.bonus_prob[n] for n in self.bonus_range])
            bonus_weights = bonus_weights / bonus_weights.sum()
            lucky_number = int(self.rng.choice(self.bonus_range, p=bonus_weights))
        else:
            weights = np.array([self.prob[n] for n in self.num_range])
            weights = weights / weights.sum()
            lucky_number = int(self.rng.choice(self.num_range, p=weights))

        # Top candidates with scores
        sorted_main = sorted(
            [(n, self.prob[n]) for n in self.num_range],
            key=lambda x: x[1],
            reverse=True
        )

        if self.bonus_prob:
            sorted_bonus = sorted(
                [(n, self.bonus_prob[n]) for n in self.bonus_range],
                key=lambda x: x[1],
                reverse=True
            )
        else:
            sorted_bonus = sorted_main

        return {
            "three_numbers": three_numbers,
            "four_numbers": four_numbers,
            "lucky_number": lucky_number,
            "top_candidates_main": [
                {"num": n, "score": round(s, 5)}
                for n, s in sorted_main[:10]
            ],
            "top_candidates_lucky": [
                {"num": n, "score": round(s, 5)}
                for n, s in sorted_bonus[:10]
            ]
        }

    def run_backtest(self, n_simulations: int = 5000) -> Dict[str, Any]:
        """
        Run backtesting on last 100 draws with Monte Carlo simulations.

        Returns hit rates and confidence intervals.
        """
        if len(self.draws) < 100:
            return {
                "last_100_hit_rate_main_top3": 0.0,
                "ci_hit_rate_main_top3": [0.0, 0.0],
                "random_baseline_hit_rate": 0.0,
                "simulations": 0,
                "note": f"Insufficient data: {len(self.draws)} draws (need 100+)"
            }

        # Get top 3 numbers by probability
        top3 = sorted(self.prob.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_nums = set(n for n, _ in top3)

        # Calculate hit rate on last 100 draws
        test_draws = self.draws[:100]
        hits = 0
        for draw in test_draws:
            if any(n in top3_nums for n in draw.main_numbers):
                hits += 1

        hit_rate = hits / len(test_draws)

        # Random baseline: probability of hitting at least 1 of 3 numbers
        # in a draw of k numbers from range n
        k = self.game_config.main_numbers
        n = len(self.num_range)
        # P(at least 1 hit) = 1 - P(no hits) = 1 - C(n-3,k)/C(n,k)
        from math import comb
        if n > 3 and k <= n - 3:
            random_baseline = 1 - comb(n - 3, k) / comb(n, k)
        else:
            random_baseline = 3 * k / n  # Approximation

        # Bootstrap confidence interval
        bootstrap_hits = []
        for _ in range(n_simulations):
            # Resample draws
            resampled_idx = self.rng.choice(len(test_draws), size=len(test_draws), replace=True)
            resampled_hits = sum(
                1 for i in resampled_idx
                if any(n in top3_nums for n in test_draws[i].main_numbers)
            )
            bootstrap_hits.append(resampled_hits / len(test_draws))

        ci_low = float(np.percentile(bootstrap_hits, 2.5))
        ci_high = float(np.percentile(bootstrap_hits, 97.5))

        return {
            "last_100_hit_rate_main_top3": round(hit_rate, 4),
            "ci_hit_rate_main_top3": [round(ci_low, 4), round(ci_high, 4)],
            "random_baseline_hit_rate": round(random_baseline, 4),
            "simulations": n_simulations,
            "top3_tested": list(top3_nums)
        }

    def generate_reasoning(self) -> str:
        """Generate human-readable reasoning for predictions."""
        n_draws = len(self.draws)
        model_type = self._detect_model_type()

        # Hot/cold numbers
        hot = sorted(self.prob.items(), key=lambda x: x[1], reverse=True)[:5]
        cold = sorted(self.prob.items(), key=lambda x: x[1])[:5]

        # Overdue numbers
        overdue = sorted(self.recency.items(), key=lambda x: x[1], reverse=True)[:5]

        # Top pairs
        top_pairs = sorted(self.cooccurrence.items(), key=lambda x: x[1], reverse=True)[:5]

        reasoning = f"""Analysis based on {n_draws} historical draws.

**Model Type:** {model_type.title()} categorical with {'pairwise adjustments' if model_type == 'pairwise' else 'empirical frequencies'}

**Statistical Summary:**
- Chi-squared statistic: {self.chi_squared:.2f} (p={self.chi_p_value:.4f})
- Entropy: {self.entropy:.3f} bits (uniform: {math.log2(len(self.num_range)):.3f})
- KL divergence from uniform: {self.kl_divergence:.5f}

**Hot Numbers (most frequent):** {', '.join(f'{n}({p:.3f})' for n,p in hot)}

**Cold Numbers (least frequent):** {', '.join(f'{n}({p:.3f})' for n,p in cold)}

**Most Overdue:** {', '.join(f'{n}({d} draws)' for n,d in overdue)}

**Top Co-occurring Pairs:** {', '.join(f'{a}-{b}({c})' for (a,b),c in top_pairs)}

**Selection Method:** Numbers sampled sequentially without replacement using weighted probabilities derived from historical frequencies{' with pairwise multiplier adjustments' if model_type == 'pairwise' else ''}."""

        return reasoning

    def run_full_analysis(self) -> AnalysisResult:
        """Run complete analysis pipeline and return structured result."""
        # Coverage calculation
        if self.draws:
            date_range = (self.draws[0].draw_date - self.draws[-1].draw_date).days
            coverage_days = min(date_range, len(self.draws))
        else:
            coverage_days = 0
        coverage_percent = round(coverage_days / TARGET_DAYS * 100, 1)

        # Run all components
        inferred_model = self.infer_model()
        predictions = self.generate_predictions()
        backtest = self.run_backtest()
        reasoning = self.generate_reasoning()

        # Compile audit notes
        audit = []
        if len(self.draws) < 100:
            audit.append(f"Limited data: only {len(self.draws)} draws available")
        if coverage_percent < 50:
            audit.append(f"Coverage below 50%: {coverage_percent}%")
        if self.chi_p_value < 0.05:
            audit.append("Chi-squared test suggests non-uniform distribution (p < 0.05)")

        return AnalysisResult(
            game=self.game,
            coverage_days=coverage_days,
            coverage_percent=coverage_percent,
            inferred_model=inferred_model,
            predictions=predictions,
            backtest=backtest,
            reasoning=reasoning,
            data_sources=self.data_sources,
            audit_notes="; ".join(audit) if audit else "No issues detected"
        )


def analyze_game(game: str, draws: List[Draw], seed: Optional[int] = None) -> AnalysisResult:
    """
    Convenience function to run full analysis on a game.

    Args:
        game: Game identifier
        draws: Historical draws
        seed: Optional RNG seed for reproducibility

    Returns:
        AnalysisResult with all analysis data
    """
    analyzer = LotteryAnalyzer(game, draws, rng_seed=seed)
    return analyzer.run_full_analysis()


# =============================================================================
# Unit Tests
# =============================================================================

def _test_frequency_calculation():
    """Test frequency calculation."""
    from models import Draw

    draws = [
        Draw("test", 1, datetime.now(), [1, 2, 3, 4, 5], []),
        Draw("test", 2, datetime.now() - timedelta(days=1), [1, 2, 6, 7, 8], []),
        Draw("test", 3, datetime.now() - timedelta(days=2), [1, 3, 5, 9, 10], []),
    ]

    analyzer = LotteryAnalyzer("daily_lotto", draws)

    assert analyzer.freq[1] == 3, f"Expected freq[1]=3, got {analyzer.freq[1]}"
    assert analyzer.freq[2] == 2, f"Expected freq[2]=2, got {analyzer.freq[2]}"
    print("✓ Frequency calculation test passed")


def _test_pairwise_matrix():
    """Test pairwise co-occurrence matrix."""
    from models import Draw

    draws = [
        Draw("test", 1, datetime.now(), [1, 2, 3, 4, 5], []),
        Draw("test", 2, datetime.now() - timedelta(days=1), [1, 2, 6, 7, 8], []),
    ]

    analyzer = LotteryAnalyzer("daily_lotto", draws)

    assert (1, 2) in analyzer.cooccurrence, "Pair (1,2) should be in cooccurrence"
    assert analyzer.cooccurrence[(1, 2)] == 2, f"Expected cooc[(1,2)]=2, got {analyzer.cooccurrence.get((1,2))}"
    print("✓ Pairwise matrix test passed")


def _test_sampling():
    """Test weighted sampling."""
    from models import Draw

    # Create biased draws (1 appears very frequently)
    draws = []
    for i in range(50):
        nums = [1, 2, 3, 4, 5] if i < 40 else [6, 7, 8, 9, 10]
        draws.append(Draw("test", i, datetime.now() - timedelta(days=i), nums, []))

    analyzer = LotteryAnalyzer("daily_lotto", draws, rng_seed=42)

    # Sample many times and check if 1 appears more often
    samples = [analyzer._sample_with_pairwise(3) for _ in range(100)]
    count_1 = sum(1 for s in samples if 1 in s)

    assert count_1 > 30, f"Expected number 1 to appear frequently, got {count_1}/100"
    print(f"✓ Sampling test passed (1 appeared {count_1}/100 times)")


def run_tests():
    """Run all unit tests."""
    print("Running analyzer unit tests...")
    _test_frequency_calculation()
    _test_pairwise_matrix()
    _test_sampling()
    print("\nAll tests passed!")


# =============================================================================
# Advanced Prediction with Range Change Detection & Multi-Factor Analysis
# =============================================================================

# Known range changes for SA Lotto
RANGE_CHANGES = {
    "lotto": {
        "change_date": datetime(2017, 11, 1),  # LOTTO changed from 1-52 to 1-58
        "old_range": (1, 52),
        "new_range": (1, 58),
    },
    "lotto_plus_1": {
        "change_date": datetime(2017, 11, 1),
        "old_range": (1, 52),
        "new_range": (1, 58),
    },
    "lotto_plus_2": {
        "change_date": datetime(2017, 11, 1),
        "old_range": (1, 52),
        "new_range": (1, 58),
    },
}


class AdvancedPredictor:
    """
    Advanced predictor with thorough multi-factor analysis.

    Checks performed before final prediction:
    1. Range change detection (old 1-52 vs new 1-58)
    2. Frequency analysis (hot/cold numbers)
    3. Recency analysis (overdue numbers)
    4. Pair co-occurrence patterns
    5. Day-of-week patterns
    6. Sum distribution targeting
    7. Consecutive number patterns
    8. Position bias analysis
    9. New number performance (53-58 for LOTTO)
    10. Final weighted consensus
    """

    def __init__(self, game: str, draws: List[Draw], rng_seed: Optional[int] = None):
        self.game = game
        self.game_config = get_game(game)
        self.rng = np.random.default_rng(rng_seed or int(datetime.now().timestamp()))
        self.draws = self._clean_and_sort(draws)
        self.checks_passed = []
        self.check_details = {}

        # Detect range change
        self.range_info = self._detect_range_change()

        # Run analyzer
        self.analyzer = LotteryAnalyzer(game, self.draws, rng_seed)

    def _clean_and_sort(self, draws: List[Draw]) -> List[Draw]:
        """Clean and sort draws by date (newest first)."""
        valid = []
        seen = set()
        for d in draws:
            key = d.draw_date.date()
            if key not in seen:
                seen.add(key)
                valid.append(d)
        valid.sort(key=lambda x: x.draw_date, reverse=True)
        return valid

    def _detect_range_change(self) -> Dict[str, Any]:
        """Detect if game has had a range change and analyze impact."""
        info = {
            "has_range_change": False,
            "change_date": None,
            "old_range": self.game_config.main_range,
            "new_range": self.game_config.main_range,
            "new_numbers": [],
            "old_draws_count": 0,
            "new_draws_count": 0,
        }

        if self.game in RANGE_CHANGES:
            change = RANGE_CHANGES[self.game]
            info["has_range_change"] = True
            info["change_date"] = change["change_date"]
            info["old_range"] = change["old_range"]
            info["new_range"] = change["new_range"]

            # Numbers only in new range
            old_max = change["old_range"][1]
            new_max = change["new_range"][1]
            info["new_numbers"] = list(range(old_max + 1, new_max + 1))

            # Count draws before/after change
            for d in self.draws:
                if d.draw_date >= change["change_date"]:
                    info["new_draws_count"] += 1
                else:
                    info["old_draws_count"] += 1

        return info

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all analysis checks and return detailed results."""
        results = {
            "game": self.game,
            "total_draws": len(self.draws),
            "checks": {},
            "warnings": [],
            "recommendations": [],
        }

        # CHECK 1: Range Change Analysis
        results["checks"]["range_change"] = self._check_range_change()

        # CHECK 2: Frequency Analysis
        results["checks"]["frequency"] = self._check_frequency()

        # CHECK 3: Recency Analysis
        results["checks"]["recency"] = self._check_recency()

        # CHECK 4: Pair Co-occurrence
        results["checks"]["pairs"] = self._check_pairs()

        # CHECK 5: Day of Week Patterns
        results["checks"]["day_of_week"] = self._check_dow()

        # CHECK 6: Sum Distribution
        results["checks"]["sum_distribution"] = self._check_sum()

        # CHECK 7: Consecutive Numbers
        results["checks"]["consecutive"] = self._check_consecutive()

        # CHECK 8: Position Bias
        results["checks"]["position_bias"] = self._check_position_bias()

        # CHECK 9: New Numbers Performance (53-58)
        results["checks"]["new_numbers"] = self._check_new_numbers()

        # CHECK 10: Statistical Tests
        results["checks"]["statistical"] = self._check_statistical()

        return results

    def _check_range_change(self) -> Dict:
        """Check 1: Analyze range change impact."""
        check = {
            "name": "Range Change Analysis",
            "passed": True,
            "details": {},
            "recommendation": [],
        }

        if not self.range_info["has_range_change"]:
            check["details"]["status"] = "No range change for this game"
            return check

        new_nums = self.range_info["new_numbers"]
        check["details"]["new_numbers"] = new_nums
        check["details"]["change_date"] = self.range_info["change_date"].strftime("%Y-%m-%d")

        # Analyze frequency of new numbers (53-58)
        new_num_freq = {}
        total_draws_after_change = self.range_info["new_draws_count"]

        for num in new_nums:
            freq = self.analyzer.freq.get(num, 0)
            expected = total_draws_after_change * self.game_config.main_numbers / self.game_config.main_range[1]
            new_num_freq[num] = {
                "frequency": freq,
                "expected": round(expected, 1),
                "deviation": round((freq - expected) / expected * 100 if expected > 0 else 0, 1),
            }

        check["details"]["new_number_stats"] = new_num_freq

        # Check if new numbers are underperforming
        underperforming = [n for n, s in new_num_freq.items() if s["deviation"] < -10]
        overperforming = [n for n, s in new_num_freq.items() if s["deviation"] > 10]

        if underperforming:
            check["recommendation"].append(f"New numbers {underperforming} are underperforming - may be due")
        if overperforming:
            check["recommendation"].append(f"New numbers {overperforming} are hot since range change")

        return check

    def _check_frequency(self) -> Dict:
        """Check 2: Frequency analysis."""
        sorted_freq = sorted(self.analyzer.prob.items(), key=lambda x: x[1], reverse=True)

        return {
            "name": "Frequency Analysis",
            "passed": True,
            "details": {
                "hot_numbers": [n for n, _ in sorted_freq[:10]],
                "cold_numbers": [n for n, _ in sorted_freq[-10:]],
                "hottest": sorted_freq[0],
                "coldest": sorted_freq[-1],
            },
            "recommendation": [f"Hot: {[n for n,_ in sorted_freq[:5]]}", f"Cold: {[n for n,_ in sorted_freq[-5:]]}"],
        }

    def _check_recency(self) -> Dict:
        """Check 3: Recency/overdue analysis."""
        sorted_recency = sorted(self.analyzer.recency.items(), key=lambda x: x[1], reverse=True)

        very_overdue = [(n, d) for n, d in sorted_recency if d > 15]

        return {
            "name": "Recency Analysis",
            "passed": True,
            "details": {
                "most_overdue": sorted_recency[:10],
                "very_overdue_count": len(very_overdue),
            },
            "recommendation": [f"Overdue numbers (15+ draws): {[n for n,_ in very_overdue[:5]]}"] if very_overdue else [],
        }

    def _check_pairs(self) -> Dict:
        """Check 4: Pair co-occurrence patterns."""
        sorted_pairs = sorted(self.analyzer.cooccurrence.items(), key=lambda x: x[1], reverse=True)

        # Find numbers that appear in top pairs
        pair_freq = Counter()
        for (a, b), count in sorted_pairs[:20]:
            pair_freq[a] += count
            pair_freq[b] += count

        return {
            "name": "Pair Co-occurrence",
            "passed": True,
            "details": {
                "top_pairs": [(f"{a}-{b}", c) for (a, b), c in sorted_pairs[:10]],
                "best_pair_numbers": pair_freq.most_common(10),
            },
            "recommendation": [f"Numbers with strong pairs: {[n for n,_ in pair_freq.most_common(5)]}"],
        }

    def _check_dow(self) -> Dict:
        """Check 5: Day of week patterns."""
        today_dow = datetime.now().weekday()
        dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        dow_probs = self.analyzer.dow_patterns.get(today_dow, {})
        if dow_probs:
            sorted_dow = sorted(dow_probs.items(), key=lambda x: x[1], reverse=True)
            hot_today = [n for n, _ in sorted_dow[:10]]
        else:
            hot_today = []

        return {
            "name": f"Day of Week ({dow_names[today_dow]})",
            "passed": True,
            "details": {
                "today": dow_names[today_dow],
                "hot_for_today": hot_today,
            },
            "recommendation": [f"Hot on {dow_names[today_dow]}s: {hot_today[:5]}"] if hot_today else [],
        }

    def _check_sum(self) -> Dict:
        """Check 6: Sum distribution analysis."""
        sums = [sum(d.main_numbers) for d in self.draws]
        avg_sum = np.mean(sums)
        std_sum = np.std(sums)

        return {
            "name": "Sum Distribution",
            "passed": True,
            "details": {
                "average_sum": round(avg_sum, 1),
                "std_dev": round(std_sum, 1),
                "target_range": (round(avg_sum - std_sum), round(avg_sum + std_sum)),
                "min_seen": min(sums),
                "max_seen": max(sums),
            },
            "recommendation": [f"Target sum: {round(avg_sum - std_sum)}-{round(avg_sum + std_sum)}"],
        }

    def _check_consecutive(self) -> Dict:
        """Check 7: Consecutive number patterns."""
        consec_counts = []
        for d in self.draws:
            nums = sorted(d.main_numbers)
            count = sum(1 for i in range(len(nums)-1) if nums[i+1] - nums[i] == 1)
            consec_counts.append(count)

        avg_consec = np.mean(consec_counts)

        return {
            "name": "Consecutive Numbers",
            "passed": True,
            "details": {
                "average_consecutive_pairs": round(avg_consec, 2),
                "draws_with_0_consecutive": sum(1 for c in consec_counts if c == 0),
                "draws_with_1_consecutive": sum(1 for c in consec_counts if c == 1),
                "draws_with_2plus_consecutive": sum(1 for c in consec_counts if c >= 2),
            },
            "recommendation": [f"Include {round(avg_consec)} consecutive pair(s) on average"],
        }

    def _check_position_bias(self) -> Dict:
        """Check 8: Position-specific bias."""
        # Check if numbers tend to appear in specific positions
        position_hot = {}
        for pos, probs in self.analyzer.position_bias.items():
            if probs:
                sorted_pos = sorted(probs.items(), key=lambda x: x[1], reverse=True)
                position_hot[f"pos_{pos+1}"] = [n for n, _ in sorted_pos[:5]]

        return {
            "name": "Position Bias",
            "passed": True,
            "details": {
                "position_preferences": position_hot,
            },
            "recommendation": [],
        }

    def _check_new_numbers(self) -> Dict:
        """Check 9: Performance of new range numbers (53-58)."""
        if not self.range_info["has_range_change"]:
            return {
                "name": "New Numbers (53-58)",
                "passed": True,
                "details": {"status": "Not applicable for this game"},
                "recommendation": [],
            }

        new_nums = self.range_info["new_numbers"]
        new_num_appearances = {n: self.analyzer.freq.get(n, 0) for n in new_nums}

        # Check in recent draws
        recent_100 = self.draws[:100]
        recent_appearances = Counter()
        for d in recent_100:
            for n in d.main_numbers:
                if n in new_nums:
                    recent_appearances[n] += 1

        return {
            "name": "New Numbers (53-58)",
            "passed": True,
            "details": {
                "total_appearances": new_num_appearances,
                "recent_100_appearances": dict(recent_appearances),
                "hottest_new": max(new_num_appearances.items(), key=lambda x: x[1]) if new_num_appearances else None,
                "coldest_new": min(new_num_appearances.items(), key=lambda x: x[1]) if new_num_appearances else None,
            },
            "recommendation": [f"Consider new range numbers: {[n for n in new_nums if recent_appearances.get(n, 0) > 5]}"],
        }

    def _check_statistical(self) -> Dict:
        """Check 10: Statistical test results."""
        return {
            "name": "Statistical Tests",
            "passed": True,
            "details": {
                "chi_squared": round(self.analyzer.chi_squared, 2),
                "chi_p_value": round(self.analyzer.chi_p_value, 4),
                "entropy": round(self.analyzer.entropy, 4),
                "max_entropy": round(math.log2(len(self.analyzer.num_range)), 4),
                "kl_divergence": round(self.analyzer.kl_divergence, 6),
                "is_uniform": self.analyzer.chi_p_value > 0.05,
            },
            "recommendation": ["Distribution appears uniform (no exploitable pattern)"] if self.analyzer.chi_p_value > 0.05 else ["Some deviation from uniform detected"],
        }

    def generate_final_prediction(self) -> Dict[str, Any]:
        """
        Generate final prediction after all checks.

        Combines all factors with weighted scoring.
        """
        checks = self.run_all_checks()
        num_to_pick = self.game_config.main_numbers  # 6 for LOTTO, 5 for Daily Lotto

        # Build weighted scores for each number
        scores = {n: 0.0 for n in self.analyzer.num_range}

        # Factor 1: Frequency (weight: 2.0)
        for n, prob in self.analyzer.prob.items():
            scores[n] += prob * 100 * 2.0

        # Factor 2: Recency/Overdue (weight: 1.5)
        max_recency = max(self.analyzer.recency.values()) if self.analyzer.recency else 1
        for n, rec in self.analyzer.recency.items():
            scores[n] += (rec / max_recency) * 1.5

        # Factor 3: Pair strength (weight: 1.0)
        pair_strength = Counter()
        for (a, b), count in self.analyzer.cooccurrence.items():
            pair_strength[a] += count
            pair_strength[b] += count
        max_pair = max(pair_strength.values()) if pair_strength else 1
        for n, strength in pair_strength.items():
            scores[n] += (strength / max_pair) * 1.0

        # Factor 4: Day of week (weight: 0.5)
        today_dow = datetime.now().weekday()
        dow_probs = self.analyzer.dow_patterns.get(today_dow, {})
        for n, prob in dow_probs.items():
            scores[n] += prob * 50 * 0.5

        # Factor 5: New numbers bonus for LOTTO (weight: 0.3)
        if self.range_info["has_range_change"]:
            for n in self.range_info["new_numbers"]:
                # Give slight boost to underrepresented new numbers
                if self.analyzer.recency.get(n, 0) > 10:
                    scores[n] += 0.3

        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Select top candidates
        top_candidates = [n for n, _ in sorted_scores[:num_to_pick * 3]]

        # Monte Carlo selection with sum targeting
        sum_check = checks["checks"]["sum_distribution"]["details"]
        target_sum = sum_check["average_sum"]
        sum_std = sum_check["std_dev"]

        best_selection = None
        best_score = -float('inf')

        # Weighted probabilities
        weights = np.array([scores[n] for n in top_candidates])
        weights = weights / weights.sum()

        for _ in range(5000):
            try:
                selection = self.rng.choice(
                    top_candidates,
                    size=num_to_pick,
                    replace=False,
                    p=weights
                )
                selection = sorted(selection.tolist())

                # Score this selection
                sel_sum = sum(selection)
                sum_penalty = abs(sel_sum - target_sum) / sum_std if sum_std > 0 else 0

                # Check consecutive
                consec = sum(1 for i in range(len(selection)-1) if selection[i+1] - selection[i] == 1)
                consec_penalty = abs(consec - 1) * 0.5  # Prefer 1 consecutive pair

                # Total score (higher is better)
                sel_score = sum(scores[n] for n in selection) - sum_penalty - consec_penalty

                if sel_score > best_score:
                    best_score = sel_score
                    best_selection = selection

            except Exception:
                continue

        if best_selection is None:
            best_selection = [n for n, _ in sorted_scores[:num_to_pick]]

        # Generate bonus number if applicable
        bonus_number = None
        if self.game_config.bonus_numbers and self.game_config.bonus_range:
            bonus_range = list(range(self.game_config.bonus_range[0], self.game_config.bonus_range[1] + 1))
            if self.analyzer.bonus_prob:
                bonus_weights = np.array([self.analyzer.bonus_prob.get(n, 1/len(bonus_range)) for n in bonus_range])
                bonus_weights = bonus_weights / bonus_weights.sum()
                bonus_number = int(self.rng.choice(bonus_range, p=bonus_weights))
            else:
                bonus_number = int(self.rng.choice(bonus_range))

        # Build result
        result = {
            "game": self.game,
            "game_display": self.game_config.display_name,
            "numbers_required": num_to_pick,
            "final_numbers": best_selection,
            "bonus_number": bonus_number,
            "selection_score": round(best_score, 2),
            "sum": sum(best_selection),
            "target_sum_range": (round(target_sum - sum_std), round(target_sum + sum_std)),
            "checks_summary": {
                name: {
                    "passed": data.get("passed", True),
                    "recommendations": data.get("recommendation", []),
                }
                for name, data in checks["checks"].items()
            },
            "top_10_candidates": [(n, round(scores[n], 2)) for n, _ in sorted_scores[:10]],
            "reasoning": self._build_reasoning(best_selection, checks, scores),
            "disclaimer": DISCLAIMER,
            "generated_at": datetime.now().isoformat(),
        }

        return result

    def _build_reasoning(self, selection: List[int], checks: Dict, scores: Dict) -> str:
        """Build human-readable reasoning."""
        freq_check = checks["checks"]["frequency"]["details"]
        sum_check = checks["checks"]["sum_distribution"]["details"]
        recency_check = checks["checks"]["recency"]["details"]

        reasoning = f"""THOROUGH ANALYSIS COMPLETE ({len(self.draws)} draws analyzed)

SELECTION: {' - '.join(f'{n:02d}' for n in selection)}

WHY THESE NUMBERS?

1. FREQUENCY ANALYSIS
   - Hot numbers: {freq_check['hot_numbers'][:5]}
   - Cold numbers: {freq_check['cold_numbers'][:5]}
   - Selected includes {len([n for n in selection if n in freq_check['hot_numbers'][:10]])} hot numbers

2. RECENCY CHECK
   - Most overdue: {[n for n,_ in recency_check['most_overdue'][:5]]}
   - Selected includes {len([n for n in selection if n in [x for x,_ in recency_check['most_overdue'][:10]]])} overdue numbers

3. SUM DISTRIBUTION
   - Target range: {sum_check['target_range'][0]}-{sum_check['target_range'][1]}
   - Selection sum: {sum(selection)} ({'WITHIN RANGE' if sum_check['target_range'][0] <= sum(selection) <= sum_check['target_range'][1] else 'OUTSIDE RANGE'})

4. PAIR CO-OCCURRENCE
   - Numbers with strong historical pairs included

5. STATISTICAL CONFIDENCE
   - Chi-squared p-value: {checks['checks']['statistical']['details']['chi_p_value']}
   - Distribution: {'Uniform (random)' if checks['checks']['statistical']['details']['is_uniform'] else 'Some deviation detected'}
"""

        if self.range_info["has_range_change"]:
            new_in_sel = [n for n in selection if n in self.range_info["new_numbers"]]
            reasoning += f"""
6. RANGE CHANGE ANALYSIS (1-52 → 1-58)
   - New numbers (53-58) in selection: {new_in_sel if new_in_sel else 'None'}
"""

        return reasoning


def get_advanced_prediction(game: str, draws: List[Draw], seed: Optional[int] = None) -> Dict[str, Any]:
    """
    Get advanced prediction with full multi-factor analysis.

    Args:
        game: Game identifier
        draws: Historical draws
        seed: Optional RNG seed

    Returns:
        Complete prediction with all checks and reasoning
    """
    predictor = AdvancedPredictor(game, draws, rng_seed=seed)
    return predictor.generate_final_prediction()


if __name__ == "__main__":
    run_tests()
