"""
FORENSIC LOTTERY ANALYSIS
==========================
Deep statistical analysis to detect potential manipulation or algorithmic patterns.

Tests performed:
1. Chi-squared uniformity test
2. Runs test for randomness
3. Gap analysis (intervals between appearances)
4. Serial correlation test
5. Benford's Law analysis (on sums)
6. Sequential dependency test
7. Digit frequency analysis
8. Hot/Cold streak anomaly detection
9. Time-based pattern detection
10. Cross-game correlation
11. Variance ratio test
12. New number (53-58) underrepresentation analysis

Author: Forensic Analysis Module
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any, Optional
from collections import Counter, defaultdict
import math
import sys

import numpy as np
from scipy import stats as scipy_stats

# Add project path
sys.path.insert(0, r"C:\Users\judah\Documents\azanda.tech\lotto-ai-draw")

from models import Draw
from storage import load_draws
from fetcher import fetch_extended_history_sync
from config import get_game, GAMES

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ForensicAnalyzer:
    """Deep forensic analysis of lottery draws."""

    def __init__(self, game: str, draws: List[Draw]):
        self.game = game
        self.game_config = get_game(game)
        self.draws = self._clean_draws(draws)
        self.findings = []
        self.suspicion_score = 0  # 0-100 scale

    def _clean_draws(self, draws: List[Draw]) -> List[Draw]:
        """Clean and validate draws."""
        cleaned = []
        seen = set()
        for d in draws:
            date_key = d.draw_date.date()
            if date_key not in seen:
                # Validate number count
                if len(d.main_numbers) == self.game_config.main_numbers:
                    seen.add(date_key)
                    cleaned.append(d)
        cleaned.sort(key=lambda x: x.draw_date, reverse=True)
        return cleaned

    def add_finding(self, test_name: str, severity: str, description: str, data: Dict = None):
        """Add a forensic finding."""
        self.findings.append({
            "test": test_name,
            "severity": severity,  # LOW, MEDIUM, HIGH, CRITICAL
            "description": description,
            "data": data or {}
        })

        # Update suspicion score
        severity_scores = {"LOW": 5, "MEDIUM": 15, "HIGH": 30, "CRITICAL": 50}
        self.suspicion_score = min(100, self.suspicion_score + severity_scores.get(severity, 0))

    def test_1_chi_squared_uniformity(self) -> Dict:
        """Test 1: Chi-squared test for uniform distribution."""
        print("\n" + "="*60)
        print("TEST 1: CHI-SQUARED UNIFORMITY TEST")
        print("="*60)

        if not self.draws:
            return {"status": "SKIP", "reason": "No data"}

        num_range = list(range(
            self.game_config.main_range[0],
            self.game_config.main_range[1] + 1
        ))

        # Count frequencies
        all_nums = [n for d in self.draws for n in d.main_numbers]
        freq = Counter(all_nums)

        observed = [freq.get(n, 0) for n in num_range]
        expected_per_num = len(all_nums) / len(num_range)
        expected = [expected_per_num] * len(num_range)

        chi2, p_value = scipy_stats.chisquare(observed, expected)

        print(f"Total numbers drawn: {len(all_nums)}")
        print(f"Expected per number: {expected_per_num:.2f}")
        print(f"Chi-squared statistic: {chi2:.4f}")
        print(f"P-value: {p_value:.10f}")

        # Find extreme deviations
        deviations = []
        for n in num_range:
            obs = freq.get(n, 0)
            dev_pct = (obs - expected_per_num) / expected_per_num * 100
            z_score = (obs - expected_per_num) / math.sqrt(expected_per_num)
            deviations.append((n, obs, expected_per_num, dev_pct, z_score))

        # Sort by absolute deviation
        deviations.sort(key=lambda x: abs(x[3]), reverse=True)

        print("\nMost deviant numbers:")
        print("-" * 50)
        for n, obs, exp, dev_pct, z_score in deviations[:10]:
            status = "UNDER" if dev_pct < 0 else "OVER "
            flag = "!!!" if abs(z_score) > 2.5 else ("!!" if abs(z_score) > 2 else ("!" if abs(z_score) > 1.5 else ""))
            print(f"  Number {n:2d}: {obs:3d} observed (expected {exp:.1f}) = {dev_pct:+6.1f}% (z={z_score:+.2f}) {status} {flag}")

        # Check result
        if p_value < 0.001:
            self.add_finding(
                "Chi-Squared Test",
                "CRITICAL",
                f"Distribution is HIGHLY NON-UNIFORM (p={p_value:.10f}). This is extremely unlikely by chance alone.",
                {"chi2": chi2, "p_value": p_value, "worst_deviations": deviations[:5]}
            )
            print(f"\n>>> CRITICAL: p-value = {p_value:.10f}")
            print(">>> Distribution is HIGHLY NON-UNIFORM - SUSPICIOUS!")
        elif p_value < 0.05:
            self.add_finding(
                "Chi-Squared Test",
                "HIGH",
                f"Distribution shows significant deviation from uniform (p={p_value:.4f})",
                {"chi2": chi2, "p_value": p_value}
            )
            print(f"\n>>> HIGH CONCERN: p-value = {p_value:.4f}")
        else:
            print(f"\n>>> OK: Distribution appears uniform (p={p_value:.4f})")

        return {
            "chi2": chi2,
            "p_value": p_value,
            "deviations": deviations[:10],
            "status": "FAIL" if p_value < 0.05 else "PASS"
        }

    def test_2_runs_test(self) -> Dict:
        """Test 2: Runs test for randomness (per number)."""
        print("\n" + "="*60)
        print("TEST 2: RUNS TEST FOR RANDOMNESS")
        print("="*60)

        if len(self.draws) < 50:
            return {"status": "SKIP", "reason": "Insufficient data"}

        num_range = list(range(
            self.game_config.main_range[0],
            self.game_config.main_range[1] + 1
        ))

        suspicious_numbers = []

        for num in num_range:
            # Create binary sequence (1 if number appeared, 0 if not)
            sequence = [1 if num in d.main_numbers else 0 for d in self.draws]

            # Count runs
            runs = 1
            for i in range(1, len(sequence)):
                if sequence[i] != sequence[i-1]:
                    runs += 1

            # Expected runs under randomness
            n1 = sum(sequence)  # Number of 1s
            n0 = len(sequence) - n1  # Number of 0s

            if n1 == 0 or n0 == 0:
                continue

            expected_runs = (2 * n1 * n0) / (n1 + n0) + 1
            variance_runs = (2 * n1 * n0 * (2 * n1 * n0 - n1 - n0)) / ((n1 + n0)**2 * (n1 + n0 - 1))

            if variance_runs > 0:
                z_score = (runs - expected_runs) / math.sqrt(variance_runs)

                # Two-tailed p-value
                p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z_score)))

                if p_value < 0.05:
                    suspicious_numbers.append((num, runs, expected_runs, z_score, p_value))

        if suspicious_numbers:
            suspicious_numbers.sort(key=lambda x: x[4])  # Sort by p-value
            print("Suspicious non-random patterns detected:")
            print("-" * 60)
            for num, runs, exp, z, p in suspicious_numbers[:10]:
                direction = "TOO FEW RUNS (clustering)" if runs < exp else "TOO MANY RUNS (alternating)"
                print(f"  Number {num:2d}: {runs} runs (expected {exp:.1f}), z={z:+.2f}, p={p:.4f} - {direction}")

            if any(p < 0.01 for _, _, _, _, p in suspicious_numbers):
                self.add_finding(
                    "Runs Test",
                    "HIGH",
                    f"{len([x for x in suspicious_numbers if x[4] < 0.01])} numbers show highly non-random patterns",
                    {"suspicious_numbers": suspicious_numbers[:5]}
                )
        else:
            print("No suspicious patterns detected in runs test.")

        return {
            "suspicious_count": len(suspicious_numbers),
            "suspicious_numbers": suspicious_numbers[:10],
            "status": "CONCERN" if suspicious_numbers else "PASS"
        }

    def test_3_gap_analysis(self) -> Dict:
        """Test 3: Gap analysis - intervals between appearances."""
        print("\n" + "="*60)
        print("TEST 3: GAP ANALYSIS (Intervals Between Appearances)")
        print("="*60)

        if len(self.draws) < 100:
            return {"status": "SKIP", "reason": "Insufficient data"}

        num_range = list(range(
            self.game_config.main_range[0],
            self.game_config.main_range[1] + 1
        ))

        suspicious_gaps = []

        for num in num_range:
            # Find all positions where this number appeared
            positions = [i for i, d in enumerate(self.draws) if num in d.main_numbers]

            if len(positions) < 10:
                continue

            # Calculate gaps between appearances
            gaps = [positions[i+1] - positions[i] for i in range(len(positions)-1)]

            mean_gap = np.mean(gaps)
            std_gap = np.std(gaps)
            cv = std_gap / mean_gap if mean_gap > 0 else 0  # Coefficient of variation

            # Expected gap (geometric distribution)
            p = self.game_config.main_numbers / len(num_range)
            expected_gap = 1 / p

            # Suspiciously regular gaps (CV too low)
            if cv < 0.5 and len(gaps) > 20:  # Very regular
                suspicious_gaps.append((num, mean_gap, std_gap, cv, expected_gap, "TOO REGULAR"))

            # Suspiciously irregular (CV too high)
            if cv > 1.5:
                suspicious_gaps.append((num, mean_gap, std_gap, cv, expected_gap, "TOO IRREGULAR"))

        if suspicious_gaps:
            print("Suspicious gap patterns detected:")
            print("-" * 60)
            for num, mean, std, cv, exp, reason in suspicious_gaps:
                print(f"  Number {num:2d}: mean gap={mean:.1f} (expected {exp:.1f}), std={std:.1f}, CV={cv:.2f} - {reason}")

            too_regular = [x for x in suspicious_gaps if x[5] == "TOO REGULAR"]
            if too_regular:
                self.add_finding(
                    "Gap Analysis",
                    "MEDIUM",
                    f"{len(too_regular)} numbers show suspiciously regular intervals (possible pattern)",
                    {"too_regular": too_regular}
                )
        else:
            print("Gap patterns appear normal.")

        return {
            "suspicious_count": len(suspicious_gaps),
            "suspicious_gaps": suspicious_gaps,
            "status": "CONCERN" if suspicious_gaps else "PASS"
        }

    def test_4_serial_correlation(self) -> Dict:
        """Test 4: Serial correlation between consecutive draws."""
        print("\n" + "="*60)
        print("TEST 4: SERIAL CORRELATION TEST")
        print("="*60)

        if len(self.draws) < 100:
            return {"status": "SKIP", "reason": "Insufficient data"}

        # Calculate sum of each draw
        sums = [sum(d.main_numbers) for d in self.draws]

        # Lag-1 autocorrelation
        correlations = []
        for lag in range(1, 11):
            if len(sums) > lag:
                corr = np.corrcoef(sums[:-lag], sums[lag:])[0, 1]
                correlations.append((lag, corr))

        print("Serial Correlation (Lag-1 to Lag-10):")
        print("-" * 40)

        suspicious_correlations = []
        for lag, corr in correlations:
            # Under randomness, correlation should be ~0
            # Standard error: 1/sqrt(n)
            se = 1 / math.sqrt(len(sums))
            z_score = corr / se
            p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z_score)))

            flag = "SUSPICIOUS" if p_value < 0.05 else ""
            print(f"  Lag {lag:2d}: r = {corr:+.4f} (z={z_score:+.2f}, p={p_value:.4f}) {flag}")

            if p_value < 0.05:
                suspicious_correlations.append((lag, corr, z_score, p_value))

        if suspicious_correlations:
            self.add_finding(
                "Serial Correlation",
                "MEDIUM",
                f"Significant correlation detected at {len(suspicious_correlations)} lag(s)",
                {"correlations": suspicious_correlations}
            )
            print(f"\n>>> CONCERN: {len(suspicious_correlations)} significant correlations detected")
        else:
            print("\n>>> OK: No significant serial correlation detected")

        return {
            "correlations": correlations,
            "suspicious": suspicious_correlations,
            "status": "CONCERN" if suspicious_correlations else "PASS"
        }

    def test_5_digit_frequency(self) -> Dict:
        """Test 5: Last digit frequency analysis."""
        print("\n" + "="*60)
        print("TEST 5: LAST DIGIT FREQUENCY ANALYSIS")
        print("="*60)

        all_nums = [n for d in self.draws for n in d.main_numbers]
        last_digits = [n % 10 for n in all_nums]

        digit_freq = Counter(last_digits)

        # Expected uniform across 0-9
        expected = len(last_digits) / 10

        print(f"Total numbers: {len(last_digits)}")
        print(f"Expected per digit: {expected:.1f}")
        print("\nLast Digit Distribution:")
        print("-" * 40)

        observed = []
        for d in range(10):
            obs = digit_freq.get(d, 0)
            dev = (obs - expected) / expected * 100
            observed.append(obs)
            flag = "!" if abs(dev) > 15 else ""
            print(f"  Digit {d}: {obs:4d} ({dev:+5.1f}%) {flag}")

        # Chi-squared test on digits
        chi2, p_value = scipy_stats.chisquare(observed, [expected] * 10)
        print(f"\nChi-squared: {chi2:.4f}, p-value: {p_value:.6f}")

        if p_value < 0.05:
            self.add_finding(
                "Digit Frequency",
                "LOW",
                f"Last digit distribution shows some deviation (p={p_value:.4f})",
                {"chi2": chi2, "p_value": p_value, "distribution": dict(digit_freq)}
            )

        return {
            "distribution": dict(digit_freq),
            "chi2": chi2,
            "p_value": p_value,
            "status": "CONCERN" if p_value < 0.05 else "PASS"
        }

    def test_6_sum_distribution(self) -> Dict:
        """Test 6: Sum distribution normality test."""
        print("\n" + "="*60)
        print("TEST 6: SUM DISTRIBUTION ANALYSIS")
        print("="*60)

        sums = [sum(d.main_numbers) for d in self.draws]

        mean_sum = np.mean(sums)
        std_sum = np.std(sums)
        skew = scipy_stats.skew(sums)
        kurtosis = scipy_stats.kurtosis(sums)

        # Theoretical expected sum
        n_nums = self.game_config.main_numbers
        num_max = self.game_config.main_range[1]
        num_min = self.game_config.main_range[0]
        expected_mean = n_nums * (num_min + num_max) / 2

        print(f"Observed Mean Sum: {mean_sum:.2f}")
        print(f"Expected Mean Sum: {expected_mean:.2f}")
        print(f"Standard Deviation: {std_sum:.2f}")
        print(f"Skewness: {skew:.4f} (0 = symmetric)")
        print(f"Kurtosis: {kurtosis:.4f} (0 = normal)")

        # Shapiro-Wilk normality test (on sample)
        sample = sums[:min(5000, len(sums))]
        if len(sample) >= 20:
            stat, p_value = scipy_stats.shapiro(sample)
            print(f"\nShapiro-Wilk normality test: W={stat:.4f}, p={p_value:.6f}")

            if p_value < 0.05:
                print(">>> Sum distribution deviates from normal")
            else:
                print(">>> Sum distribution appears normal")

        return {
            "mean": mean_sum,
            "expected_mean": expected_mean,
            "std": std_sum,
            "skew": skew,
            "kurtosis": kurtosis,
            "status": "PASS"
        }

    def test_7_consecutive_numbers(self) -> Dict:
        """Test 7: Consecutive number pair analysis."""
        print("\n" + "="*60)
        print("TEST 7: CONSECUTIVE NUMBER PAIR ANALYSIS")
        print("="*60)

        consec_counts = []
        for d in self.draws:
            nums = sorted(d.main_numbers)
            consec = sum(1 for i in range(len(nums)-1) if nums[i+1] - nums[i] == 1)
            consec_counts.append(consec)

        freq = Counter(consec_counts)
        print("Consecutive pairs per draw:")
        print("-" * 30)
        for count in sorted(freq.keys()):
            pct = freq[count] / len(self.draws) * 100
            print(f"  {count} consecutive pairs: {freq[count]:4d} draws ({pct:.1f}%)")

        # Expected under random selection (hypergeometric)
        mean_consec = np.mean(consec_counts)
        print(f"\nAverage consecutive pairs: {mean_consec:.3f}")

        return {
            "distribution": dict(freq),
            "mean": mean_consec,
            "status": "PASS"
        }

    def test_8_new_numbers_analysis(self) -> Dict:
        """Test 8: Analysis of new range numbers (53-58 for LOTTO)."""
        print("\n" + "="*60)
        print("TEST 8: NEW RANGE NUMBERS ANALYSIS (53-58)")
        print("="*60)

        if self.game not in ["lotto", "lotto_plus_1", "lotto_plus_2"]:
            print("Not applicable for this game.")
            return {"status": "SKIP", "reason": "Not a LOTTO game"}

        # Range changed November 2017: 1-52 -> 1-58
        change_date = datetime(2017, 11, 1)
        new_numbers = [53, 54, 55, 56, 57, 58]

        # Filter draws after range change
        post_change_draws = [d for d in self.draws if d.draw_date >= change_date]

        if not post_change_draws:
            print("No draws found after range change.")
            return {"status": "SKIP", "reason": "No post-change data"}

        print(f"Draws since range change (Nov 2017): {len(post_change_draws)}")

        # Count appearances of each new number
        all_nums = [n for d in post_change_draws for n in d.main_numbers]
        freq = Counter(all_nums)

        # Expected frequency
        n_nums = self.game_config.main_numbers
        n_range = self.game_config.main_range[1] - self.game_config.main_range[0] + 1
        expected = len(all_nums) / n_range

        print(f"\nExpected appearances per number: {expected:.1f}")
        print("\nNew Numbers (53-58) Performance:")
        print("-" * 50)

        severe_under = []
        for num in new_numbers:
            obs = freq.get(num, 0)
            dev = (obs - expected) / expected * 100
            z_score = (obs - expected) / math.sqrt(expected)

            flag = ""
            if dev < -30:
                flag = "!!! SEVERELY UNDERREPRESENTED"
                severe_under.append((num, obs, expected, dev, z_score))
            elif dev < -15:
                flag = "!! UNDERREPRESENTED"

            print(f"  Number {num}: {obs:3d} (expected {expected:.1f}) = {dev:+6.1f}% (z={z_score:+.2f}) {flag}")

        if severe_under:
            self.add_finding(
                "New Numbers Analysis",
                "CRITICAL",
                f"Numbers {[x[0] for x in severe_under]} are severely underrepresented since range change. This is statistically improbable.",
                {"severe_under": severe_under}
            )
            print(f"\n>>> CRITICAL: {len(severe_under)} new numbers severely underrepresented!")
        else:
            print("\n>>> New numbers appear within expected range")

        return {
            "post_change_draws": len(post_change_draws),
            "new_number_freq": {n: freq.get(n, 0) for n in new_numbers},
            "expected": expected,
            "severe_under": severe_under,
            "status": "CRITICAL" if severe_under else "PASS"
        }

    def test_9_time_patterns(self) -> Dict:
        """Test 9: Time-based pattern detection."""
        print("\n" + "="*60)
        print("TEST 9: TIME-BASED PATTERN DETECTION")
        print("="*60)

        # Day of week analysis
        dow_counts = defaultdict(Counter)
        dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for d in self.draws:
            dow = d.draw_date.weekday()
            for n in d.main_numbers:
                dow_counts[dow][n] += 1

        print("Day-of-week number distribution:")
        print("-" * 50)

        # Check for anomalies
        dow_anomalies = []
        for dow in range(7):
            if dow not in dow_counts:
                continue

            counts = dow_counts[dow]
            total = sum(counts.values())
            expected = total / len(self.game_config.main_range)

            for num, obs in counts.items():
                dev = (obs - expected) / expected * 100 if expected > 0 else 0
                if abs(dev) > 50:  # More than 50% deviation
                    dow_anomalies.append((dow_names[dow], num, obs, expected, dev))

        if dow_anomalies:
            print(f"Found {len(dow_anomalies)} day-of-week anomalies:")
            for day, num, obs, exp, dev in dow_anomalies[:10]:
                print(f"  {day}: Number {num} - {obs} obs (expected {exp:.1f}) = {dev:+.1f}%")

        # Monthly pattern check
        month_counts = defaultdict(Counter)
        for d in self.draws:
            month = d.draw_date.month
            for n in d.main_numbers:
                month_counts[month][n] += 1

        return {
            "dow_anomalies": len(dow_anomalies),
            "status": "CONCERN" if dow_anomalies else "PASS"
        }

    def test_10_pair_anomalies(self) -> Dict:
        """Test 10: Pair co-occurrence anomalies."""
        print("\n" + "="*60)
        print("TEST 10: PAIR CO-OCCURRENCE ANOMALIES")
        print("="*60)

        # Count pair occurrences
        pair_counts = Counter()
        for d in self.draws:
            nums = sorted(d.main_numbers)
            for i in range(len(nums)):
                for j in range(i+1, len(nums)):
                    pair_counts[(nums[i], nums[j])] += 1

        if not pair_counts:
            return {"status": "SKIP", "reason": "No pairs"}

        # Expected pair frequency
        n_draws = len(self.draws)
        n_range = self.game_config.main_range[1] - self.game_config.main_range[0] + 1
        k = self.game_config.main_numbers

        # Expected occurrences per pair under random selection
        # P(pair) = C(n-2, k-2) / C(n, k) = k(k-1) / n(n-1)
        p_pair = (k * (k-1)) / (n_range * (n_range - 1))
        expected_pair = n_draws * p_pair

        print(f"Total draws: {n_draws}")
        print(f"Expected pair occurrences: {expected_pair:.2f}")

        # Find extreme pairs
        anomalies = []
        for pair, count in pair_counts.items():
            dev = (count - expected_pair) / expected_pair * 100 if expected_pair > 0 else 0
            z_score = (count - expected_pair) / math.sqrt(n_draws * p_pair * (1-p_pair)) if p_pair < 1 else 0

            if abs(z_score) > 3:  # More than 3 standard deviations
                anomalies.append((pair, count, expected_pair, dev, z_score))

        if anomalies:
            anomalies.sort(key=lambda x: abs(x[4]), reverse=True)
            print(f"\nFound {len(anomalies)} pair anomalies (|z| > 3):")
            print("-" * 60)
            for pair, count, exp, dev, z in anomalies[:15]:
                direction = "OVER" if z > 0 else "UNDER"
                print(f"  Pair {pair[0]:2d}-{pair[1]:2d}: {count:3d} (expected {exp:.1f}) = {dev:+6.1f}% (z={z:+.2f}) {direction}")

            if len(anomalies) > 20:
                self.add_finding(
                    "Pair Anomalies",
                    "MEDIUM",
                    f"{len(anomalies)} pairs show extreme deviation from expected (|z| > 3)",
                    {"anomalies": [(p, c, z) for p, c, _, _, z in anomalies[:10]]}
                )
        else:
            print("No extreme pair anomalies detected.")

        return {
            "anomaly_count": len(anomalies),
            "top_anomalies": anomalies[:10] if anomalies else [],
            "status": "CONCERN" if len(anomalies) > 20 else "PASS"
        }

    def test_11_variance_ratio(self) -> Dict:
        """Test 11: Variance ratio test (Lo-MacKinlay)."""
        print("\n" + "="*60)
        print("TEST 11: VARIANCE RATIO TEST")
        print("="*60)

        if len(self.draws) < 200:
            print("Insufficient data for variance ratio test")
            return {"status": "SKIP", "reason": "Insufficient data"}

        # Use sum of numbers as the series
        sums = np.array([sum(d.main_numbers) for d in self.draws])

        # Calculate returns/changes
        changes = np.diff(sums)

        if len(changes) < 100:
            return {"status": "SKIP", "reason": "Insufficient changes"}

        # Variance ratio test
        var_1 = np.var(changes)

        results = {}
        for k in [2, 4, 8, 16]:
            if len(changes) < k * 2:
                continue

            # Variance of k-period changes
            k_changes = sums[k:] - sums[:-k]
            var_k = np.var(k_changes) / k

            vr = var_k / var_1 if var_1 > 0 else 1

            # Under random walk, VR should be 1
            # z-statistic (asymptotic)
            n = len(changes)
            z = (vr - 1) / math.sqrt(2 * (2*k - 1) * (k - 1) / (3 * k * n)) if n > 0 and k > 1 else 0

            p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z)))

            flag = "SUSPICIOUS" if p_value < 0.05 else ""
            print(f"  VR({k}): {vr:.4f} (z={z:+.2f}, p={p_value:.4f}) {flag}")

            results[k] = {"vr": vr, "z": z, "p_value": p_value}

            if p_value < 0.05:
                self.add_finding(
                    "Variance Ratio",
                    "LOW",
                    f"VR({k}) deviates from random walk expectation",
                    {"k": k, "vr": vr, "p_value": p_value}
                )

        return results

    def test_12_benford_analysis(self) -> Dict:
        """Test 12: Benford's Law on draw sums."""
        print("\n" + "="*60)
        print("TEST 12: BENFORD'S LAW ANALYSIS (on sums)")
        print("="*60)

        sums = [sum(d.main_numbers) for d in self.draws]

        # First digit of sums
        first_digits = [int(str(s)[0]) for s in sums if s > 0]
        digit_freq = Counter(first_digits)

        # Benford expected frequencies
        benford_expected = {d: math.log10(1 + 1/d) for d in range(1, 10)}

        print("First Digit Distribution (Sums):")
        print("-" * 50)

        observed = []
        expected = []
        for d in range(1, 10):
            obs = digit_freq.get(d, 0) / len(first_digits) if first_digits else 0
            exp = benford_expected[d]
            observed.append(digit_freq.get(d, 0))
            expected.append(exp * len(first_digits))
            flag = "!" if abs(obs - exp) > 0.05 else ""
            print(f"  Digit {d}: {obs:.3f} (Benford: {exp:.3f}) {flag}")

        # Chi-squared test
        if all(e > 0 for e in expected):
            chi2, p_value = scipy_stats.chisquare(observed, expected)
            print(f"\nChi-squared: {chi2:.4f}, p-value: {p_value:.6f}")
        else:
            chi2, p_value = 0, 1

        return {
            "chi2": chi2,
            "p_value": p_value,
            "status": "CONCERN" if p_value < 0.05 else "PASS"
        }

    def run_all_tests(self) -> Dict:
        """Run all forensic tests and compile report."""
        print("\n" + "#"*60)
        print(f"# FORENSIC ANALYSIS: {self.game.upper()}")
        print(f"# Total draws analyzed: {len(self.draws)}")
        print(f"# Date range: {self.draws[-1].draw_date.date()} to {self.draws[0].draw_date.date()}")
        print("#"*60)

        results = {}

        results["chi_squared"] = self.test_1_chi_squared_uniformity()
        results["runs_test"] = self.test_2_runs_test()
        results["gap_analysis"] = self.test_3_gap_analysis()
        results["serial_correlation"] = self.test_4_serial_correlation()
        results["digit_frequency"] = self.test_5_digit_frequency()
        results["sum_distribution"] = self.test_6_sum_distribution()
        results["consecutive"] = self.test_7_consecutive_numbers()
        results["new_numbers"] = self.test_8_new_numbers_analysis()
        results["time_patterns"] = self.test_9_time_patterns()
        results["pair_anomalies"] = self.test_10_pair_anomalies()
        results["variance_ratio"] = self.test_11_variance_ratio()
        results["benford"] = self.test_12_benford_analysis()

        return results

    def generate_report(self) -> str:
        """Generate final forensic report."""
        report = []
        report.append("\n" + "="*70)
        report.append("                    FORENSIC ANALYSIS REPORT")
        report.append("="*70)
        report.append(f"\nGame: {self.game.upper()}")
        report.append(f"Draws Analyzed: {len(self.draws)}")
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"\nSUSPICION SCORE: {self.suspicion_score}/100")

        if self.suspicion_score >= 70:
            report.append("VERDICT: HIGH PROBABILITY OF MANIPULATION")
        elif self.suspicion_score >= 40:
            report.append("VERDICT: MODERATE CONCERNS - WARRANTS INVESTIGATION")
        elif self.suspicion_score >= 20:
            report.append("VERDICT: MINOR ANOMALIES - LIKELY NATURAL VARIATION")
        else:
            report.append("VERDICT: NO SIGNIFICANT EVIDENCE OF MANIPULATION")

        report.append("\n" + "-"*70)
        report.append("FINDINGS:")
        report.append("-"*70)

        if not self.findings:
            report.append("  No significant anomalies detected.")
        else:
            # Sort by severity
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            sorted_findings = sorted(self.findings, key=lambda x: severity_order.get(x["severity"], 4))

            for f in sorted_findings:
                report.append(f"\n[{f['severity']}] {f['test']}")
                report.append(f"  {f['description']}")

        report.append("\n" + "-"*70)
        report.append("DISCLAIMER:")
        report.append("-"*70)
        report.append("  This analysis is purely statistical and for educational purposes.")
        report.append("  Anomalies may have legitimate explanations such as range changes,")
        report.append("  ball machine maintenance, or natural variance. This is not proof")
        report.append("  of any wrongdoing.")

        return "\n".join(report)


def run_forensic_analysis(games: List[str] = None):
    """Run forensic analysis on specified games."""
    if games is None:
        games = ["daily_lotto", "lotto", "powerball"]

    for game in games:
        print(f"\n{'#'*70}")
        print(f"FETCHING DATA FOR: {game.upper()}")
        print(f"{'#'*70}")

        try:
            # Try to fetch extended history
            result = fetch_extended_history_sync(game, target_days=1095)  # 3 years
            draws = result[0] if isinstance(result, tuple) else result
            if not draws or len(draws) < 50:
                # Fall back to stored data
                draws = load_draws(game)

            if not draws:
                print(f"No data available for {game}")
                continue

            print(f"Loaded {len(draws)} draws for analysis")

            # Run forensic analysis
            analyzer = ForensicAnalyzer(game, draws)
            analyzer.run_all_tests()

            # Print report
            report = analyzer.generate_report()
            print(report)

        except Exception as e:
            print(f"Error analyzing {game}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys

    games_to_analyze = sys.argv[1:] if len(sys.argv) > 1 else None
    run_forensic_analysis(games_to_analyze)
