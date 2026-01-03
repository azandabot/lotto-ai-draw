#!/usr/bin/env python3
"""
UI Components for SA Lotto CLI
Professional terminal interface inspired by gh, vercel, and claude-code CLIs.
"""

import sys
import io
import time
import threading
from typing import Optional, List, Callable, Any

# =============================================================================
# Terminal Setup & ANSI Codes
# =============================================================================

def setup_terminal():
    """Configure terminal for UTF-8 and ANSI support."""
    if sys.platform == 'win32':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            # Enable ANSI on Windows
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass

# ANSI escape codes
class Color:
    """ANSI TrueColor codes."""
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"

    # Foreground
    WHITE = "\x1b[97m"
    BLACK = "\x1b[30m"
    RED = "\x1b[38;2;255;82;82m"
    GREEN = "\x1b[38;2;80;250;123m"
    YELLOW = "\x1b[38;2;255;221;0m"
    CYAN = "\x1b[38;2;0;200;255m"
    MAGENTA = "\x1b[38;2;228;0;43m"
    GRAY = "\x1b[38;2;128;128;128m"

    # Logo colors
    LOGO_YELLOW = "\x1b[38;2;255;221;0m"
    LOGO_BLACK = "\x1b[38;2;0;0;0m"
    LOGO_MAGENTA = "\x1b[38;2;228;0;43m"
    LOGO_GREEN = "\x1b[38;2;0;148;68m"
    LOGO_CYAN = "\x1b[38;2;0;159;227m"

    # Background
    BG_CYAN = "\x1b[48;2;0;200;255m"
    BG_YELLOW = "\x1b[48;2;255;221;0m"
    BG_GREEN = "\x1b[48;2;80;250;123m"
    BG_RED = "\x1b[48;2;255;82;82m"
    BG_GRAY = "\x1b[48;2;60;60;60m"

class Cursor:
    """ANSI cursor control."""
    UP = "\x1b[F"
    DOWN = "\x1b[E"
    CLEAR_LINE = "\x1b[2K"
    HIDE = "\x1b[?25l"
    SHOW = "\x1b[?25h"
    HOME = "\x1b[H"
    CLEAR_SCREEN = "\x1b[2J"

    @staticmethod
    def up(n: int = 1) -> str:
        return f"\x1b[{n}A"

    @staticmethod
    def down(n: int = 1) -> str:
        return f"\x1b[{n}B"

    @staticmethod
    def move_to(row: int, col: int = 1) -> str:
        return f"\x1b[{row};{col}H"

# =============================================================================
# Icons (UTF-8)
# =============================================================================

class Icon:
    """UTF-8 icons for clean UI."""
    BOLT = "⚡"
    TICKET = "🎫"
    VAULT = "🔐"
    REFRESH = "↻"
    INFO = "ℹ"
    CHECK = "✓"
    CROSS = "✗"
    ARROW = "→"
    POINTER = "›"
    DOT = "●"
    CIRCLE = "○"
    STAR = "★"
    SPARKLE = "✦"
    DICE = "🎲"
    CHART = "📊"
    CLOCK = "⏱"
    MONEY = "💰"
    TROPHY = "🏆"

# =============================================================================
# Banner - Half-Block Rendering
# =============================================================================

_LOGO_DATA = [
    "....YYYYYY....",
    "..YYYYYYYYYY..",
    ".YYYMKYYKGYYY.",
    "YYYYMKYYKGYYYY",
    "YYYYYKKKKYYYYY",
    "YYYYYKKKKYYYYY",
    "YYYYCKYYKCYYYY",
    ".YYYCKYYKCYYY.",
    "..YYYYYYYYYY..",
    "....YYYYYY....",
]

_COLORS = {
    'Y': (255, 221, 0),
    'K': (0, 0, 0),
    'M': (228, 0, 43),
    'G': (0, 148, 68),
    'C': (0, 159, 227),
    '.': None,
}

def _fg(r, g, b):
    return f"\x1b[38;2;{r};{g};{b}m"

def _bg(r, g, b):
    return f"\x1b[48;2;{r};{g};{b}m"

