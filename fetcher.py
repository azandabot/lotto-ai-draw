"""
Fetch historical lottery results from the web.

Enhanced version with:
- Retry logic with exponential backoff
- Response caching (6-hour TTL)
- Improved error handling
- Rate limiting awareness
"""

import httpx
import asyncio
import hashlib
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
import re

from models import Draw
from config import GAMES


logger = logging.getLogger(__name__)

# Configuration
LOTTERY_CO_ZA_BASE = "https://www.lottery.co.za"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_TTL_HOURS = 1  # Reduced TTL for fresher data
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3


# =============================================================================
# Custom Exceptions
# =============================================================================

class FetchError(Exception):
    """Custom exception for fetch failures."""
    pass


# =============================================================================
# Caching Layer
# =============================================================================

def _get_cache_path(url: str) -> Path:
    """Generate cache file path from URL hash."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return CACHE_DIR / f"{url_hash}.json"


def _get_cached(url: str) -> Optional[str]:
    """Retrieve cached response if valid."""
    cache_path = _get_cache_path(url)

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        cached_at = datetime.fromisoformat(cache_data['cached_at'])
        if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
            logger.debug(f"Cache expired for {url}")
            return None

        logger.debug(f"Cache hit for {url}")
        return cache_data['content']

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Cache read error: {e}")
        return None


def _set_cached(url: str, content: str) -> None:
    """Cache response content."""
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        cache_path = _get_cache_path(url)

        cache_data = {
            'url': url,
            'cached_at': datetime.now().isoformat(),
            'content': content
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)

        logger.debug(f"Cached response for {url}")

    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def clear_cache() -> int:
    """Clear all cached responses. Returns number of files deleted."""
    if not CACHE_DIR.exists():
        return 0

    count = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            cache_file.unlink()
            count += 1
        except Exception:
            pass

    logger.info(f"Cleared {count} cache files")
    return count


# =============================================================================
# HTTP Fetching with Retry
# =============================================================================

async def fetch_with_retry(
    url: str,
    max_retries: int = MAX_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True
) -> str:
    """
    Fetch URL with retry logic and optional caching.

    Args:
        url: URL to fetch
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds
        use_cache: Whether to use caching

    Returns:
        HTML content as string

    Raises:
        FetchError: If all retries fail
    """
    # Check cache first
    if use_cache:
        cached = _get_cached(url)
        if cached:
            return cached

    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching {url} (attempt {attempt + 1}/{max_retries})")

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                    }
                )
                response.raise_for_status()

                content = response.text

                # Cache successful response
                if use_cache:
                    _set_cached(url, content)

                return content

        except httpx.TimeoutException:
            last_error = FetchError(f"Timeout after {timeout}s: {url}")
            logger.warning(f"Timeout on attempt {attempt + 1}")

        except httpx.HTTPStatusError as e:
            last_error = FetchError(f"HTTP {e.response.status_code}: {url}")
            logger.warning(f"HTTP error {e.response.status_code} on attempt {attempt + 1}")

            # Don't retry on client errors (4xx)
            if 400 <= e.response.status_code < 500:
                break

        except httpx.RequestError as e:
            last_error = FetchError(f"Request failed: {e}")
            logger.warning(f"Request error on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            sleep_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
            logger.info(f"Retrying in {sleep_time} seconds...")
            await asyncio.sleep(sleep_time)

    raise last_error or FetchError(f"Failed to fetch {url}")


# =============================================================================
# Game Configuration for lottery.co.za
# =============================================================================

GAME_CONFIG = {
    "lotto": {
        "url": "/lotto/results",
        "main_ball_class": "lotto-ball",
        "bonus_ball_class": "lotto-bonus-ball",
    },
    "lotto_plus_1": {
        "url": "/lotto-plus-1/results",
        "main_ball_class": "lotto-ball",  # Same class as regular lotto
        "bonus_ball_class": "lotto-bonus-ball",
    },
    "lotto_plus_2": {
        "url": "/lotto-plus-2/results",
        "main_ball_class": "lotto-ball",  # Same class as regular lotto
        "bonus_ball_class": "lotto-bonus-ball",
    },
    "powerball": {
        "url": "/powerball/results",
        "main_ball_class": "powerball-ball",
        "bonus_ball_class": "powerball-powerball",
    },
    "powerball_plus": {
        "url": "/powerball-plus/results",
        "main_ball_class": "powerball-ball",  # Same class as regular powerball
        "bonus_ball_class": "powerball-powerball",
    },
    "daily_lotto": {
        "url": "/daily-lotto/results",
        "main_ball_class": "daily-lotto-ball",
        "bonus_ball_class": None,
    },
}

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12
}


# =============================================================================
# Game-Specific Fetchers
# =============================================================================

async def fetch_lotto_results(limit: int = 20) -> List[Draw]:
    """Fetch LOTTO results from lottery.co.za"""
    return await _fetch_from_lottery_co_za("lotto", limit)


async def fetch_lotto_plus_1_results(limit: int = 20) -> List[Draw]:
    """Fetch LOTTO PLUS 1 results."""
    return await _fetch_from_lottery_co_za("lotto_plus_1", limit)


async def fetch_lotto_plus_2_results(limit: int = 20) -> List[Draw]:
    """Fetch LOTTO PLUS 2 results."""
    return await _fetch_from_lottery_co_za("lotto_plus_2", limit)


async def fetch_powerball_results(limit: int = 20) -> List[Draw]:
    """Fetch PowerBall results."""
    return await _fetch_from_lottery_co_za("powerball", limit)


async def fetch_powerball_plus_results(limit: int = 20) -> List[Draw]:
    """Fetch PowerBall PLUS results."""
    return await _fetch_from_lottery_co_za("powerball_plus", limit)


async def fetch_daily_lotto_results(limit: int = 20) -> List[Draw]:
    """Fetch Daily Lotto results."""
    return await _fetch_from_lottery_co_za("daily_lotto", limit)


async def _fetch_from_lottery_co_za(game: str, limit: int) -> List[Draw]:
    """
    Fetch results from lottery.co.za with proper parsing.
    """
    draws = []
    config = GAME_CONFIG.get(game)
    if not config:
        logger.error(f"Unknown game: {game}")
        return draws

    url = f"{LOTTERY_CO_ZA_BASE}{config['url']}"

    try:
        html_content = await fetch_with_retry(url)
    except FetchError as e:
        logger.error(f"Failed to fetch {game}: {e}")
        return draws

    soup = BeautifulSoup(html_content, "html.parser")

    # Find all resultBox containers
    result_boxes = soup.find_all("div", class_="resultBox")
    logger.debug(f"Found {len(result_boxes)} resultBox containers for {game}")

    game_settings = GAMES.get(game)
    main_count = game_settings.main_numbers if game_settings else 6
    bonus_count = game_settings.bonus_numbers if game_settings else 0

    for box in result_boxes[:limit]:
        draw = _parse_lottery_co_za_box(box, game, config, main_count, bonus_count)
        if draw:
            draws.append(draw)

    logger.info(f"Parsed {len(draws)} draws for {game}")
    return draws


def _parse_lottery_co_za_box(
    box,
    game: str,
    config: dict,
    main_count: int,
    bonus_count: int
) -> Optional[Draw]:
    """
    Parse a resultBox from lottery.co.za
    """
    try:
        text = box.get_text(' ', strip=True)

        # Extract date (format: "11 December 2025")
        date_match = re.search(
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(202\d)',
            text,
            re.I
        )
        if date_match:
            day = int(date_match.group(1))
            month = MONTH_MAP[date_match.group(2).lower()]
            year = int(date_match.group(3))
            draw_date = datetime(year, month, day)
        else:
            draw_date = datetime.now()

        # Extract draw number if present
        draw_num_match = re.search(r'Draw\s+(\d+)', text, re.I)
        draw_number = int(draw_num_match.group(1)) if draw_num_match else 0

        # Extract main numbers using the specific ball class
        main_ball_class = config['main_ball_class']
        main_balls = box.find_all("div", class_=lambda c: c and main_ball_class in c and 'bonus' not in c.lower() and 'powerball-powerball' not in c)

        main_numbers = []
        for ball in main_balls:
            num_text = ball.get_text().strip()
            if num_text.isdigit():
                num = int(num_text)
                if num not in main_numbers:  # Avoid duplicates
                    main_numbers.append(num)
                    if len(main_numbers) >= main_count:
                        break

        # Extract bonus numbers if applicable
        bonus_numbers = []
        bonus_ball_class = config.get('bonus_ball_class')
        if bonus_ball_class and bonus_count > 0:
            bonus_balls = box.find_all("div", class_=lambda c: c and bonus_ball_class in c)
            for ball in bonus_balls:
                num_text = ball.get_text().strip()
                if num_text.isdigit():
                    num = int(num_text)
                    if num not in bonus_numbers:
                        bonus_numbers.append(num)
                        if len(bonus_numbers) >= bonus_count:
                            break

        # Validate we have enough numbers
        if len(main_numbers) < main_count:
            logger.debug(f"Not enough main numbers: {len(main_numbers)} < {main_count}")
            return None

        return Draw(
            game=game,
            draw_number=draw_number,
            draw_date=draw_date,
            main_numbers=main_numbers,
            bonus_numbers=bonus_numbers
        )

    except Exception as e:
        logger.debug(f"Failed to parse resultBox: {e}")
        return None


# =============================================================================
# Public API
# =============================================================================

async def fetch_results_for_game(game: str, limit: int = 20) -> List[Draw]:
    """Fetch results for a specific game."""
    fetchers = {
        "lotto": fetch_lotto_results,
        "lotto_plus_1": fetch_lotto_plus_1_results,
        "lotto_plus_2": fetch_lotto_plus_2_results,
        "powerball": fetch_powerball_results,
        "powerball_plus": fetch_powerball_plus_results,
        "daily_lotto": fetch_daily_lotto_results,
    }

    fetcher = fetchers.get(game)
    if not fetcher:
        raise ValueError(f"Unknown game: {game}. Available: {list(fetchers.keys())}")

    return await fetcher(limit)


def fetch_results_sync(game: str, limit: int = 20) -> List[Draw]:
    """Synchronous wrapper for fetching results."""
    return asyncio.run(fetch_results_for_game(game, limit))


async def fetch_all_games(limit: int = 20) -> dict:
    """Fetch results for all games concurrently."""
    games = ["lotto", "lotto_plus_1", "lotto_plus_2", "powerball", "powerball_plus", "daily_lotto"]

    tasks = [fetch_results_for_game(game, limit) for game in games]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        game: result if not isinstance(result, Exception) else []
        for game, result in zip(games, results)
    }


# =============================================================================
# Extended Fetching for 2-Year Historical Data
# =============================================================================

ARCHIVE_YEARS = [2025, 2024, 2023]  # Years to fetch from archive

async def fetch_extended_history(game: str, target_days: int = 730) -> Tuple[List[Draw], dict]:
    """
    Fetch up to 2 years of historical draws for a game.

    Attempts multiple sources:
    1. Primary: lottery.co.za results page
    2. Archive: lottery.co.za yearly archives
    3. Fallback: Alternative aggregator sites

    Args:
        game: Game identifier
        target_days: Target number of days to fetch (default 730 = 2 years)

    Returns:
        Tuple of (draws list, metadata dict with coverage info)
    """
    all_draws = []
    sources_used = []
    errors = []

    config = GAME_CONFIG.get(game)
    if not config:
        return [], {"error": f"Unknown game: {game}"}

    # 1. Fetch from main results page
    try:
        main_draws = await _fetch_from_lottery_co_za(game, limit=50)
        all_draws.extend(main_draws)
        sources_used.append(f"{LOTTERY_CO_ZA_BASE}{config['url']}")
        logger.info(f"Fetched {len(main_draws)} draws from main page")
    except Exception as e:
        errors.append(f"Main page: {e}")
        logger.warning(f"Failed to fetch main page: {e}")

    # 2. Fetch from yearly archives
    for year in ARCHIVE_YEARS:
        try:
            archive_draws = await _fetch_yearly_archive(game, year)
            all_draws.extend(archive_draws)
            if archive_draws:
                sources_used.append(f"{LOTTERY_CO_ZA_BASE}{config['url']}/{year}")
                logger.info(f"Fetched {len(archive_draws)} draws from {year} archive")
        except Exception as e:
            errors.append(f"Archive {year}: {e}")
            logger.debug(f"Failed to fetch {year} archive: {e}")

    # 3. Try fallback source if insufficient data
    if len(all_draws) < target_days // 2:
        try:
            fallback_draws = await _fetch_from_fallback(game)
            all_draws.extend(fallback_draws)
            if fallback_draws:
                sources_used.append("https://za.lottonumbers.com")
                logger.info(f"Fetched {len(fallback_draws)} draws from fallback")
        except Exception as e:
            errors.append(f"Fallback: {e}")
            logger.debug(f"Failed to fetch fallback: {e}")

    # Deduplicate by date
    seen_dates = set()
    unique_draws = []
    for draw in all_draws:
        date_key = draw.draw_date.date()
        if date_key not in seen_dates:
            seen_dates.add(date_key)
            unique_draws.append(draw)

    # Sort by date (newest first)
    unique_draws.sort(key=lambda d: d.draw_date, reverse=True)

    # Calculate coverage
    if unique_draws:
        date_range = (unique_draws[0].draw_date - unique_draws[-1].draw_date).days
        coverage_days = len(unique_draws)
    else:
        date_range = 0
        coverage_days = 0

    metadata = {
        "total_draws": len(unique_draws),
        "coverage_days": coverage_days,
        "date_range_days": date_range,
        "coverage_percent": round(coverage_days / target_days * 100, 1),
        "sources": sources_used,
        "errors": errors if errors else None,
        "target_days": target_days
    }

    logger.info(f"Extended fetch complete: {len(unique_draws)} draws, {metadata['coverage_percent']}% coverage")
    return unique_draws, metadata


async def _fetch_yearly_archive(game: str, year: int) -> List[Draw]:
    """Fetch draws from yearly archive page (table format)."""
    config = GAME_CONFIG.get(game)
    if not config:
        return []

    url = f"{LOTTERY_CO_ZA_BASE}{config['url']}/{year}"

    try:
        html_content = await fetch_with_retry(url, use_cache=True)
    except FetchError:
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    game_settings = GAMES.get(game)
    main_count = game_settings.main_numbers if game_settings else 6
    bonus_count = game_settings.bonus_numbers if game_settings else 0
    main_ball_class = config['main_ball_class']
    bonus_ball_class = config.get('bonus_ball_class')

    draws = []

    # Archive pages use tables
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")

        for row in rows[1:]:  # Skip header row
            try:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                # Extract date from first cell
                date_text = cells[0].get_text(strip=True)
                date_match = re.search(
                    r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(202\d)',
                    date_text,
                    re.I
                )
                if not date_match:
                    continue

                day = int(date_match.group(1))
                month = MONTH_MAP[date_match.group(2).lower()]
                year_parsed = int(date_match.group(3))
                draw_date = datetime(year_parsed, month, day)

                # Extract draw number from second cell
                draw_num_text = cells[1].get_text(strip=True)
                draw_number = int(draw_num_text) if draw_num_text.isdigit() else 0

                # Extract numbers from ball elements in third cell (or entire row)
                ball_elems = row.find_all("div", class_=lambda c: c and main_ball_class in c and 'bonus' not in str(c).lower())

                main_numbers = []
                for ball in ball_elems:
                    num_text = ball.get_text(strip=True)
                    if num_text.isdigit():
                        num = int(num_text)
                        if num not in main_numbers:
                            main_numbers.append(num)
                            if len(main_numbers) >= main_count:
                                break

                # Extract bonus numbers if applicable
                bonus_numbers = []
                if bonus_ball_class and bonus_count > 0:
                    bonus_elems = row.find_all("div", class_=lambda c: c and bonus_ball_class in c)
                    for ball in bonus_elems:
                        num_text = ball.get_text(strip=True)
                        if num_text.isdigit():
                            bonus_numbers.append(int(num_text))
                            if len(bonus_numbers) >= bonus_count:
                                break

                if len(main_numbers) >= main_count:
                    draws.append(Draw(
                        game=game,
                        draw_number=draw_number,
                        draw_date=draw_date,
                        main_numbers=main_numbers[:main_count],
                        bonus_numbers=bonus_numbers
                    ))

            except Exception as e:
                logger.debug(f"Failed to parse archive row: {e}")
                continue

    logger.info(f"Parsed {len(draws)} draws from {year} archive")
    return draws


async def _fetch_from_fallback(game: str) -> List[Draw]:
    """Fetch from fallback source (za.lottonumbers.com)."""
    # Map game names to fallback URLs
    fallback_urls = {
        "daily_lotto": "https://za.lottonumbers.com/daily-lotto/results",
        "lotto": "https://za.lottonumbers.com/lotto/results",
        "powerball": "https://za.lottonumbers.com/powerball/results",
        "powerball_plus": "https://za.lottonumbers.com/powerball-plus/results",
        "lotto_plus_1": "https://za.lottonumbers.com/lotto-plus-1/results",
        "lotto_plus_2": "https://za.lottonumbers.com/lotto-plus-2/results",
    }

    url = fallback_urls.get(game)
    if not url:
        return []

    try:
        html_content = await fetch_with_retry(url, use_cache=True)
    except FetchError:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    draws = []

    # Parse lottonumbers.com structure (different from lottery.co.za)
    result_items = soup.find_all("li", class_=re.compile(r"result", re.I))

    game_settings = GAMES.get(game)
    main_count = game_settings.main_numbers if game_settings else 6

    for item in result_items[:100]:  # Limit to prevent over-fetching
        try:
            # Extract date
            date_elem = item.find(class_=re.compile(r"date", re.I))
            if date_elem:
                date_text = date_elem.get_text()
                date_match = re.search(
                    r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(202\d)',
                    date_text,
                    re.I
                )
                if date_match:
                    day = int(date_match.group(1))
                    month = MONTH_MAP[date_match.group(2).lower()]
                    year = int(date_match.group(3))
                    draw_date = datetime(year, month, day)
                else:
                    continue
            else:
                continue

            # Extract numbers
            ball_elems = item.find_all(class_=re.compile(r"ball", re.I))
            numbers = []
            for ball in ball_elems:
                num_text = ball.get_text().strip()
                if num_text.isdigit():
                    numbers.append(int(num_text))

            if len(numbers) >= main_count:
                draws.append(Draw(
                    game=game,
                    draw_number=0,
                    draw_date=draw_date,
                    main_numbers=numbers[:main_count],
                    bonus_numbers=numbers[main_count:] if len(numbers) > main_count else []
                ))

        except Exception as e:
            logger.debug(f"Failed to parse fallback item: {e}")
            continue

    return draws


def fetch_extended_history_sync(game: str, target_days: int = 730) -> Tuple[List[Draw], dict]:
    """Synchronous wrapper for extended history fetch."""
    return asyncio.run(fetch_extended_history(game, target_days))
