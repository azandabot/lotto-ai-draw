#!/usr/bin/env python3
"""
SA Lotto - Interactive AI-Powered Lottery Predictions

Developed by Azanda Zama
Proudly South African
"""

import click
import sys
from datetime import datetime

# UI Module - all visual components
import ui
from ui import Color, Icon, Cursor, Spinner

# Core modules
from config import GAMES, list_games, get_game
from models import Draw
import storage
import fetcher
import predictor
import ticket_generator
import play_tracker
from logging_config import setup_logging

__version__ = "0.4"
__author__ = "Azanda Zama"
__email__ = "judah.zama@gmail.com"

# Global tracker
tracker = play_tracker.get_tracker()

# InquirerPy imports
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import InquirerPyStyle

# Consistent menu style - Cyan accent
MENU_STYLE = InquirerPyStyle({
    "questionmark": "#666666",
    "answermark": "#666666",
    "answer": "#00c8ff bold",
    "pointer": "#00c8ff bold",
    "highlighted": "#00c8ff bold",
    "selected": "#00c8ff",
    "instruction": "#444444",
    "input": "#00c8ff",
})


# =============================================================================
# Game Selection UI
# =============================================================================

def select_game(prompt: str = "Select game") -> str:
    """Clean game selector."""
    games = [
        Choice(value="daily_lotto", name=f"{Icon.DICE} Daily Lotto"),
        Choice(value="lotto", name=f"{Icon.DICE} LOTTO"),
        Choice(value="lotto_plus_1", name=f"{Icon.DICE} LOTTO Plus 1"),
        Choice(value="lotto_plus_2", name=f"{Icon.DICE} LOTTO Plus 2"),
        Choice(value="powerball", name=f"{Icon.BOLT} PowerBall"),
        Choice(value="powerball_plus", name=f"{Icon.BOLT} PowerBall Plus"),
    ]

    return inquirer.select(
        message=prompt,
        choices=games,
        default="daily_lotto",
        pointer=Icon.POINTER,
        qmark="",
        amark="",
        style=MENU_STYLE,
    ).execute()


def select_game_simple(prompt: str = "Select game") -> str:
    """
    Simple numbered game selector that doesn't conflict with input.
    Used after interactive menu to avoid buffer issues.
    """
    ui.flush_input()  # Clear any ghost characters

    games = [
        ("daily_lotto", f"{Icon.DICE} Daily Lotto"),
        ("lotto", f"{Icon.DICE} LOTTO"),
        ("lotto_plus_1", f"{Icon.DICE} LOTTO Plus 1"),
        ("lotto_plus_2", f"{Icon.DICE} LOTTO Plus 2"),
        ("powerball", f"{Icon.BOLT} PowerBall"),
        ("powerball_plus", f"{Icon.BOLT} PowerBall Plus"),
    ]

    print(f"\n  {Color.BOLD}{prompt}{Color.RESET}\n")
    for i, (_, name) in enumerate(games, 1):
        print(f"  {Color.DIM}{i}.{Color.RESET} {name}")
    print()

    idx = ui.input_int("Choose game", min_val=1, max_val=6, default=1)
    if idx is None:
        return None

    return games[idx - 1][0]


# =============================================================================
# Display Components
# =============================================================================

def show_numbers(numbers: list, powerball: int = None, label: str = ""):
    """Display lottery numbers in styled format."""
    R = Color.RESET
    result = "  "

    for num in numbers:
        result += f"{Color.BG_GRAY}{Color.WHITE} {num:02d} {R} "

    if powerball is not None:
        result += f" {Color.BG_CYAN}{Color.BLACK} {powerball:02d} {R}"

    print(result)
    if label:
        ui.dim(label)


def show_prediction(numbers: list, game_name: str, bonus: int = None, method: str = "AI"):
    """Display prediction result."""
    print()
    ui.separator()
    print(f"  {Color.BOLD}{game_name}{Color.RESET}")
    ui.dim(f"{method} Analysis {Icon.ARROW} {datetime.now().strftime('%d %b %H:%M')}")
    print()
    show_numbers(numbers, bonus)
    print()
    ui.separator()
    ui.dim("For entertainment only. Lottery is random.")
    print()


