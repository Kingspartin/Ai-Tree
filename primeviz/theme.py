"""Shared visual language for every representation.

Palette slots come from a validated categorical set (blue / orange / aqua on a
dark surface): all-pairs CVD separation ΔE 9.4, normal-vision ΔE 20.9, every
slot >= 3:1 against the surface. Real and null panels are never overlaid, so
identity is also carried by the panel title, not by hue alone.

Colour jobs used here:
  * identity  -> SET_COLORS (which integer set a panel shows)
  * magnitude -> SEQ_CMAP, one hue light->dark, for raw density
  * polarity  -> DIV_CMAP, blue<->red with a neutral grey midpoint, used only
                 for observed/expected ratios where 1.0 is the "nothing here"
                 midpoint.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

SURFACE = "#1a1a19"
SURFACE_2 = "#232322"
INK = "#ffffff"
INK_2 = "#c3c2b7"
INK_MUTED = "#8a8a80"
GRID = "#383835"

# categorical slots 1-3, dark steps
BLUE = "#3987e5"
ORANGE = "#d95926"
AQUA = "#199e70"
RED = "#e66767"
VIOLET = "#9085e9"

SET_COLORS = {"primes": BLUE, "cramer": ORANGE, "sieved": AQUA, "rough": VIOLET}

VERDICT_COLORS = {
    "SURVIVES": "#199e70",
    "DEEP-COPRIMALITY": "#c98500",
    "COPRIMALITY": "#c98500",
    "ARTIFACT": "#e66767",
    "INCONCLUSIVE": INK_MUTED,
}

# one-hue sequential ramp (blue 100 -> 700)
SEQ_CMAP = LinearSegmentedColormap.from_list(
    "seq_blue",
    ["#12161c", "#184f95", "#256abf", "#3987e5", "#86b6ef", "#cde2fb"],
)
# diverging: blue <-> red with a neutral grey midpoint
DIV_CMAP = LinearSegmentedColormap.from_list(
    "div_blue_red",
    ["#0d366b", "#256abf", "#3987e5", GRID, "#e66767", "#c0342f", "#7d1f1c"],
)


def ratio_norm(vmax: float = 2.0):
    """Norm for observed/expected maps: 1.0 always sits on the grey midpoint."""
    return TwoSlopeNorm(vmin=0.0, vcenter=1.0, vmax=vmax)


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.linewidth": 0.8,
            "axes.grid": False,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "text.color": INK,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.frameon": False,
            "legend.labelcolor": INK_2,
            "legend.fontsize": 8,
            "lines.linewidth": 2.0,
            "lines.markersize": 8,
            "font.family": "DejaVu Sans",
            "figure.dpi": 110,
        }
    )


def bare(ax) -> None:
    """Strip an axes down to the image it holds."""
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def recessive(ax) -> None:
    """Keep axes present but quiet."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.35, linewidth=0.6)
    ax.set_axisbelow(True)
