"""Export the forecast pipeline and proposed operational learning loop."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.path import Path as MplPath

OUT = Path(__file__).resolve().parents[1] / "site-vnext" / "assets"
BG, PANEL = "#0a111c", "#111b2a"
INK, MUTED = "#ebf0f6", "#b8c5d6"
BLUE, GREEN, AMBER = "#7ea8ff", "#34e58a", "#ffb21f"


def draw():
    plt.rcParams["svg.fonttype"] = "path"
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(15.5, 5.7), dpi=180, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 15.5)
    ax.set_ylim(0, 5.7)
    ax.axis("off")

    def node(x, y, w, h, title, body, accent=BLUE, title_size=17,
             body_size=14, dashed=False):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.09",
            facecolor=PANEL, edgecolor=accent, linewidth=1.4,
            linestyle=(0, (5, 4)) if dashed else "solid", zorder=3))
        ax.text(x + w / 2, y + h - .24, title, ha="center", va="top",
                color=accent if dashed else INK, fontsize=title_size,
                fontweight="bold", linespacing=1.12, zorder=4)
        ax.text(x + w / 2, y + .20, body, ha="center", va="bottom",
                color=MUTED, fontsize=body_size, linespacing=1.4, zorder=4)

    def wire(points, color=BLUE, dashed=False):
        codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1)
        ax.add_patch(FancyArrowPatch(
            path=MplPath(points, codes), arrowstyle="-|>", mutation_scale=15,
            linewidth=1.6, color=color,
            linestyle=(0, (4, 4)) if dashed else "solid", zorder=2))

    node(.08, 2.35, 2.45, 2.4, "Input signals",
         "Occupancy history\nTime + weekday\nWeather + events\nCinema schedules")
    node(3.20, 3.80, 2.55, 1.3, "Weekly pattern", "Adjusted to today")
    node(3.20, 2.00, 2.55, 1.3, "LightGBM", "Learned patterns")
    node(6.50, 2.70, 2.4, 1.7, "Blend + range",
         "Weighted blend\nConformal prediction", title_size=16)
    node(9.60, 2.50, 2.8, 2.1, "30 / 60 / 90 min",
         "Expected occupancy\n+ 80% range", accent=GREEN)
    node(13.10, 2.50, 2.3, 2.1, "Actual\noccupancy",
         "Measured on site", title_size=16, body_size=13)
    node(6.20, .25, 6.1, 1.25, "Check errors · retrain · validate",
         "Deploy an update only if validation passes",
         accent=GREEN, title_size=17, body_size=14)

    wire([(2.56, 3.55), (2.90, 3.55), (2.90, 4.45), (3.17, 4.45)])
    wire([(2.56, 3.55), (2.90, 3.55), (2.90, 2.65), (3.17, 2.65)])
    wire([(5.78, 4.45), (6.12, 4.45), (6.12, 3.55), (6.47, 3.55)])
    wire([(5.78, 2.65), (6.12, 2.65), (6.12, 3.55), (6.47, 3.55)])
    wire([(8.93, 3.55), (9.57, 3.55)], GREEN)
    wire([(12.43, 3.55), (13.07, 3.55)], MUTED, dashed=True)
    ax.text(12.75, 3.84, "later", ha="center", va="bottom",
            color=MUTED, fontsize=12)

    # Extra signals and the operational deployment loop are proposed pilot work.
    wire([(14.25, 2.47), (14.25, .88), (12.33, .88)], GREEN)
    wire([(6.80, 1.53), (6.80, 1.72), (2.90, 1.72), (2.90, 3.45)], GREEN)
    ax.text(4.45, 1.35, "Validated update", ha="center", va="center",
            color=GREEN, fontsize=13)
    ax.text(4.48, 5.48, "Two models", ha="center", va="center",
            color=BLUE, fontsize=16)

    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.01)
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ["svg", "png"]:
        fig.savefig(OUT / f"ml_forecasting_pipeline.{suffix}", facecolor=BG,
                    bbox_inches="tight", pad_inches=.03)
    plt.close(fig)


if __name__ == "__main__":
    draw()
    print("Exported forecast pipeline and learning loop as SVG and PNG")
