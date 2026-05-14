from __future__ import annotations

import random
import time

from pyfiglet import Figlet
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from ask.config import Settings
from ask.ui import theme as T


def _glitch_block(width: int = 52, rows: int = 7) -> Text:
    chars = "01█▓▒░·∴∵▸◂╱╲"
    lines: list[str] = []
    for _ in range(rows):
        lines.append("".join(random.choice(chars) for _ in range(width)))
    return Text("\n".join(lines), style=T.MATRIX_DIM)


def _typewriter_log(live: Live, lines: list[str], char_delay: float) -> None:
    done: list[str] = []
    for line in lines:
        current = ""
        for ch in line:
            current += ch
            body = "\n".join(done + [current])
            live.update(
                Panel(
                    Text(body, style=T.CYAN),
                    title=f"[{T.TITLE}]▶ SYSTEM LOG[/]",
                    border_style=T.BORDER,
                    subtitle=f"[{T.DIM}]encrypted local session[/]",
                    padding=(0, 1),
                )
            )
            time.sleep(char_delay)
        done.append(line)


def play_startup_animation(console: Console, settings: Settings) -> None:
    """Animated boot: glitch matrix → typed boot log → title pulse → static banner panel."""
    title = settings.ui_banner_title
    subtitle = settings.ui_banner_subtitle or "OFFLINE NEURAL INTERFACE"
    font = settings.ui_banner_font

    t0 = time.monotonic()
    with Live(
        Panel(Text("…", style=T.DIM), border_style=T.BORDER, title=f"[{T.TITLE}]BOOT[/]"),
        console=console,
        refresh_per_second=30,
        transient=True,
    ) as live:
        while time.monotonic() - t0 < 0.55:
            live.update(
                Panel(
                    _glitch_block(),
                    title=f"[{T.TITLE}]◆ MEMCORE SCRAMBLE[/]",
                    border_style=T.MAGENTA,
                    padding=(0, 1),
                )
            )
            time.sleep(0.055)

        mem = "PERSISTENT SQLITE" if settings.memory_persist_path else "VOLATILE RAM"
        _typewriter_log(
            live,
            [
                "> handshake: OLLAMA uplink reserved",
                f"> memory substrate: {mem}",
                "> channel: SECURE / LOCAL-ONLY",
            ],
            char_delay=0.016,
        )
        time.sleep(0.1)

        try:
            ascii_art = Figlet(font=font).renderText(title)
        except Exception:
            ascii_art = title + "\n"

        for glow in (T.CYAN, T.MAGENTA, T.YELLOW):
            live.update(
                Panel(
                    Text(ascii_art, style=f"bold {T.MAGENTA}"),
                    title=f"[{T.TITLE}]◆ NEURAL ARRAY ONLINE[/]",
                    border_style=glow,
                    subtitle=f"[bold {glow}]{subtitle}[/]",
                    padding=(0, 2),
                )
            )
            time.sleep(0.18)

    try:
        ascii_final = Figlet(font=font).renderText(title)
    except Exception:
        ascii_final = title + "\n"
    console.print(
        Panel(
            Text(ascii_final, style=f"bold {T.MAGENTA}"),
            title=f"[{T.TITLE}]◆ ASK AI — NEURAL SHELL[/]",
            border_style=T.CYAN,
            subtitle=f"[bold {T.CYAN}]{subtitle}[/]",
            padding=(0, 2),
        )
    )