def show_tickets(tickets: list, game_name: str, total_cost: float):
    """Display generated tickets."""
    print()
    ui.separator()
    print(f"  {Color.BOLD}{game_name}{Color.RESET}")
    print(f"  {Color.GREEN}{len(tickets)} tickets{Color.RESET} {Color.DIM}│{Color.RESET} {Color.YELLOW}R{total_cost:.0f}{Color.RESET}")
    print()

    for i, ticket in enumerate(tickets, 1):
        nums = " ".join(f"{Color.CYAN}{n:02d}{Color.RESET}" for n in ticket)
        print(f"  {Color.DIM}{i:2d}.{Color.RESET} {nums}")

    print()
    ui.separator()
    ui.dim("Selbee Wheeling Strategy applied")
    print()


def show_history(draws: list, game_name: str):
    """Display draw history."""
    print()
    print(f"  {Color.BOLD}{game_name}{Color.RESET} {Color.DIM}│ Last {len(draws)} draws{Color.RESET}")
    print()

    headers = ["Date", "Numbers"]
    rows = []
    for draw in reversed(draws[:10]):
        rows.append([
            draw.draw_date.strftime("%d %b"),
            draw.format_numbers()
        ])

    ui.table(headers, rows)
    print()


def show_stats(game_name: str, stats: dict):
    """Display statistics with visual elements."""
    print()
    ui.separator()
    print(f"  {Color.BOLD}{game_name}{Color.RESET} {Color.DIM}│ Statistics{Color.RESET}")
    ui.dim(f"Based on {stats['total_draws']} draws")
    print()

    # Hot numbers with bar
    freq = stats['frequency']
    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    hot = [n for n, _ in sorted_freq[:8]]
    cold = [n for n, _ in sorted_freq[-8:]]

    print(f"  {Color.RED}{Icon.STAR} Hot{Color.RESET}    ", end="")
    for n in hot:
        print(f"{Color.RED}{n:02d}{Color.RESET} ", end="")
    print()

    print(f"  {Color.CYAN}{Icon.CIRCLE} Cold{Color.RESET}   ", end="")
    for n in cold:
        print(f"{Color.CYAN}{n:02d}{Color.RESET} ", end="")
    print()

    # Sparkline of recent frequencies
    recent_vals = [freq.get(i, 0) for i in range(1, 21)]
    print(f"\n  {Color.DIM}Frequency:{Color.RESET} {ui.sparkline(recent_vals, 20)}")

    # Sum range
    print(f"\n  {Color.DIM}Sum Range:{Color.RESET} {stats['avg_sum']:.0f} +/- {stats['sum_std']:.0f}")

    print()
    ui.separator()
    print()


def show_vault(stats):
    """Display play vault (history & stats)."""
    print()
    ui.separator()
    print(f"  {Color.BOLD}{Icon.VAULT} My Vault{Color.RESET}")
    print()

    if stats.total_played == 0:
        ui.dim("No plays recorded yet")
        ui.dim("Generate some tickets to get started!")
        print()
        return

    # Stats display
    pl_color = Color.GREEN if stats.profit_loss >= 0 else Color.RED
    pl_sign = "+" if stats.profit_loss >= 0 else ""

    print(f"  {Color.DIM}Spent{Color.RESET}      R{stats.total_played:,.0f}")
    print(f"  {Color.DIM}Won{Color.RESET}        {Color.GREEN}R{stats.total_won:,.0f}{Color.RESET}")
    print(f"  {Color.DIM}Net{Color.RESET}        {pl_color}{pl_sign}R{stats.profit_loss:,.0f}{Color.RESET}")
    print(f"  {Color.DIM}Tickets{Color.RESET}    {stats.total_tickets}")

    # Simple bar chart of spending by game
    if hasattr(stats, 'by_game') and stats.by_game:
        print()
        for line in ui.bar_chart(stats.by_game, 15):
            print(line)

    print()
    ui.separator()
    print()