def _render_logo():
    """Render logo using half-block technique."""
    lines = []
    for i in range(0, len(_LOGO_DATA), 2):
        top_row = _LOGO_DATA[i]
        bottom_row = _LOGO_DATA[i + 1]
        line = ""
        for j in range(len(top_row)):
            top_color = _COLORS.get(top_row[j])
            bottom_color = _COLORS.get(bottom_row[j])
            if top_color is None and bottom_color is None:
                line += " "
            elif top_color is not None and bottom_color is None:
                line += _fg(*top_color) + "▀" + Color.RESET
            elif top_color is None and bottom_color is not None:
                line += _fg(*bottom_color) + "▄" + Color.RESET
            else:
                line += _fg(*top_color) + _bg(*bottom_color) + "▀" + Color.RESET
        lines.append(line)
    return lines

def get_banner(version: str = "0.4") -> List[str]:
    """Generate complete banner with text and logo."""
    logo = _render_logo()
    R = Color.RESET
    W = f"{Color.BOLD}{Color.WHITE}"
    C = _fg(0, 159, 227)
    G = _fg(0, 148, 68)
    M = _fg(228, 0, 43)

    text = [
        ("", 0),
        (f"{W}PHANDA{R}", 6),
        (f"{W}PUSHA{R}  {C}{Icon.DOT}{R}", 8),
        (f"{W}PLAY{R}   {G}{Icon.DOT}{R} {M}{Icon.DOT}{R}", 10),
        ("", 0),
    ]

    output = []
    for i in range(5):
        txt, vis_len = text[i]
        padding = " " * (10 - vis_len)
        output.append(f"  {txt}{padding}    {logo[i]}")

    return output

def print_banner(version: str = "0.4"):
    """Print the complete banner."""
    for line in get_banner(version):
        print(line)

def print_header(version: str = "0.4"):
    """Print full header with banner and subtitle."""
    print()
    print_banner(version)
    print()
    # Minimal subtitle
    print(f"  {Color.DIM}Lotto {Color.GRAY}│{Color.DIM} Powered by AI {Color.GRAY}│{Color.DIM} v{version}{Color.RESET}")
    print(f"  {Color.DIM}Developed by Azanda Zama{Color.RESET}")
    print()

# =============================================================================
# Spinner & Progress
# =============================================================================

