"""Illustrative KL East booking-fee economics, independent of portfolio licensing."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

OUT = Path(__file__).resolve().parents[1] / "site-vnext" / "assets"
WEEKDAY_FEE = 4
PEAK_FEE = 5
PEAK_DAYS = 104
WEEKDAY_DAYS = 261
OPERATOR_SHARE = 0.20
PROCESSING_SHARE = 0.02  # Allowance applied to gross booking fees.
ANNUAL_RUNNING = 10_500
UPFRONT = 103_140


def economics(peak_per_day=30, weekday_per_day=7.5):
    gross = PEAK_DAYS * peak_per_day * PEAK_FEE + WEEKDAY_DAYS * weekday_per_day * WEEKDAY_FEE
    operator = gross * OPERATOR_SHARE
    processing = gross * PROCESSING_SHARE
    net = gross - operator - processing
    contribution = net - ANNUAL_RUNNING
    return dict(gross=gross, operator=operator, processing=processing, net=net,
                contribution=contribution,
                payback=UPFRONT / contribution if contribution > 0 else None)


def draw():
    r = economics()
    values = [r["gross"], -r["operator"], -r["processing"], -ANNUAL_RUNNING, r["contribution"]]
    labels = ["Member\nbooking fees", "Operator\n20% share", "Processing\n2% allowance", "Zone\nrunning costs", "Operating\ncontribution"]
    colors = ["#2f6fe0", "#9aa6b6", "#9aa6b6", "#9aa6b6", "#168a64"]
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=220, facecolor="white")
    ax.set_facecolor("white")
    running = 0
    for i, (value, color) in enumerate(zip(values, colors)):
        bottom = 0 if i in (0, 4) else running + value
        height = abs(value)
        ax.bar(i, height / 1000, bottom=bottom / 1000, width=.63, color=color, zorder=3)
        top = (bottom + height) / 1000
        if i in (0, 4):
            text = f"RM{value / 1000:.1f}k"
        else:
            text = f"−RM{abs(value):,.0f}"
        ax.text(i, top + .7, text, ha="center", va="bottom", fontsize=14,
                color="#111827", fontweight="bold")
        running = value if i in (0, 4) else running + value
        if i < 3:
            ax.plot([i + .32, i + .68], [running / 1000] * 2, color="#b7c0cb", lw=1)
    ax.set_xticks(range(5), labels, fontsize=12, color="#344054")
    ax.set_ylim(0, 28)
    ax.set_yticks([0, 5, 10, 15, 20, 25])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}k"))
    ax.set_ylabel("Annual cash (RM)", fontsize=14, color="#344054", labelpad=10)
    ax.tick_params(axis="y", labelsize=13, length=0, colors="#475467")
    ax.tick_params(axis="x", length=0, pad=12)
    ax.grid(axis="y", color="#e6e9ef", linewidth=.8, zorder=0)
    for side in ["left", "right", "top"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c6cfdb")
    fig.tight_layout(pad=1.5)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "booking_cash_bridge.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return r


def draw_recovery_gap():
    """Compare booking-only contribution with illustrative capital-recovery hurdles."""
    r = economics()
    targets = [UPFRONT / 5, UPFRONT / 3]
    base = r["contribution"]
    fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=220, facecolor="white")
    labels = ["5-year recovery", "3-year recovery"]
    for i, target in enumerate(targets):
        ax.barh(i, base / 1000, height=.5, color="#2f6fe0", label="Booking contribution" if i == 0 else None)
        ax.barh(i, (target - base) / 1000, left=base / 1000, height=.5, color="#e5eaf1",
                label="Additional net benefit needed" if i == 0 else None)
        ax.text(base / 2000, i, f"RM{base / 1000:.1f}k", ha="center", va="center", color="white", fontsize=14, fontweight="bold")
        ax.text((base + (target - base) / 2) / 1000, i, f"+RM{(target - base) / 1000:.1f}k",
                ha="center", va="center", color="#18212b", fontsize=15, fontweight="bold")
        ax.text(target / 1000, i - .36, f"RM{target / 1000:.1f}k / year required",
                ha="right", va="center", color="#344054", fontsize=14)
    ax.set_yticks([0, 1], labels, fontsize=15, color="#18212b")
    ax.set_ylim(1.55, -.65)
    ax.set_xlim(0, 38)
    ax.set_xlabel("Annual operating contribution (RM thousands)", fontsize=14, labelpad=12, color="#344054")
    ax.tick_params(axis="both", length=0, labelsize=13)
    ax.grid(axis="x", color="#e6e9ef", linewidth=.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c6cfdb")
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.01), ncol=1, frameon=False, fontsize=13)
    fig.tight_layout(pad=1.5)
    fig.savefig(OUT / "capital_recovery_gap.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Additional annual contribution for 5-year recovery:", round(targets[0] - base, 2))
    print("Additional annual contribution for 3-year recovery:", round(targets[1] - base, 2))


if __name__ == "__main__":
    result = draw()
    draw_recovery_gap()
    for name, value in result.items():
        print(f"{name}: {value:,.2f}")
    assert round(result["gross"], 2) == 23430
    assert round(result["net"], 2) == 18275.40
    assert round(result["contribution"], 2) == 7775.40