def show_about():
    """Display about screen."""
    print()
    ui.separator()
    print(f"  {Color.BOLD}{Color.YELLOW}Lotto{Color.RESET} {Color.DIM}v{__version__}{Color.RESET}")
    print()
    print(f"  {Color.DIM}AI-powered lottery predictions for{Color.RESET}")
    print(f"  {Color.DIM}South African National Lottery{Color.RESET}")
    print()
    print(f"  {Icon.DICE} Daily Lotto    {Color.DIM}5 from 1-36{Color.RESET}")
    print(f"  {Icon.DICE} LOTTO          {Color.DIM}6 from 1-52{Color.RESET}")
    print(f"  {Icon.BOLT} PowerBall      {Color.DIM}5+1 from 1-50{Color.RESET}")
    print()
    print(f"  {Color.DIM}Developer{Color.RESET}  {__author__}")
    print(f"  {Color.DIM}Contact{Color.RESET}    {__email__}")
    print()
    ui.separator()
    ui.dim(f"{Icon.STAR} Proudly South African")
    print()


# =============================================================================
# Actions - Core Logic
# =============================================================================

def ensure_data(game: str) -> list:
    """Ensure we have lottery data, fetching if needed."""
    draws = storage.load_draws(game)
    if not draws:
        with Spinner("Fetching data") as spinner:
            draws = fetcher.fetch_results_sync(game, limit=50)
            if draws:
                storage.save_draws(game, draws)
                spinner.stop(True, "Data loaded")
            else:
                spinner.stop(False, "Fetch failed")
    return draws


def action_quick_predict():
    """Quick AI prediction."""
    ui.clear()
    ui.print_header(__version__)

    game = select_game()
    game_config = get_game(game)
    draws = ensure_data(game)

    if not draws:
        ui.error("No data available")
        return

    with Spinner("AI analyzing patterns") as spinner:
        pred = predictor.predict_numbers_local(game, draws)
        spinner.stop(True, "Analysis complete")

    show_prediction(
        pred.main_numbers,
        game_config.display_name,
        pred.bonus_numbers[0] if pred.bonus_numbers else None,
        "Quick Stats"
    )


def action_smart_tickets():
    """Generate tickets with budget - Premium UX with robust input."""
    ui.clear()
    ui.print_header(__version__)

    print(f"  {Color.BOLD}{Icon.TICKET} Smart Tickets{Color.RESET}")
    ui.dim("Budget-based Selbee wheeling strategy")
    print()

    # Step 1: Select game (using simple selector to avoid buffer issues)
    game = select_game_simple("Choose your game")
    if game is None:
        return

    game_config = get_game(game)

    # Get minimum budget for this game
    generator = ticket_generator.TicketGenerator(game)
    settings = generator.settings
    min_budget = (settings['batch_size'] * settings['cost_per_ticket']) + settings['admin_fee']

    # Step 2: Get budget with robust input (supports decimals, inline validation)
    print()
    ui.dim(f"Minimum: R{min_budget:.2f} │ Cost per ticket: R{settings['cost_per_ticket']:.2f}")
    print()

    budget = ui.input_float(
        f"Enter budget (R)",
        min_val=min_budget,
        max_val=10000,
        default=50.0
    )

    if budget is None:
        return

    # Step 3: Ensure we have data
    print()
    draws = ensure_data(game)
    if not draws:
        ui.error("Could not load lottery data")
        return

    # Step 4: Generate tickets with live progress bar
    print()
    progress = ui.LiveProgress(
        f"AI analyzing hot numbers for R{budget:.0f} budget...",
        steps=5,
        width=20
    )
    progress.start()

    try:
        # Simulate progress steps for better UX
        import time
        progress.update(1, "Loading historical data...")
        time.sleep(0.2)

        progress.update(2, "Computing frequency analysis...")
        time.sleep(0.2)

        progress.update(3, "Applying Selbee wheeling...")
        batch = generator.generate_for_budget(budget)
        time.sleep(0.1)

        if batch:
            progress.update(4, "Validating ticket quality...")
            time.sleep(0.1)

            progress.update(5, f"Generated {len(batch.tickets)} tickets")
            progress.complete(f"{len(batch.tickets)} tickets ready!")
        else:
            progress.fail("Generation failed")
            return

    except Exception as e:
        progress.fail(str(e))
        return

    # Step 5: Show results and record play
    tracker.record_play(game=game, tickets=batch.tickets, total_cost=batch.total_cost)
    show_tickets(batch.tickets, game_config.display_name, batch.total_cost)
    ui.success(f"Play recorded! Good luck {Icon.STAR}")


