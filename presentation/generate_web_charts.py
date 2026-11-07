from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site-vnext" / "assets"

BG = "#111b2a"
INK = "#ebf0f6"
MUTED = "#aebbd0"
GRID = "#2f4360"
BLUE = "#7ea8ff"
GREEN = "#34e58a"
AMBER = "#ffb21f"


def base_axes(figsize=(9.4, 5.3)):
    fig, ax = plt.subplots(figsize=figsize, dpi=200, facecolor=BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=14, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8, alpha=0.72)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    return fig, ax


def forecast_error():
    x = np.array([30, 60, 90])
    series = [
        ("Assume no change", [3.7, 7.0, 10.1], "#73839a", "--", 1.8),
        ("Same time last week", [5.26, 5.34, 5.40], MUTED, "-", 1.8),
        ("ParkFlow forecast", [1.41, 2.07, 2.63], BLUE, "-", 3.2),
    ]
    fig, ax = base_axes()
    for label, values, color, style, width in series:
        ax.plot(x, values, style, color=color, linewidth=width, marker="o", markersize=6, label=label)
        ax.text(92, values[-1], f"{values[-1]:.1f}%", color=color, va="center", fontsize=14, fontweight="bold")
    ax.set_xlim(26, 100)
    ax.set_ylim(0, 11)
    ax.set_xticks(x, ["30 min", "60 min", "90 min"])
    ax.set_yticks(range(0, 11, 2), [f"{v}%" for v in range(0, 11, 2)])
    ax.set_xlabel("Forecast horizon", color=MUTED, labelpad=13, fontsize=14)
    ax.set_ylabel("Mean absolute error (% of capacity)", color=MUTED, labelpad=14, fontsize=14)
    ax.legend(loc="upper left", frameon=False, labelcolor=INK, fontsize=12, ncol=1)
    ax.annotate(
        "61% lower error\nat 60 minutes",
        xy=(60, 2.07),
        xytext=(69, 3.25),
        color=GREEN,
        fontsize=14,
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": GREEN, "lw": 1.4},
    )
    fig.tight_layout(pad=1.4)
    fig.savefig(OUT / "forecast_error.png", facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def guarantee_vs_waste():
    points = [
        ("No booking", 0, 85.5, "#73839a"),
        ("Simple count", 12, 100, MUTED),
        ("VIP area", 19, 99.94, AMBER),
        ("Count + buffer", 23, 100, MUTED),
        ("ParkFlow", 5, 100, GREEN),
    ]
    fig, ax = base_axes()
    ax.axvspan(0, 8, ymin=0.78, ymax=1, color=GREEN, alpha=0.08)
    offsets = {
        "No booking": (0.8, 0.7),
        "Simple count": (-1.2, -2.0),
        "VIP area": (-0.7, 1.0),
        "Count + buffer": (-5.2, -3.0),
        "ParkFlow": (0.8, 0.8),
    }
    for label, x, y, color in points:
        size = 170 if label == "ParkFlow" else 85
        ax.scatter(x, y, s=size, color=color, edgecolor=BG, linewidth=1.6, zorder=3)
        dx, dy = offsets[label]
        ax.text(x + dx, y + dy, label, color=color if label in ("ParkFlow", "VIP area") else INK, fontsize=13, fontweight="bold" if label == "ParkFlow" else "normal")
    ax.set_xlim(-1, 26)
    ax.set_ylim(83, 102)
    ax.set_xticks([0, 5, 10, 15, 20, 25])
    ax.set_yticks([85, 90, 95, 100], ["85%", "90%", "95%", "100%"])
    ax.set_xlabel("Empty, blocked bay-hours per busy Saturday", color=MUTED, labelpad=13, fontsize=14)
    ax.set_ylabel("Booking reliability / walk-in success", color=MUTED, labelpad=14, fontsize=14)
    ax.annotate(
        "14 fewer blocked bay-hours\nthan the fixed VIP area",
        xy=(5, 100),
        xytext=(7.3, 94.0),
        color=GREEN,
        fontsize=14,
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": GREEN, "lw": 1.3},
    )
    fig.tight_layout(pad=1.4)
    fig.savefig(OUT / "guarantee_waste.png", facecolor=BG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    forecast_error()
    guarantee_vs_waste()
    print("wrote", OUT / "forecast_error.png")
    print("wrote", OUT / "guarantee_waste.png")
