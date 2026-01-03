#!/usr/bin/env python3
"""
National Lottery Logo - Half-Block Rendering
Uses Unicode ▀ (upper half block) with foreground/background colors
to achieve proper 2:1 aspect ratio correction.
"""

# Logo pixel data: Y=Yellow, K=Black, M=Magenta, G=Green, C=Cyan, .=Transparent
logo_data = [
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

# ANSI TrueColor values
COLORS = {
    'Y': (255, 221, 0),    # Yellow
    'K': (0, 0, 0),        # Black
    'M': (228, 0, 43),     # Magenta/Red
    'G': (0, 148, 68),     # Green
    'C': (0, 159, 227),    # Cyan
    '.': None,             # Transparent
}

def fg(r, g, b):
    """Set foreground color."""
    return f"\x1b[38;2;{r};{g};{b}m"

def bg(r, g, b):
    """Set background color."""
    return f"\x1b[48;2;{r};{g};{b}m"

R = "\x1b[0m"  # Reset


def render_logo_lines():
    """
    Render logo using half-block technique.
    Process two rows at a time: top row = foreground, bottom row = background.
    Returns 5 lines (from 10 rows of data).
    """
    lines = []

    for i in range(0, len(logo_data), 2):
        top_row = logo_data[i]
        bottom_row = logo_data[i + 1]
        line = ""

        for j in range(len(top_row)):
            top_color = COLORS.get(top_row[j])
            bottom_color = COLORS.get(bottom_row[j])

            if top_color is None and bottom_color is None:
                # Both transparent - just a space
                line += " "
            elif top_color is not None and bottom_color is None:
                # Top has color, bottom transparent - upper half block
                line += fg(*top_color) + "▀" + R
            elif top_color is None and bottom_color is not None:
                # Top transparent, bottom has color - lower half block
                line += fg(*bottom_color) + "▄" + R
            else:
                # Both have colors - upper half with fg=top, bg=bottom
                line += fg(*top_color) + bg(*bottom_color) + "▀" + R

        lines.append(line)

    return lines


def get_banner_lines():
    """
    Generate complete banner with text on left, logo on right.
    Returns list of strings ready to print.
    """
    logo = render_logo_lines()

    # Text colors
    W = "\x1b[1;97m"  # Bold bright white
    C = fg(0, 159, 227)   # Cyan
    G = fg(0, 148, 68)    # Green
    M = fg(228, 0, 43)    # Magenta/Red

    # Text lines with their visible character counts
    # Format: (ansi_string, visible_length)
    text = [
        ("", 0),                                    # Line 0: empty
        (f"{W}PHANDA{R}", 6),                       # Line 1
        (f"{W}PUSHA{R}  {C}●{R}", 8),               # Line 2
        (f"{W}PLAY{R}   {G}●{R} {M}●{R}", 10),      # Line 3
        ("", 0),                                    # Line 4: empty
    ]

    max_text_width = 10
    spacing = "    "  # 4 spaces between text and logo

    output = []
    for i in range(5):
        txt, vis_len = text[i]
        padding = " " * (max_text_width - vis_len)
        output.append(f"  {txt}{padding}{spacing}{logo[i]}")

    return output


def print_banner():
    """Print the complete banner."""
    import sys
    import io
    # Handle Windows encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    for line in get_banner_lines():
        print(line)


if __name__ == "__main__":
    print_banner()