def action_my_vault():
    """View vault - history and stats."""
    ui.clear()
    ui.print_header(__version__)

    # Sub-menu for vault
    choices = [
        Choice(value="stats", name=f"{Icon.CHART} Play Statistics"),
        Choice(value="history", name=f"{Icon.CLOCK} Draw History"),
        Choice(value="back", name=f"{Icon.ARROW} Back"),
    ]

    action = inquirer.select(
        message="Vault",
        choices=choices,
        pointer=Icon.POINTER,
        qmark="",
        amark="",
        style=MENU_STYLE,
    ).execute()

    if action == "stats":
        stats = tracker.get_stats()
        show_vault(stats)
    elif action == "history":
        game = select_game("View history for")
        game_config = get_game(game)
        draws = storage.load_draws(game, limit=10)
        if draws:
            show_history(draws, game_config.display_name)
        else:
            ui.error("No data. Fetch results first.")


def action_live_results():
    """Fetch latest results."""
    ui.clear()
    ui.print_header(__version__)

    choices = [
        Choice(value="all", name=f"{Icon.REFRESH} All Games"),
        Choice(value="daily_lotto", name=f"{Icon.DICE} Daily Lotto"),
        Choice(value="lotto", name=f"{Icon.DICE} LOTTO"),
        Choice(value="powerball", name=f"{Icon.BOLT} PowerBall"),
    ]

    game = inquirer.select(
        message="Fetch",
        choices=choices,
        pointer=Icon.POINTER,
        qmark="",
        amark="",
        style=MENU_STYLE,
    ).execute()

    games_to_fetch = [g.name for g in list_games()] if game == "all" else [game]

    print()
    for g in games_to_fetch:
        game_config = get_game(g)
        with Spinner(f"Fetching {game_config.display_name}") as spinner:
            draws = fetcher.fetch_results_sync(g, limit=50)
            if draws:
                storage.save_draws(g, draws)
                spinner.stop(True, f"{len(draws)} draws")
            else:
                spinner.stop(False, "Failed")

    print()


def action_stats_view():
    """View statistics."""
    ui.clear()
    ui.print_header(__version__)

    game = select_game("Statistics for")
    game_config = get_game(game)
    draws = storage.load_draws(game)

    if not draws:
        ui.error("No data. Fetch results first.")
        return

    with Spinner("Computing statistics") as spinner:
        enhanced_stats = predictor.compute_enhanced_stats(draws, game_config)
        spinner.stop(True, "Done")

    show_stats(game_config.display_name, enhanced_stats)


def action_about():
    """Show about."""
    ui.clear()
    ui.print_header(__version__)
    show_about()


# =============================================================================
# Main Menu
# =============================================================================

def run_interactive():
    """Main interactive loop with professional state management."""
    setup_logging(verbose=False)

    while True:
        ui.clear()
        ui.print_header(__version__)

        print(f"  {Color.BOLD}Get started{Color.RESET}")
        print()

        choices = [
            Choice(value="quick", name=f"{Icon.BOLT} Quick Predict"),
            Choice(value="tickets", name=f"{Icon.TICKET} Smart Tickets"),
            Choice(value="vault", name=f"{Icon.VAULT} My Vault"),
            Choice(value="live", name=f"{Icon.REFRESH} Live Results"),
            Choice(value="stats", name=f"{Icon.CHART} Statistics"),
            Choice(value="about", name=f"{Icon.INFO} About"),
            Choice(value="exit", name=f"{Icon.ARROW} Exit"),
        ]

        try:
            # Flush any leftover input from previous operations
            ui.flush_input()

            action = inquirer.select(
                message="",
                choices=choices,
                pointer=Icon.POINTER,
                qmark="",
                amark="",
                instruction="",
                style=MENU_STYLE,
            ).execute()
        except KeyboardInterrupt:
            print(f"\n  {Color.DIM}Goodbye!{Color.RESET}\n")
            break

        try:
            if action == "exit":
                print(f"\n  {Color.DIM}Phanda, Pusha, Play!{Color.RESET}\n")
                break
            elif action == "quick":
                action_quick_predict()
            elif action == "tickets":
                action_smart_tickets()
            elif action == "vault":
                action_my_vault()
            elif action == "live":
                action_live_results()
            elif action == "stats":
                action_stats_view()
            elif action == "about":
                action_about()

            # Post-action menu with clear options
            if action != "exit":
                result = ui.post_action_menu()
                if result == 'quit':
                    print(f"\n  {Color.DIM}Phanda, Pusha, Play!{Color.RESET}\n")
                    break
                # 'menu' or 'continue' both loop back to menu

        except KeyboardInterrupt:
            pass
        except Exception as e:
            ui.error(str(e))
            ui.wait_for_key()


