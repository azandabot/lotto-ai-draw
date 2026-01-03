"""
Unit tests for predictor.py - Prediction engine.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from models import Draw, Prediction
from config import get_game


class TestClosePairAnalysis:
    """Tests for close pair pattern analysis functions."""

    def test_count_close_pairs_with_consecutive(self):
        """Test counting close pairs with consecutive numbers."""
        from predictor import count_close_pairs

        # 5, 6 are consecutive (gap of 1)
        numbers = [1, 5, 6, 20, 30]
        assert count_close_pairs(numbers, max_gap=3) == 1

    def test_count_close_pairs_multiple(self):
        """Test counting multiple close pairs."""
        from predictor import count_close_pairs

        # 5-6 (gap 1), 6-8 (gap 2), 8-10 (gap 2)
        numbers = [5, 6, 8, 10, 30]
        assert count_close_pairs(numbers, max_gap=3) == 3

    def test_count_close_pairs_none(self):
        """Test when no close pairs exist."""
        from predictor import count_close_pairs

        numbers = [1, 10, 20, 30, 36]
        assert count_close_pairs(numbers, max_gap=3) == 0

    def test_count_close_pairs_unsorted_input(self):
        """Test that count_close_pairs handles unsorted input."""
        from predictor import count_close_pairs

        # Unsorted input
        numbers = [30, 5, 6, 20, 1]
        assert count_close_pairs(numbers, max_gap=3) == 1

    def test_has_close_pair_true(self):
        """Test has_close_pair returns True when pair exists."""
        from predictor import has_close_pair

        numbers = [1, 5, 6, 20, 30]
        assert has_close_pair(numbers, max_gap=3) is True

    def test_has_close_pair_false(self):
        """Test has_close_pair returns False when no pair exists."""
        from predictor import has_close_pair

        numbers = [1, 10, 20, 30, 36]
        assert has_close_pair(numbers, max_gap=3) is False

    def test_get_close_pair_rate(self, sample_draws_list):
        """Test calculating close pair rate from draws."""
        from predictor import get_close_pair_rate

        rate = get_close_pair_rate(sample_draws_list, max_gap=3)

        assert 0 <= rate <= 1

    def test_get_close_pair_rate_empty(self):
        """Test close pair rate with empty draws."""
        from predictor import get_close_pair_rate

        rate = get_close_pair_rate([], max_gap=3)
        assert rate == 0.0

    def test_analyze_close_pair_pattern(self, sample_draws_list):
        """Test comprehensive close pair analysis."""
        from predictor import analyze_close_pair_pattern

        stats = analyze_close_pair_pattern(sample_draws_list, max_gap=3)

        assert 'rate' in stats
        assert 'avg_pairs_per_draw' in stats
        assert 'common_pair_gaps' in stats
        assert 'draws_analyzed' in stats
        assert stats['draws_analyzed'] == len(sample_draws_list)


class TestComputeEnhancedStats:
    """Tests for compute_enhanced_stats function."""

    def test_compute_stats_basic(self, sample_draws_list, daily_lotto_config):
        """Test basic statistics computation."""
        from predictor import compute_enhanced_stats

        stats = compute_enhanced_stats(sample_draws_list, daily_lotto_config)

        assert 'hot_numbers' in stats
        assert 'cold_numbers' in stats
        assert 'avg_sum' in stats
        assert 'sum_std' in stats
        assert 'consecutive_rate' in stats
        assert 'top_pairs' in stats
        assert 'frequency' in stats
        assert 'total_draws' in stats

    def test_compute_stats_hot_numbers(self, create_draws_with_pattern, daily_lotto_config):
        """Test that frequently appearing numbers are marked as hot."""
        from predictor import compute_enhanced_stats

        # Create draws where number 12 appears every time
        draws = create_draws_with_pattern([1, 12, 20, 25, 33], count=50)

        stats = compute_enhanced_stats(draws, daily_lotto_config)

        assert 12 in stats['hot_numbers']

    def test_compute_stats_empty_draws(self, daily_lotto_config):
        """Test stats computation with empty draws list."""
        from predictor import compute_enhanced_stats

        stats = compute_enhanced_stats([], daily_lotto_config)

        assert stats['hot_numbers'] == []
        assert stats['avg_sum'] == 0
        # total_draws may not be present when empty, or could be 0
        assert stats.get('total_draws', 0) == 0

    def test_compute_stats_close_pair_stats(self, sample_draws_list, daily_lotto_config):
        """Test that close pair statistics are included."""
        from predictor import compute_enhanced_stats

        stats = compute_enhanced_stats(sample_draws_list, daily_lotto_config)

        assert 'close_pair_rate' in stats
        assert 'avg_close_pairs_per_draw' in stats
        assert 'common_pair_gaps' in stats

    def test_compute_stats_recency(self, sample_draws_list, daily_lotto_config):
        """Test recency calculation."""
        from predictor import compute_enhanced_stats

        stats = compute_enhanced_stats(sample_draws_list, daily_lotto_config)

        assert 'recency' in stats
        assert isinstance(stats['recency'], dict)


class TestPredictNumbersLocal:
    """Tests for local statistical prediction."""

    def test_predict_local_returns_prediction(self, sample_draws_list):
        """Test that predict_numbers_local returns a Prediction."""
        from predictor import predict_numbers_local

        prediction = predict_numbers_local("daily_lotto", sample_draws_list)

        assert isinstance(prediction, Prediction)
        assert prediction.game == "daily_lotto"

    def test_predict_local_correct_number_count(self, sample_draws_list):
        """Test that prediction has correct number count."""
        from predictor import predict_numbers_local

        prediction = predict_numbers_local("daily_lotto", sample_draws_list)

        assert len(prediction.main_numbers) == 5  # Daily Lotto has 5 numbers

    def test_predict_local_numbers_in_range(self, sample_draws_list):
        """Test that predicted numbers are within valid range."""
        from predictor import predict_numbers_local

        prediction = predict_numbers_local("daily_lotto", sample_draws_list)

        for num in prediction.main_numbers:
            assert 1 <= num <= 36

    def test_predict_local_no_duplicates(self, sample_draws_list):
        """Test that predicted numbers have no duplicates."""
        from predictor import predict_numbers_local

        prediction = predict_numbers_local("daily_lotto", sample_draws_list)

        assert len(prediction.main_numbers) == len(set(prediction.main_numbers))

    def test_predict_local_numbers_sorted(self, sample_draws_list):
        """Test that predicted numbers are sorted."""
        from predictor import predict_numbers_local

        prediction = predict_numbers_local("daily_lotto", sample_draws_list)

        assert prediction.main_numbers == sorted(prediction.main_numbers)

    def test_predict_local_has_reasoning(self, sample_draws_list):
        """Test that prediction includes reasoning."""
        from predictor import predict_numbers_local

        prediction = predict_numbers_local("daily_lotto", sample_draws_list)

        assert prediction.reasoning != ""
        assert "Statistical Analysis" in prediction.reasoning

    def test_predict_local_has_confidence_note(self, sample_draws_list):
        """Test that prediction includes confidence note."""
        from predictor import predict_numbers_local

        prediction = predict_numbers_local("daily_lotto", sample_draws_list)

        assert prediction.confidence_note != ""

    def test_predict_local_insufficient_data(self):
        """Test prediction with very few draws."""
        from predictor import predict_numbers_local

        # Only 3 draws (less than 5 required for statistical prediction)
        draws = [
            Draw("daily_lotto", i, datetime.now() - timedelta(days=i), [1, 2, 3, 4, 5], [])
            for i in range(3)
        ]

        prediction = predict_numbers_local("daily_lotto", draws)

        assert isinstance(prediction, Prediction)
        assert "Insufficient" in prediction.reasoning or len(prediction.main_numbers) == 5

    def test_predict_local_powerball(self):
        """Test prediction for PowerBall game."""
        from predictor import predict_numbers_local

        draws = [
            Draw("powerball", i, datetime.now() - timedelta(days=i),
                 [1, 10, 20, 30, 40], [5])
            for i in range(50)
        ]

        prediction = predict_numbers_local("powerball", draws)

        assert len(prediction.main_numbers) == 5
        assert len(prediction.bonus_numbers) == 1
        for num in prediction.main_numbers:
            assert 1 <= num <= 50
        for num in prediction.bonus_numbers:
            assert 1 <= num <= 20


class TestHasApiKey:
    """Tests for API key detection."""

    def test_has_api_key_with_valid_key(self, monkeypatch):
        """Test has_api_key with valid API key."""
        from predictor import has_api_key

        monkeypatch.setenv("OPENAI_API_KEY", "sk-validkey12345678901234567890")
        assert has_api_key() is True

    def test_has_api_key_without_key(self, monkeypatch):
        """Test has_api_key when key is not set."""
        from predictor import has_api_key

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert has_api_key() is False

    def test_has_api_key_placeholder_key(self, monkeypatch):
        """Test has_api_key with placeholder key."""
        from predictor import has_api_key

        monkeypatch.setenv("OPENAI_API_KEY", "your-api-key-here")
        assert has_api_key() is False

    def test_has_api_key_short_key(self, monkeypatch):
        """Test has_api_key with too short key."""
        from predictor import has_api_key

        monkeypatch.setenv("OPENAI_API_KEY", "short")
        assert has_api_key() is False


class TestAnalyzePatterns:
    """Tests for analyze_patterns function."""

    def test_analyze_patterns_basic(self, sample_draws_list):
        """Test basic pattern analysis."""
        from predictor import analyze_patterns

        patterns = analyze_patterns(sample_draws_list)

        assert 'total_draws' in patterns
        assert 'most_frequent' in patterns
        assert 'least_frequent' in patterns
        assert 'average_sum' in patterns
        assert 'consecutive_pairs_per_draw' in patterns

    def test_analyze_patterns_empty(self):
        """Test pattern analysis with empty draws."""
        from predictor import analyze_patterns

        patterns = analyze_patterns([])

        assert 'error' in patterns

    def test_analyze_patterns_frequency_order(self, sample_draws_list):
        """Test that most_frequent is ordered correctly."""
        from predictor import analyze_patterns

        patterns = analyze_patterns(sample_draws_list)

        most_frequent = patterns['most_frequent']
        if len(most_frequent) >= 2:
            # First element should have higher or equal frequency than second
            assert most_frequent[0][1] >= most_frequent[1][1]


class TestBuildPredictionPrompt:
    """Tests for GPT prompt building."""

    def test_build_prompt_contains_game_info(self, sample_draws_list, daily_lotto_config):
        """Test that prompt contains game information."""
        from predictor import build_prediction_prompt, compute_enhanced_stats

        stats = compute_enhanced_stats(sample_draws_list, daily_lotto_config)
        prompt = build_prediction_prompt(daily_lotto_config, sample_draws_list, stats)

        assert "Daily Lotto" in prompt
        assert "1-36" in prompt
        assert "5" in prompt  # 5 main numbers

    def test_build_prompt_contains_statistics(self, sample_draws_list, daily_lotto_config):
        """Test that prompt contains statistical information."""
        from predictor import build_prediction_prompt, compute_enhanced_stats

        stats = compute_enhanced_stats(sample_draws_list, daily_lotto_config)
        prompt = build_prediction_prompt(daily_lotto_config, sample_draws_list, stats)

        assert "Hot numbers" in prompt
        assert "Cold numbers" in prompt
        assert "Average sum" in prompt

    def test_build_prompt_contains_close_pair_info(self, sample_draws_list, daily_lotto_config):
        """Test that prompt emphasizes close pair pattern."""
        from predictor import build_prediction_prompt, compute_enhanced_stats

        stats = compute_enhanced_stats(sample_draws_list, daily_lotto_config)
        prompt = build_prediction_prompt(daily_lotto_config, sample_draws_list, stats)

        assert "close pair" in prompt.lower()
        assert "CRITICAL" in prompt or "IMPORTANT" in prompt