class Spinner:
    """Animated spinner for async operations."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Loading"):
        self.message = message
        self._running = False
        self._thread = None

    def _animate(self):
        idx = 0
        while self._running:
            frame = self.FRAMES[idx % len(self.FRAMES)]
            print(f"\r  {Color.CYAN}{frame}{Color.RESET} {self.message}...", end="", flush=True)
            idx += 1
            time.sleep(0.08)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self, success: bool = True, message: str = None):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.2)
        icon = f"{Color.GREEN}{Icon.CHECK}" if success else f"{Color.RED}{Icon.CROSS}"
        msg = message or self.message
        print(f"\r{Cursor.CLEAR_LINE}  {icon}{Color.RESET} {msg}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

def progress_bar(current: int, total: int, width: int = 20, label: str = "") -> str:
    """Generate a progress bar string."""
    filled = int(width * current / total)
    empty = width - filled
    bar = f"{Color.GREEN}{'█' * filled}{Color.GRAY}{'░' * empty}{Color.RESET}"
    percent = int(100 * current / total)
    return f"  {bar} {percent:3d}% {Color.DIM}{label}{Color.RESET}"

def sparkline(values: List[float], width: int = 10) -> str:
    """Generate a sparkline from values."""
    if not values:
        return ""

    blocks = " ▁▂▃▄▅▆▇█"
    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val if max_val != min_val else 1

    # Normalize and map to blocks
    result = ""
    step = max(1, len(values) // width)
    for i in range(0, min(len(values), width * step), step):
        normalized = (values[i] - min_val) / range_val
        idx = int(normalized * (len(blocks) - 1))
        result += f"{Color.CYAN}{blocks[idx]}{Color.RESET}"

    return result

def bar_chart(data: dict, max_width: int = 20) -> List[str]:
    """Generate horizontal bar chart."""
    if not data:
        return []

    max_val = max(data.values()) if data.values() else 1
    max_label = max(len(str(k)) for k in data.keys())

    lines = []
    for label, value in data.items():
        bar_len = int(max_width * value / max_val)
        bar = f"{Color.CYAN}{'▇' * bar_len}{Color.RESET}"
        lines.append(f"  {str(label):>{max_label}} {bar} {Color.DIM}{value}{Color.RESET}")

    return lines

# =============================================================================
# Messages
# =============================================================================

def success(message: str, icon: str = Icon.CHECK):
    """Print success message."""
    print(f"  {Color.GREEN}{icon}{Color.RESET} {message}")

def error(message: str, icon: str = Icon.CROSS):
    """Print error message."""
    print(f"  {Color.RED}{icon}{Color.RESET} {message}")

def warning(message: str, icon: str = "⚠"):
    """Print warning message."""
    print(f"  {Color.YELLOW}{icon}{Color.RESET} {message}")

def info(message: str, icon: str = Icon.INFO):
    """Print info message."""
    print(f"  {Color.CYAN}{icon}{Color.RESET} {message}")

def dim(message: str):
    """Print dim/muted message."""
    print(f"  {Color.DIM}{message}{Color.RESET}")

def flash_message(message: str, color: str = Color.GREEN, duration: float = 2.0):
    """Show a message that disappears after duration."""
    print(f"\r{Cursor.CLEAR_LINE}  {color}{message}{Color.RESET}", end="", flush=True)
    time.sleep(duration)
    print(f"\r{Cursor.CLEAR_LINE}", end="", flush=True)

# =============================================================================
# Interactive Menu
# =============================================================================

class Menu:
    """Interactive arrow-key menu."""

    def __init__(self, title: str, options: List[tuple], show_header: bool = True):
        """
        Args:
            title: Menu title
            options: List of (label, icon, handler) tuples
            show_header: Whether to show the banner header
        """
        self.title = title
        self.options = options
        self.show_header = show_header
        self.selected = 0

    def _render_option(self, idx: int, label: str, icon: str, is_selected: bool) -> str:
        """Render a single menu option."""
        if is_selected:
            pointer = f"{Color.CYAN}{Icon.POINTER}{Color.RESET}"
            text = f"{Color.CYAN}{Color.BOLD}{icon} {label}{Color.RESET}"
            return f"  {pointer} {text}"
        else:
            return f"    {Color.DIM}{icon}{Color.RESET} {label}"

    def _clear_menu(self, lines: int):
        """Clear menu lines for refresh."""
        for _ in range(lines):
            print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")

    def display(self) -> Optional[Any]:
        """Display menu and handle input. Returns handler result or None."""
        try:
            # Use InquirerPy for cross-platform arrow key support
            from InquirerPy import inquirer
            from InquirerPy.base.control import Choice
            from InquirerPy.utils import InquirerPyStyle

            # Clear screen and show header
            print(f"{Cursor.CLEAR_SCREEN}{Cursor.HOME}", end="")

            if self.show_header:
                print_header()

            print(f"  {Color.BOLD}{self.title}{Color.RESET}")
            print()

            # Build choices
            choices = []
            for label, icon, handler in self.options:
                if label == "---":
                    continue  # Skip separators for now
                choices.append(Choice(value=handler, name=f"{icon} {label}"))

            # Custom style
            style = InquirerPyStyle({
                "questionmark": "#666666",
                "answermark": "#666666",
                "answer": "#00c8ff bold",
                "pointer": "#00c8ff bold",
                "highlighted": "#00c8ff bold",
                "selected": "#00c8ff",
                "instruction": "#666666",
                "input": "#00c8ff",
            })

            result = inquirer.select(
                message="",
                choices=choices,
                style=style,
                pointer=f"{Icon.POINTER}",
                show_cursor=False,
                qmark="",
                amark="",
            ).execute()

            return result

        except KeyboardInterrupt:
            return None
        except ImportError:
            # Fallback to simple numbered menu
            return self._simple_menu()

    def _simple_menu(self) -> Optional[Any]:
        """Fallback numbered menu if InquirerPy unavailable."""
        print(f"{Cursor.CLEAR_SCREEN}{Cursor.HOME}", end="")

        if self.show_header:
            print_header()

        print(f"  {Color.BOLD}{self.title}{Color.RESET}")
        print()

        for i, (label, icon, _) in enumerate(self.options, 1):
            if label == "---":
                print()
                continue
            print(f"  {Color.CYAN}{i}{Color.RESET}. {icon} {label}")

        print()
        try:
            choice = input(f"  {Color.DIM}Enter choice:{Color.RESET} ")
            idx = int(choice) - 1
            if 0 <= idx < len(self.options):
                return self.options[idx][2]
        except (ValueError, KeyboardInterrupt):
            pass

        return None

# =============================================================================
# Tables & Lists
# =============================================================================

def table(headers: List[str], rows: List[List[str]], title: str = None):
    """Print a formatted table."""
    if title:
        print(f"\n  {Color.BOLD}{title}{Color.RESET}")

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Header
    header_str = "  " + "  ".join(f"{Color.DIM}{h:<{widths[i]}}{Color.RESET}" for i, h in enumerate(headers))
    print(header_str)
    print(f"  {Color.DIM}{'─' * (sum(widths) + 2 * len(widths))}{Color.RESET}")

    # Rows
    for row in rows:
        row_str = "  " + "  ".join(f"{str(cell):<{widths[i]}}" for i, cell in enumerate(row))
        print(row_str)

def key_value(data: dict, title: str = None):
    """Print key-value pairs."""
    if title:
        print(f"\n  {Color.BOLD}{title}{Color.RESET}")
        print()

    max_key = max(len(str(k)) for k in data.keys())
    for key, value in data.items():
        print(f"  {Color.DIM}{key:>{max_key}}{Color.RESET}  {value}")

# =============================================================================
# Number Display
# =============================================================================

def lottery_numbers(numbers: List[int], powerball: int = None, highlight: List[int] = None):
    """Display lottery numbers in styled balls."""
    highlight = highlight or []

    result = "  "
    for num in numbers:
        if num in highlight:
            result += f"{Color.BG_GREEN}{Color.BLACK} {num:2d} {Color.RESET} "
        else:
            result += f"{Color.BG_GRAY}{Color.WHITE} {num:2d} {Color.RESET} "

    if powerball is not None:
        result += f" {Color.BG_CYAN}{Color.BLACK} {powerball:2d} {Color.RESET}"

    print(result)

def number_grid(numbers: List[int], cols: int = 10, max_num: int = 52):
    """Display numbers in a grid with frequency coloring."""
    from collections import Counter
    freq = Counter(numbers)
    max_freq = max(freq.values()) if freq else 1

    for row_start in range(1, max_num + 1, cols):
        row = ""
        for num in range(row_start, min(row_start + cols, max_num + 1)):
            f = freq.get(num, 0)
            if f == 0:
                row += f"{Color.DIM}{num:3d}{Color.RESET}"
            elif f >= max_freq * 0.8:
                row += f"{Color.GREEN}{Color.BOLD}{num:3d}{Color.RESET}"
            elif f >= max_freq * 0.5:
                row += f"{Color.YELLOW}{num:3d}{Color.RESET}"
            else:
                row += f"{Color.WHITE}{num:3d}{Color.RESET}"
        print(f"  {row}")

# =============================================================================
# Screen Management
# =============================================================================

def clear():
    """Clear screen and move cursor to top."""
    print(f"{Cursor.CLEAR_SCREEN}{Cursor.HOME}", end="")

def separator(char: str = "─", width: int = 50):
    """Print a separator line."""
    print(f"  {Color.DIM}{char * width}{Color.RESET}")

def blank_lines(n: int = 1):
    """Print blank lines."""
    print("\n" * (n - 1))

def wait_for_key(message: str = "Press Enter to continue..."):
    """Wait for user input."""
    try:
        input(f"\n  {Color.DIM}{message}{Color.RESET}")
    except KeyboardInterrupt:
        pass


# =============================================================================
# Terminal Buffer Management
# =============================================================================

def flush_input():
    """
    Clear any pending input from the terminal buffer.
    Critical for preventing ghost characters after menu selection.
    """
    try:
        if sys.platform == 'win32':
            # Windows: use msvcrt to clear keyboard buffer
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        else:
            # Unix/Linux: use termios to flush input
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except:
        # Fallback: just continue
        pass


def reset_terminal():
    """Reset terminal to a clean state for input."""
    flush_input()
    # Small delay to let terminal settle
    time.sleep(0.05)
    # Show cursor
    print(Cursor.SHOW, end="", flush=True)


# =============================================================================
# Robust Input Prompts
# =============================================================================

def input_float(
    prompt: str,
    min_val: float = None,
    max_val: float = None,
    default: float = None,
    allow_empty: bool = False
) -> Optional[float]:
    """
    Robust float input with inline validation and retry.
    Returns None only on Ctrl+C.
    """
    reset_terminal()

    while True:
        try:
            # Build prompt string
            prompt_str = f"  {Color.CYAN}{Icon.POINTER}{Color.RESET} {prompt}"
            if default is not None:
                prompt_str += f" {Color.DIM}[{default}]{Color.RESET}"
            prompt_str += f": "

            # Get input
            raw = input(prompt_str).strip()

            # Handle empty input
            if not raw:
                if default is not None:
                    return float(default)
                if allow_empty:
                    return None
                # Show inline error and retry
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                print(f"  {Color.RED}{Icon.CROSS} Enter a value{Color.RESET}")
                time.sleep(0.8)
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                continue

            # Parse value
            try:
                value = float(raw)
            except ValueError:
                # Show inline error and retry
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                print(f"  {Color.RED}{Icon.CROSS} Invalid number, try again{Color.RESET}")
                time.sleep(0.8)
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                continue

            # Validate range
            if min_val is not None and value < min_val:
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                print(f"  {Color.RED}{Icon.CROSS} Minimum is {min_val}{Color.RESET}")
                time.sleep(0.8)
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                continue

            if max_val is not None and value > max_val:
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                print(f"  {Color.RED}{Icon.CROSS} Maximum is {max_val}{Color.RESET}")
                time.sleep(0.8)
                print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
                continue

            return value

        except KeyboardInterrupt:
            print()
            return None
        except EOFError:
            return None


def input_int(
    prompt: str,
    min_val: int = None,
    max_val: int = None,
    default: int = None
) -> Optional[int]:
    """Robust integer input with validation."""
    result = input_float(prompt, min_val, max_val, default)
    if result is not None:
        return int(result)
    return None


def input_choice(prompt: str, choices: List[str], default: int = 0) -> Optional[int]:
    """
    Simple choice input without arrow keys.
    Returns index of selected choice or None on cancel.
    """
    reset_terminal()

    print(f"\n  {Color.BOLD}{prompt}{Color.RESET}\n")

    for i, choice in enumerate(choices):
        marker = f"{Color.CYAN}{Icon.POINTER}" if i == default else " "
        print(f"  {marker} {Color.RESET}{i + 1}. {choice}")

    print()

    while True:
        try:
            raw = input(f"  {Color.DIM}Enter 1-{len(choices)}:{Color.RESET} ").strip()

            if not raw:
                return default

            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return idx

            print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
            print(f"  {Color.RED}{Icon.CROSS} Choose 1-{len(choices)}{Color.RESET}")
            time.sleep(0.5)
            print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")

        except ValueError:
            print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
            print(f"  {Color.RED}{Icon.CROSS} Enter a number{Color.RESET}")
            time.sleep(0.5)
            print(f"{Cursor.UP}{Cursor.CLEAR_LINE}", end="")
        except KeyboardInterrupt:
            print()
            return None


# =============================================================================
# Progress Bar with Animation
# =============================================================================

class ProgressBar:
    """Animated progress bar for multi-step operations."""

    def __init__(self, total: int, width: int = 25, label: str = ""):
        self.total = total
        self.width = width
        self.label = label
        self.current = 0

    def update(self, current: int = None, label: str = None):
        """Update progress bar."""
        if current is not None:
            self.current = current
        else:
            self.current += 1

        if label is not None:
            self.label = label

        filled = int(self.width * self.current / self.total)
        empty = self.width - filled

        bar = f"{Color.GREEN}{'█' * filled}{Color.GRAY}{'░' * empty}{Color.RESET}"
        percent = int(100 * self.current / self.total)

        print(f"\r  {bar} {percent:3d}% {Color.DIM}{self.label}{Color.RESET}  ", end="", flush=True)

    def complete(self, message: str = "Done"):
        """Complete the progress bar."""
        bar = f"{Color.GREEN}{'█' * self.width}{Color.RESET}"
        print(f"\r  {bar} 100% {Color.GREEN}{Icon.CHECK} {message}{Color.RESET}  ")


class LiveProgress:
    """
    Animated progress with spinner and message.
    Shows: [■■■■□□□□□□] 40% AI analyzing hot numbers...
    """

    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str, steps: int = 10, width: int = 20):
        self.message = message
        self.steps = steps
        self.width = width
        self.current = 0
        self._running = False
        self._thread = None
        self._spinner_idx = 0

    def _render(self):
        """Render current state."""
        filled = int(self.width * self.current / self.steps)
        empty = self.width - filled
        bar = f"{Color.GREEN}{'■' * filled}{Color.GRAY}{'□' * empty}{Color.RESET}"
        percent = int(100 * self.current / self.steps)
        spinner = self.SPINNER[self._spinner_idx % len(self.SPINNER)]

        print(f"\r  {bar} {percent:3d}% {Color.CYAN}{spinner}{Color.RESET} {self.message}", end="", flush=True)

    def _animate(self):
        """Background animation loop."""
        while self._running:
            self._spinner_idx += 1
            self._render()
            time.sleep(0.08)

    def start(self):
        """Start the animated progress."""
        self._running = True
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def update(self, step: int = None, message: str = None):
        """Update progress step and/or message."""
        if step is not None:
            self.current = min(step, self.steps)
        if message is not None:
            self.message = message

    def complete(self, message: str = "Complete"):
        """Complete the progress."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.2)

        bar = f"{Color.GREEN}{'■' * self.width}{Color.RESET}"
        print(f"\r{Cursor.CLEAR_LINE}  {bar} 100% {Color.GREEN}{Icon.CHECK}{Color.RESET} {message}")

    def fail(self, message: str = "Failed"):
        """Mark as failed."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.2)

        filled = int(self.width * self.current / self.steps)
        empty = self.width - filled
        bar = f"{Color.RED}{'■' * filled}{Color.GRAY}{'□' * empty}{Color.RESET}"
        percent = int(100 * self.current / self.steps)
        print(f"\r{Cursor.CLEAR_LINE}  {bar} {percent:3d}% {Color.RED}{Icon.CROSS}{Color.RESET} {message}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, *args):
        if exc_type:
            self.fail()
        elif self._running:
            self.complete()


# =============================================================================
# Post-Action Menu
# =============================================================================

def post_action_menu() -> str:
    """
    Show post-action options: [M] Menu  [Q] Quit
    Returns 'menu', 'quit', or 'continue' on Enter
    """
    reset_terminal()

    print()
    print(f"  {Color.DIM}─────────────────────────────────────────{Color.RESET}")
    print(f"  {Color.CYAN}[M]{Color.RESET} Menu  {Color.CYAN}[Q]{Color.RESET} Quit  {Color.DIM}[Enter] Continue{Color.RESET}")

    try:
        raw = input(f"  {Color.DIM}>{Color.RESET} ").strip().lower()

        if raw == 'm':
            return 'menu'
        elif raw == 'q':
            return 'quit'
        else:
            return 'continue'
    except KeyboardInterrupt:
        return 'quit'
    except:
        return 'menu'


def action_prompt(actions: List[tuple]) -> Optional[str]:
    """
    Show action prompt at bottom.
    actions: List of (key, label) tuples, e.g. [('m', 'Menu'), ('q', 'Quit')]
    Returns the key pressed or None on cancel.
    """
    reset_terminal()

    print()
    separator()

    prompt_parts = []
    for key, label in actions:
        prompt_parts.append(f"{Color.CYAN}[{key.upper()}]{Color.RESET} {label}")

    print(f"  {' │ '.join(prompt_parts)}")

    try:
        raw = input(f"  {Color.DIM}>{Color.RESET} ").strip().lower()

        for key, _ in actions:
            if raw == key.lower():
                return key

        # Default to first action if just Enter
        if not raw and actions:
            return actions[0][0]

        return None
    except KeyboardInterrupt:
        return None


# Initialize terminal on import
setup_terminal()