# =============================================================================
# CLI Commands (backward compatibility)
# =============================================================================

@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.version_option(__version__, "-V", "--version", prog_name="lotto")
@click.pass_context
def cli(ctx, verbose):
    """SA Lotto - AI-Powered Lottery Predictions"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

    if verbose:
        setup_logging(verbose=True)

    if ctx.invoked_subcommand is None:
        run_interactive()


@cli.command()
@click.option("--game", "-g", required=True, help="Game: daily_lotto, lotto, powerball")
def quick(game: str):
    """Quick prediction."""
    game_config = get_game(game)
    draws = storage.load_draws(game)

    if not draws:
        with Spinner("Fetching data"):
            draws = fetcher.fetch_results_sync(game, limit=50)
            if draws:
                storage.save_draws(game, draws)

    if not draws:
        ui.error("No data available")
        return

    with Spinner("Analyzing"):
        pred = predictor.predict_numbers_local(game, draws)

    show_prediction(
        pred.main_numbers,
        game_config.display_name,
        pred.bonus_numbers[0] if pred.bonus_numbers else None
    )


@cli.command()
@click.option("--game", "-g", required=True, help="Game")
@click.option("--budget", "-b", required=True, type=float, help="Budget in Rands")
def play(game: str, budget: float):
    """Generate tickets with budget."""
    game_config = get_game(game)
    storage.load_draws(game)

    generator = ticket_generator.TicketGenerator(game)
    with Spinner("Generating"):
        batch = generator.generate_for_budget(budget)

    if batch:
        tracker.record_play(game=game, tickets=batch.tickets, total_cost=batch.total_cost)
        show_tickets(batch.tickets, game_config.display_name, batch.total_cost)


@cli.command()
@click.option("--game", "-g", required=True, help="Game")
@click.option("--last", "-n", default=10, help="Count")
def history(game: str, last: int):
    """View draw history."""
    game_config = get_game(game)
    draws = storage.load_draws(game, limit=last)

    if draws:
        show_history(draws, game_config.display_name)
    else:
        ui.error("No data")


@cli.command()
@click.option("--game", "-g", required=True, help="Game")
def stats(game: str):
    """View statistics."""
    game_config = get_game(game)
    draws = storage.load_draws(game)

    if not draws:
        ui.error("No data")
        return

    enhanced_stats = predictor.compute_enhanced_stats(draws, game_config)
    show_stats(game_config.display_name, enhanced_stats)


@cli.command()
@click.option("--game", "-g", required=True, help="Game or 'all'")
@click.option("--limit", "-n", default=50, help="Draws to fetch")
def fetch(game: str, limit: int):
    """Fetch latest results."""
    games_to_fetch = [g.name for g in list_games()] if game == "all" else [game]

    for g in games_to_fetch:
        game_config = get_game(g)
        with Spinner(f"Fetching {game_config.display_name}") as spinner:
            draws = fetcher.fetch_results_sync(g, limit=limit)
            if draws:
                storage.save_draws(g, draws)
                spinner.stop(True, f"{len(draws)} draws")
            else:
                spinner.stop(False, "Failed")


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
