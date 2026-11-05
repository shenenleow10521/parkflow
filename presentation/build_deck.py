from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
import plotly.graph_objects as go
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT_DIR = ROOT / "submission"
GEN_DIR = ROOT / "presentation" / "generated"
OUT_PPTX = OUT_DIR / "ParkFlow-Priority-Zone-Business-Case-vNext.pptx"

ASSET_DIR = WORKSPACE / "deck" / "assets"
LOGO = ASSET_DIR / "logo-sdp.png"
BG_TITLE = ASSET_DIR / "bg-title.jpg"
BG_CONTENT = ASSET_DIR / "bg-content.jpg"
SITE_REF = ROOT / "references" / "parkflow-site-v2"
SHOT_HOME = SITE_REF / "assets" / "app-home.webp"
SHOT_GUIDANCE = SITE_REF / "assets" / "app-guidance.webp"
SHOT_OPERATOR = SITE_REF / "assets" / "op-overview.webp"

W, H = 13.333, 7.5
M = 0.62

NAVY = "0A111C"
NAVY_2 = "111B2A"
INK = "18212B"
SLATE = "5F6B76"
MUTED = "8696AD"
LINE = "D9DEE3"
PAPER = "F7F7F4"
WHITE = "FFFFFF"
GOLD = "E3C35A"
GOLD_2 = "F3D879"
RED = "FF5A66"
GREEN = "34E58A"
BLUE = "2F6FE0"
PALE_GOLD = "FFF7D9"
PALE_BLUE = "EEF4FF"
PALE_GREEN = "EAF7F2"
PALE_RED = "FDEEEF"


def rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color)


def make_charts() -> dict[str, Path]:
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 16,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )

    spend = GEN_DIR / "member_spend.png"
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=220)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    labels = ["Occasional\n1–2 visits / month", "Frequent\n5+ visits / month"]
    vals = [195, 327]
    bars = ax.bar(labels, vals, color=["#C7CDD3", "#F0B400"], width=0.58)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 9, f"RM{v}", ha="center", va="bottom", fontsize=15, fontweight="bold", color="#18212B")
    ax.text(0.5, 260, "+68%", ha="center", va="center", fontsize=16, fontweight="bold", color="#168A64")
    ax.set_ylim(0, 380)
    ax.set_ylabel("Mean recalled spend per trip (RM)", color="#5F6B76")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#D9DEE3")
    ax.tick_params(axis="y", length=0, colors="#5F6B76")
    ax.grid(axis="y", color="#E6E9EC", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(spend, transparent=True, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)

    investment = GEN_DIR / "pilot_investment_waterfall.png"
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=["Hardware +\ninstall", "Production\nintegration", "Year 1\nrunning", "Planning\nenvelope"],
            y=[43.14, 60.0, 10.5, 0],
            text=["RM43.1k", "RM60.0k", "RM10.5k", "RM113.6k"],
            textposition="outside",
            textfont={"family": "Arial", "size": 18, "color": "#18212B"},
            connector={"line": {"color": "#AEB7BF", "width": 1.4}},
            increasing={"marker": {"color": "#2F6FE0"}},
            totals={"marker": {"color": "#0A111C"}},
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        showlegend=False,
        margin={"l": 64, "r": 24, "t": 42, "b": 54},
        width=1200,
        height=620,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial", "color": "#5F6B76", "size": 15},
        yaxis={
            "title": "RM thousands",
            "range": [0, 135],
            "gridcolor": "#E6E9EC",
            "zeroline": False,
            "showline": False,
            "ticksuffix": "k",
        },
        xaxis={"showline": False, "tickfont": {"size": 14, "color": "#18212B"}},
    )
    fig.write_image(investment, scale=2)

    heat = GEN_DIR / "retention_sensitivity.png"
    baskets = [195, 260, 327]
    captures = [0.03, 0.05, 0.08]
    target = 9360
    data = np.array([[target / (b * c) / 52 for b in baskets] for c in captures])
    cmap = LinearSegmentedColormap.from_list("pf", ["#EAF7F2", "#FFF7D9", "#FDEEEF"])
    fig, ax = plt.subplots(figsize=(7.4, 3.8), dpi=220)
    im = ax.imshow(data, cmap=cmap, vmin=6, vmax=32, aspect="auto")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.1f}\nvisits / week", ha="center", va="center", fontsize=12, fontweight="bold", color="#18212B")
    ax.set_xticks(range(len(baskets)), [f"RM{b}" for b in baskets])
    ax.set_yticks(range(len(captures)), [f"{int(c*100)}%" for c in captures])
    ax.set_xlabel("Tenant sales per genuinely incremental visit", labelpad=9, color="#5F6B76")
    ax.set_ylabel("Illustrative effective GTO capture", labelpad=9, color="#5F6B76")
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.tight_layout()
    fig.savefig(heat, transparent=True, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)

    horizons = GEN_DIR / "three_horizons.png"
    fig, ax = plt.subplots(figsize=(10.8, 3.4), dpi=220)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    x = np.linspace(0, 48, 500)
    curves = [
        (0, 12, 0.25, 1.35, "#2D6CDF"),
        (7, 30, 0.52, 1.62, "#F0B400"),
        (20, 48, 0.82, 1.92, "#168A64"),
    ]
    for start, end, base, top, color in curves:
        y = np.full_like(x, np.nan)
        mask = (x >= start) & (x <= end)
        xm = (x[mask] - start) / (end - start)
        y[mask] = base + (top - base) * (1 - np.exp(-4.5 * xm)) / (1 - np.exp(-4.5))
        ax.plot(x, y, color=color, linewidth=4.2, solid_capstyle="round")
        ax.fill_between(x, base - 0.12, y, where=mask, color=color, alpha=0.09)
    ax.text(2, 0.57, "H1  LIGHTHOUSE", color="#2D6CDF", fontsize=12, fontweight="bold")
    ax.text(10, 1.18, "H2  PORTFOLIO", color="#9A7100", fontsize=12, fontweight="bold")
    ax.text(26, 1.63, "H3  PLATFORM OPTION", color="#168A64", fontsize=12, fontweight="bold")
    for month in [6, 18, 36]:
        ax.axvline(month, color="#BFC6CC", linewidth=1.0, linestyle=(0, (3, 4)))
    ax.set_xlim(0, 48)
    ax.set_ylim(0, 2.15)
    ax.set_xticks([0, 6, 12, 18, 24, 36, 48], ["Now", "6m", "12m", "18m", "24m", "36m", "48m"])
    ax.set_yticks([])
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#AEB6BD")
    ax.tick_params(axis="x", length=0, pad=8, colors="#5F6B76")
    fig.tight_layout()
    fig.savefig(horizons, transparent=True, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)

    return {"spend": spend, "investment": investment, "heat": heat, "horizons": horizons}


def add_text(slide, text, x, y, w, h, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT,
             valign=MSO_ANCHOR.TOP, font="Arial", margin=0.0, italic=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = rgb(color)
    return box


def add_rich_text(slide, runs, x, y, w, h, size=16, color=INK, valign=MSO_ANCHOR.TOP, margin=0.0):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    for item in runs:
        r = p.add_run()
        r.text = item[0]
        r.font.name = "Arial"
        r.font.size = Pt(item[2] if len(item) > 2 else size)
        r.font.bold = item[1]
        r.font.color.rgb = rgb(item[3] if len(item) > 3 else color)
    return box


def add_rect(slide, x, y, w, h, fill=WHITE, line=LINE, radius=False, transparency=0):
    typ = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shape = slide.shapes.add_shape(typ, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.fill.transparency = transparency
    shape.line.color.rgb = rgb(line)
    shape.line.width = Pt(0.8)
    return shape


def add_line(slide, x1, y1, x2, y2, color=LINE, width=1.0):
    line = slide.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    line.line.color.rgb = rgb(color)
    line.line.width = Pt(width)
    return line


def add_logo(slide, dark=False):
    if LOGO.exists():
        slide.shapes.add_picture(str(LOGO), Inches(12.03), Inches(0.22), height=Inches(0.48))


def add_header(slide, section, title, subtitle=None, dark=False):
    add_text(slide, section.upper(), M, 0.34, 7.5, 0.25, 9, GOLD if dark else SLATE, True)
    add_text(slide, title, M, 0.72, 11.8, 0.82, 25, WHITE if dark else INK, False)
    if subtitle:
        add_text(slide, subtitle, M, 1.48, 11.4, 0.42, 11.5, "C9D2DB" if dark else SLATE)
    add_logo(slide, dark)


def add_footer(slide, number, source=None, dark=False):
    if source:
        add_text(slide, source, M, 7.10, 11.6, 0.22, 7.2, "AEB8C2" if dark else MUTED)
    add_text(slide, str(number), 12.28, 7.05, 0.4, 0.22, 8, "AEB8C2" if dark else MUTED, align=PP_ALIGN.RIGHT)


def add_bullets(slide, items, x, y, w, h, size=13, color=INK, bullet_color=None, spacing=7):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.font.name = "Arial"
        p.font.size = Pt(size)
        p.font.color.rgb = rgb(color)
        p.level = 0
        p.text = "•  " + item
        p.space_after = Pt(spacing)
    return box


def add_metric(slide, x, y, w, h, value, label, accent=GOLD, dark=False, note=None):
    add_rect(slide, x, y, w, h, fill=NAVY_2 if dark else WHITE, line=NAVY_2 if dark else LINE, radius=True)
    add_rect(slide, x, y, 0.07, h, fill=accent, line=accent)
    add_text(slide, value, x + 0.24, y + 0.16, w - 0.38, 0.44, 23, WHITE if dark else INK, True)
    add_text(slide, label, x + 0.24, y + 0.68, w - 0.38, 0.46, 10.5, "C9D2DB" if dark else SLATE)
    if note:
        add_text(slide, note, x + 0.24, y + h - 0.33, w - 0.38, 0.18, 7.5, "9EABB7" if dark else MUTED)


def add_image_crop(slide, path, x, y, w, h):
    if path.exists():
        use_path = path
        if path.suffix.lower() == ".webp":
            use_path = GEN_DIR / f"{path.stem}.png"
            if not use_path.exists():
                with Image.open(path) as img:
                    img.convert("RGB").save(use_path, "PNG")
        slide.shapes.add_picture(str(use_path), Inches(x), Inches(y), width=Inches(w), height=Inches(h))


def build_deck():
    charts = make_charts()
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    # 1 — Title
    slide = prs.slides.add_slide(blank)
    if BG_TITLE.exists():
        slide.shapes.add_picture(str(BG_TITLE), 0, 0, width=Inches(W), height=Inches(H))
    overlay = add_rect(slide, 0, 0, W, H, fill=NAVY, line=NAVY, transparency=18)
    add_logo(slide, True)
    add_text(slide, "SIME DARBY PROPERTY  •  MEMBERS-FIRST PARKING", M, 0.95, 8.8, 0.3, 10, "D7DEE5", True)
    add_text(slide, "ParkFlow", M, 1.48, 7.2, 0.8, 38, WHITE, True)
    add_text(slide, "Guaranteed access for members.\nBetter decisions for every driver.", M, 2.38, 7.6, 1.25, 27, GOLD, False)
    add_text(slide, "A gated Priority Zone, deterministic booking control and whole-car-park forecasting—starting with a measured KL East Mall lighthouse.", M, 4.05, 7.2, 1.0, 15, WHITE)
    add_text(slide, "Business case vNext  •  5 November 2026", M, 6.72, 7.0, 0.26, 9, "C7D0D8")
    add_footer(slide, 1, dark=True)

    # 2 — Executive answer
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Executive answer", "Approve a KL East lighthouse—not a national rollout")
    add_text(slide, "ParkFlow should be judged first as an SDP member-experience and operating-data business case. External commercialisation is an option earned by proof, not assumed revenue.", M, 1.54, 11.7, 0.72, 16, INK, True)
    cols = [
        ("01", "Prove the core", "A gated Priority Zone uses observed entries, exits and protected reservations to accept or reject bookings deterministically."),
        ("02", "Measure value", "The pilot tests member adoption, fulfilment, repeat visits, utilization and operator decisions—without claiming unproven GTO uplift."),
        ("03", "Scale one adjacency", "Replicate only into SDP malls that pass a readiness screen; productise the playbook before considering external licensing."),
    ]
    for i, (n, t, b) in enumerate(cols):
        x = M + i * 4.08
        add_rect(slide, x, 2.55, 3.78, 2.55, fill=WHITE, line=LINE, radius=True)
        add_text(slide, n, x + 0.22, 2.77, 0.7, 0.35, 12, GOLD, True)
        add_text(slide, t, x + 0.22, 3.19, 3.25, 0.42, 18, INK, True)
        add_text(slide, b, x + 0.22, 3.78, 3.27, 0.98, 11.5, SLATE)
    add_rect(slide, M, 5.46, 12.08, 0.82, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "RECOMMENDATION", M + 0.25, 5.69, 1.25, 0.25, 9, GOLD, True)
    add_text(slide, "SDP first → evidence first → portfolio second → venture option third", M + 1.65, 5.60, 9.9, 0.4, 17, WHITE, True)
    add_footer(slide, 2, "GTM principle: customer-specific proof of value, repeatable expansion and explicit scale gates.")

    # 3 — Problem and customer
    slide = prs.slides.add_slide(blank)
    add_header(slide, "The business problem", "Parking certainty matters most when the visit matters most")
    add_text(slide, "KL East Mall has finite capacity; the commercial question is not whether ParkFlow creates bays, but whether it protects the experience of valuable repeat visitors while improving how the car park is operated.", M, 1.53, 11.7, 0.62, 14.5, INK)
    add_metric(slide, M, 2.42, 2.75, 1.45, "1,300", "parking bays at KL East Mall", BLUE)
    add_metric(slide, 3.58, 2.42, 2.75, 1.45, "200+", "retail outlets across four levels", GOLD)
    add_metric(slide, 6.54, 2.42, 2.75, 1.45, "RM327", "mean trip spend: frequent visitors", GREEN, note="Malaysia survey, n=500")
    add_metric(slide, 9.50, 2.42, 2.55, 1.45, "28%", "spent RM300+ on latest trip", RED, note="Malaysia survey, 2026")
    add_rect(slide, M, 4.27, 5.78, 1.65, fill=PALE_GOLD, line="F2D978", radius=True)
    add_text(slide, "Member need", M + 0.23, 4.52, 2.1, 0.3, 12, "8A6700", True)
    add_text(slide, "Know whether a guaranteed Priority Zone booking is available—and when to arrive if it is not.", M + 0.23, 4.93, 5.25, 0.72, 14, INK, True)
    add_rect(slide, 6.67, 4.27, 5.40, 1.65, fill=PALE_BLUE, line="C8D8F2", radius=True)
    add_text(slide, "Operator need", 6.90, 4.52, 2.1, 0.3, 12, BLUE, True)
    add_text(slide, "See demand, occupancy, turnover and exceptions early enough to direct traffic and deploy staff.", 6.90, 4.93, 4.85, 0.72, 14, INK, True)
    add_footer(slide, 3, "Sources: Sime Darby Property KL East Mall; Vase.ai Malaysia Shopping Mall Report 2026 (n=500, recalled behaviour).")

    # 4 — Two-layer product logic
    slide = prs.slides.add_slide(blank)
    add_header(slide, "How it works", "Separate the guarantee from the forecast")
    add_rect(slide, M, 1.65, 5.75, 4.62, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "LAYER 1  •  CONTROL", M + 0.28, 1.95, 2.6, 0.3, 10, GOLD, True)
    add_text(slide, "Deterministic booking", M + 0.28, 2.40, 4.9, 0.44, 22, WHITE, True)
    add_bullets(slide, [
        "Entry and exit LPR verify the gated Priority Zone boundary",
        "Observed occupancy + protected reservations determine available-to-promise",
        "If capacity is unavailable, the answer is a hard no or another time",
        "The forecast never gambles with an accepted member booking",
    ], M + 0.28, 3.08, 5.1, 1.75, 12, "D9E2EA", spacing=8)
    add_rect(slide, 6.48, 1.65, 5.60, 4.62, fill=WHITE, line=LINE, radius=True)
    add_text(slide, "LAYER 2  •  DECISION SUPPORT", 6.76, 1.95, 3.7, 0.3, 10, BLUE, True)
    add_text(slide, "Whole-car-park forecast", 6.76, 2.40, 4.9, 0.44, 22, INK, True)
    add_bullets(slide, [
        "Predicts likely availability by area and time—not only inside the Priority Zone",
        "Helps a member decide whether to book now, arrive later or use general parking",
        "Gives non-members broad level guidance to reduce circulation",
        "Gives the operator exact flows, confidence and exception alerts",
    ], 6.76, 3.08, 4.92, 1.75, 12, SLATE, spacing=8)
    add_rect(slide, 4.97, 5.58, 3.35, 0.52, fill=GOLD, line=GOLD, radius=True)
    add_text(slide, "GUARANTEE ≠ FORECAST", 5.11, 5.73, 3.07, 0.21, 10.5, NAVY, True, align=PP_ALIGN.CENTER)
    add_footer(slide, 4)

    # 5 — Member journey
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Member experience", "One decision, three useful outcomes")
    add_image_crop(slide, SHOT_HOME, M, 1.65, 3.15, 4.95)
    stages = [
        ("1", "Check", "The member sees Priority Zone status plus general-parking context."),
        ("2", "Decide", "Book a guaranteed window, choose a later slot, or use open parking."),
        ("3", "Verify", "The gated LPR boundary admits the registered plate and records exit."),
    ]
    for i, (n, t, b) in enumerate(stages):
        y = 1.78 + i * 1.45
        add_rect(slide, 4.23, y, 7.82, 1.10, fill=WHITE, line=LINE, radius=True)
        add_rect(slide, 4.48, y + 0.25, 0.60, 0.60, fill=GOLD if i == 1 else NAVY, line=GOLD if i == 1 else NAVY, radius=True)
        add_text(slide, n, 4.48, y + 0.35, 0.60, 0.25, 13, NAVY if i == 1 else WHITE, True, align=PP_ALIGN.CENTER)
        add_text(slide, t, 5.34, y + 0.20, 1.50, 0.34, 16, INK, True)
        add_text(slide, b, 5.34, y + 0.59, 6.23, 0.30, 11.5, SLATE)
    add_rect(slide, 4.23, 6.17, 7.82, 0.45, fill=PALE_GREEN, line="B7DDCF", radius=True)
    add_text(slide, "Member privilege = guaranteed booking access. Public benefit = clearer guidance and less circulation.", 4.42, 6.29, 7.46, 0.20, 10.5, GREEN, True)
    add_footer(slide, 5)

    # 6 — Information design
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Information architecture", "Show each audience only the precision they need")
    audience = [
        ("NON-MEMBER", "General guidance", ["Current level availability", "Broad congestion bands", "Where to go now"], MUTED, "F2F4F5"),
        ("MEMBER", "Actionable access", ["Priority Zone status", "Likely next opening", "Booking and alerts"], GOLD, PALE_GOLD),
        ("OPERATOR", "Operational truth", ["Exact counts and flows", "Forecast confidence", "Exceptions and interventions"], BLUE, PALE_BLUE),
    ]
    for i, (tag, title, bullets, accent, fill) in enumerate(audience):
        x = M + i * 4.08
        add_rect(slide, x, 1.78, 3.76, 4.35, fill=fill, line=LINE, radius=True)
        add_text(slide, tag, x + 0.24, 2.02, 2.6, 0.25, 9.5, accent, True)
        add_text(slide, title, x + 0.24, 2.50, 3.10, 0.44, 20, INK, True)
        for j, b in enumerate(bullets):
            add_line(slide, x + 0.24, 3.34 + j * 0.70, x + 0.56, 3.34 + j * 0.70, accent, 3)
            add_text(slide, b, x + 0.70, 3.20 + j * 0.70, 2.72, 0.34, 12, SLATE)
        privilege = ["No booking rights", "Guaranteed booking rights", "Control and audit rights"][i]
        add_rect(slide, x + 0.24, 5.45, 3.25, 0.43, fill=WHITE, line=LINE, radius=True)
        add_text(slide, privilege, x + 0.37, 5.57, 2.98, 0.19, 10, accent, True, align=PP_ALIGN.CENTER)
    add_footer(slide, 6)

    # 7 — Member evidence
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Commercial evidence", "The strongest signal is frequency—not a speculative parking fee")
    add_image_crop(slide, charts["spend"], M, 1.65, 6.25, 4.05)
    add_rect(slide, 7.18, 1.72, 4.88, 1.50, fill=PALE_GOLD, line="F2D978", radius=True)
    add_text(slide, "1 Utama ONECARD", 7.44, 1.98, 3.8, 0.28, 11, "8A6700", True)
    add_text(slide, "RM20,000 + 100 transactions", 7.44, 2.34, 4.10, 0.34, 19, INK, True)
    add_text(slide, "Silver qualification over 12 months; members-only preferred parking exists.", 7.44, 2.76, 4.10, 0.26, 9.5, SLATE)
    add_rect(slide, 7.18, 3.45, 4.88, 1.50, fill=PALE_BLUE, line="C8D8F2", radius=True)
    add_text(slide, "The Gardens Club", 7.44, 3.71, 3.8, 0.28, 11, BLUE, True)
    add_text(slide, "Loyalty + parking privileges", 7.44, 4.07, 4.10, 0.34, 19, INK, True)
    add_text(slide, "RM15,000 joining threshold; qualifying members receive spend-linked parking benefits.", 7.44, 4.49, 4.10, 0.26, 9.5, SLATE)
    add_rect(slide, 7.18, 5.18, 4.88, 0.74, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "What this proves", 7.42, 5.34, 1.35, 0.23, 9.0, GOLD, True)
    add_text(slide, "Valuable membership and parking privileges already coexist.", 8.78, 5.28, 3.03, 0.40, 9.3, WHITE, True)
    add_footer(slide, 7, "Sources: Vase.ai 2026 (n=500); official ONECARD FAQ and Silver T&C; official The Gardens Club programme.")

    # 8 — Investment case
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Business case", "Finance the proof; do not capitalise the hypothesis")
    add_text(slide, "The approval case is a bounded pilot investment with explicit evidence gates. Retention and GTO are measured upside—not guaranteed cash flow.", M, 1.48, 11.7, 0.46, 14, INK, True)
    add_image_crop(slide, charts["investment"], M, 2.08, 6.18, 3.26)
    add_text(slide, "Midpoint planning case; ranges remain RM30k–58k hardware and RM45k–100k integration.", M + 0.23, 5.17, 5.72, 0.32, 8.3, SLATE)
    add_rect(slide, 7.18, 2.20, 4.88, 3.02, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "ILLUSTRATIVE VALUE BRIDGE", 7.47, 2.49, 3.8, 0.24, 9.5, GOLD, True)
    add_text(slide, "RM327", 7.47, 3.00, 1.5, 0.45, 25, WHITE, True)
    add_text(slide, "tenant sales / genuinely incremental visit", 8.93, 3.06, 2.56, 0.34, 10, "CBD5DE")
    add_text(slide, "× 5%", 7.47, 3.66, 1.5, 0.38, 21, WHITE, True)
    add_text(slide, "assumed effective GTO capture", 8.93, 3.71, 2.56, 0.28, 10, "CBD5DE")
    add_line(slide, 7.47, 4.24, 11.48, 4.24, "526170", 1.1)
    add_text(slide, "RM16.35", 7.47, 4.43, 1.8, 0.40, 23, GOLD, True)
    add_text(slide, "potential GTO value per incremental visit", 9.18, 4.47, 2.35, 0.34, 10, "CBD5DE")
    add_rect(slide, M, 5.56, 11.42, 0.65, fill=PALE_RED, line="F2C2C5", radius=True)
    add_text(slide, "Not yet proven: reservation → incremental visit; KL East GTO share; member retention effect; final vendor cost.", M + 0.22, 5.76, 10.98, 0.22, 10.5, RED, True)
    add_footer(slide, 8)

    # 9 — Sensitivity
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Financial sensitivity", "Make the retention threshold transparent")
    add_image_crop(slide, charts["heat"], M, 1.48, 7.15, 4.35)
    add_rect(slide, 8.08, 1.70, 3.98, 3.62, fill=WHITE, line=LINE, radius=True)
    add_text(slide, "REFERENCE CASE", 8.36, 1.98, 2.6, 0.24, 9.5, BLUE, True)
    add_text(slide, "~11 visits / week", 8.36, 2.45, 3.2, 0.42, 23, INK, True)
    add_text(slide, "At RM327 sales and 5% illustrative capture, approximately 573 genuinely incremental visits per year correspond to RM9,360 potential GTO value.", 8.36, 3.06, 3.18, 1.02, 12, SLATE)
    add_text(slide, "This is a pilot hurdle—not a forecast.", 8.36, 4.55, 3.10, 0.30, 11, RED, True)
    add_rect(slide, M, 6.05, 11.42, 0.45, fill=PALE_GOLD, line="F2D978", radius=True)
    add_text(slide, "Decision rule: report measured incremental visits and observed tenant sales; do not multiply every booking by a basket value.", M + 0.22, 6.17, 10.98, 0.20, 10.5, "7A5B00", True)
    add_footer(slide, 9)

    # 10 — Operator value
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Operator proposition", "The data product is operational control, not another dashboard")
    add_image_crop(slide, SHOT_OPERATOR, 7.58, 1.63, 4.50, 4.70)
    values = [
        ("NOW", "Live truth", "Entries, exits, occupancy, bookings and exceptions by zone and level."),
        ("NEXT", "Forward warning", "Likely peaks, departures and confidence bands for staffing and signage."),
        ("LEARN", "Closed-loop improvement", "No-shows, dwell, interventions and fulfilment refine the operating rule."),
    ]
    for i, (tag, title, body) in enumerate(values):
        y = 1.78 + i * 1.39
        add_rect(slide, M, y, 6.40, 1.05, fill=WHITE, line=LINE, radius=True)
        add_text(slide, tag, M + 0.22, y + 0.18, 0.72, 0.22, 9.5, [BLUE, GOLD, GREEN][i], True)
        add_text(slide, title, M + 1.05, y + 0.14, 1.65, 0.30, 15, INK, True)
        add_text(slide, body, M + 2.72, y + 0.14, 3.38, 0.55, 10.5, SLATE)
    add_rect(slide, M, 6.05, 6.40, 0.48, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "Operator outcome: clearer staffing decisions and auditable service levels.", M + 0.22, 6.16, 5.98, 0.25, 9.7, WHITE, True)
    add_footer(slide, 10)

    # 11 — Professional GTM
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Go-to-market", "A gated enterprise adoption system—not a marketing funnel")
    steps = [
        ("1", "LIGHTHOUSE", "KL East", "Deploy with the real operator, data and member workflow."),
        ("2", "VALUE GATE", "Measured proof", "Pass technical, adoption, operational and commercial thresholds."),
        ("3", "PORTFOLIO", "Qualified SDP malls", "Expand only where readiness and parking pressure justify it."),
        ("4", "PRODUCTISE", "Repeatable playbook", "Standardise integrations, governance, training and support."),
        ("5", "OPTION", "External scale", "Choose internal, JV or licensed model after reference proof."),
    ]
    for i, (num, tag, title, body) in enumerate(steps):
        x = M + i * 2.43
        add_rect(slide, x, 1.82, 2.15, 3.73, fill=WHITE if i != 0 else NAVY, line=LINE if i != 0 else NAVY, radius=True)
        add_text(slide, num, x + 0.18, 2.02, 0.45, 0.26, 10, GOLD, True)
        add_text(slide, tag, x + 0.18, 2.48, 1.74, 0.23, 9.2, GOLD if i == 0 else [BLUE, RED, GREEN, SLATE][i-1], True)
        add_text(slide, title, x + 0.18, 2.92, 1.76, 0.60, 17, WHITE if i == 0 else INK, True)
        add_text(slide, body, x + 0.18, 3.72, 1.76, 1.15, 10.2, "D6DFE7" if i == 0 else SLATE)
        if i < 4:
            add_text(slide, "›", x + 2.17, 3.27, 0.25, 0.40, 24, GOLD, True, align=PP_ALIGN.CENTER)
    add_rect(slide, M, 5.90, 11.88, 0.50, fill=PALE_BLUE, line="C8D8F2", radius=True)
    add_text(slide, "Buyer coalition: Mall GM  •  Parking operator  •  Loyalty/digital  •  IT & DPO  •  Finance", M + 0.22, 6.04, 11.44, 0.20, 10.5, BLUE, True, align=PP_ALIGN.CENTER)
    add_footer(slide, 11, "Framework adapted to ParkFlow from BCG proof-of-value, Bain repeatable models and HBR pilot-to-scale guidance.")

    # 12 — Horizons
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Three horizons", "Build the next option before the current horizon is complete")
    add_image_crop(slide, charts["horizons"], M, 1.52, 11.90, 3.18)
    horizon_cards = [
        (M, "H1  •  0–6 months", "Prove at KL East", "Deterministic fulfilment, member adoption, operator value and data quality.", BLUE),
        (4.76, "H2  •  6–24 months", "Replicate in SDP", "Readiness screen, loyalty integration and a standard operating playbook.", GOLD),
        (8.89, "H3  •  24–48 months", "Exercise the option", "Productise for internal ownership, a JV or selective external licensing.", GREEN),
    ]
    for x, tag, title, body, accent in horizon_cards:
        add_rect(slide, x, 4.80, 3.82, 1.52, fill=WHITE, line=LINE, radius=True)
        add_text(slide, tag, x + 0.20, 5.02, 3.35, 0.23, 9.2, accent, True)
        add_text(slide, title, x + 0.20, 5.37, 3.35, 0.31, 15, INK, True)
        add_text(slide, body, x + 0.20, 5.77, 3.35, 0.42, 9.6, SLATE)
    add_footer(slide, 12)

    # 13 — Ownership choices
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Operating model", "Keep ownership open until the evidence changes the answer")
    options = [
        ("SDP-owned capability", "Highest control", "SDP funds, operates and retains the data and capability.", "Best if portfolio value dominates."),
        ("Joint venture / managed service", "Balanced", "SDP anchors demand while a venture team builds and operates the platform.", "Best if specialist execution is needed."),
        ("Independent platform", "Highest external upside", "A standalone company licenses ParkFlow to SDP and other asset owners.", "Only after repeatability is proven."),
    ]
    for i, (title, label, body, use) in enumerate(options):
        x = M + i * 4.08
        add_rect(slide, x, 1.78, 3.76, 3.92, fill=WHITE, line=LINE, radius=True)
        add_text(slide, f"OPTION {i+1}", x + 0.24, 2.03, 1.0, 0.22, 9.2, [BLUE, GOLD, GREEN][i], True)
        add_text(slide, title, x + 0.24, 2.45, 3.16, 0.66, 19, INK, True)
        add_text(slide, label, x + 0.24, 3.24, 3.16, 0.27, 11, [BLUE, "9A7100", GREEN][i], True)
        add_text(slide, body, x + 0.24, 3.75, 3.16, 0.85, 11, SLATE)
        add_line(slide, x + 0.24, 4.82, x + 3.50, 4.82, LINE, 0.8)
        add_text(slide, use, x + 0.24, 5.05, 3.16, 0.43, 10.2, INK, True)
    add_rect(slide, M, 6.05, 11.88, 0.48, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "Recommended now: approve the lighthouse under SDP sponsorship; make ownership a Horizon 2 decision gate.", M + 0.22, 6.18, 11.44, 0.20, 10.5, WHITE, True, align=PP_ALIGN.CENTER)
    add_footer(slide, 13)

    # 14 — Pilot ask
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Decision and pilot", "Approve a bounded proof with four non-negotiable gates")
    gates = [
        ("TECHNICAL", "≥99%", "accepted bookings fulfilled", BLUE),
        ("ADOPTION", "Target set", "eligible members who book and return", GOLD),
        ("OPERATIONS", "Measured", "utilization, flow and intervention improvement", GREEN),
        ("ECONOMICS", "Observed", "incremental visits, tenant sales and cost per booking", RED),
    ]
    for i, (tag, val, body, accent) in enumerate(gates):
        x = M + i * 3.02
        add_rect(slide, x, 1.78, 2.72, 2.30, fill=WHITE, line=LINE, radius=True)
        add_text(slide, tag, x + 0.20, 2.03, 2.20, 0.22, 9.2, accent, True)
        add_text(slide, val, x + 0.20, 2.47, 2.20, 0.46, 24, INK, True)
        add_text(slide, body, x + 0.20, 3.12, 2.20, 0.55, 10.5, SLATE)
    add_rect(slide, M, 4.55, 7.48, 1.30, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "THE ASK", M + 0.25, 4.82, 1.05, 0.25, 10, GOLD, True)
    add_text(slide, "Authorize site validation, vendor quotations and a KL East pilot design with agreed data access and success gates.", M + 1.35, 4.75, 5.45, 0.65, 16, WHITE, True)
    add_rect(slide, 8.34, 4.55, 3.68, 1.30, fill=PALE_GOLD, line="F2D978", radius=True)
    add_text(slide, "NO SCALE COMMITMENT", 8.60, 4.82, 2.95, 0.24, 10, "8A6700", True, align=PP_ALIGN.CENTER)
    add_text(slide, "Horizon 2 begins only if the lighthouse passes.", 8.60, 5.22, 2.95, 0.34, 11.5, INK, True, align=PP_ALIGN.CENTER)
    add_footer(slide, 14)

    # A1 — Control rule
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Appendix A1", "Deterministic available-to-promise rule")
    add_rect(slide, M, 1.72, 11.88, 1.20, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "AVAILABLE TO PROMISE", M + 0.30, 2.02, 2.15, 0.27, 10, GOLD, True)
    add_text(slide, "Zone capacity  −  vehicles inside  −  protected upcoming reservations  −  safety allowance", M + 2.68, 1.96, 8.68, 0.42, 18, WHITE, True)
    blocks = [
        ("Entry / exit truth", "Matched LPR events maintain boundary occupancy."),
        ("Reservation ledger", "Each accepted arrival window consumes protected capacity until arrival or expiry."),
        ("Hard acceptance", "Accept only when capacity remains non-negative across the protected interval."),
        ("Forecast advisory", "Prediction proposes likely future openings; it does not override the guarantee."),
    ]
    for i, (title, body) in enumerate(blocks):
        x = M + (i % 2) * 6.05
        y = 3.35 + (i // 2) * 1.38
        add_rect(slide, x, y, 5.72, 1.05, fill=WHITE, line=LINE, radius=True)
        add_text(slide, title, x + 0.22, y + 0.17, 1.75, 0.30, 13, INK, True)
        add_text(slide, body, x + 2.07, y + 0.17, 3.30, 0.56, 10.5, SLATE)
    add_footer(slide, 15, "Final allowance and expiry rules require site geometry, operating policy and pilot calibration.")

    # A2 — Forecast
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Appendix A2", "Forecasting supports decisions across the whole car park")
    sources = ["Zone entry / exit", "General occupancy", "Gate flows", "Booking demand", "Time & events"]
    for i, s in enumerate(sources):
        x = M + i * 2.38
        add_rect(slide, x, 1.84, 2.10, 0.62, fill=PALE_BLUE, line="C8D8F2", radius=True)
        add_text(slide, s, x + 0.10, 2.04, 1.90, 0.20, 10, BLUE, True, align=PP_ALIGN.CENTER)
    add_text(slide, "↓", 6.10, 2.61, 1.0, 0.38, 22, GOLD, True, align=PP_ALIGN.CENTER)
    add_rect(slide, 3.60, 3.03, 6.15, 1.05, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "Availability forecast + confidence", 3.82, 3.34, 5.70, 0.30, 20, WHITE, True, align=PP_ALIGN.CENTER)
    outputs = [
        ("Member", "Book now / later / general parking"),
        ("Non-member", "Go to the level with space"),
        ("Operator", "Staff, sign, intervene and learn"),
    ]
    for i, (who, action) in enumerate(outputs):
        x = 1.05 + i * 4.12
        add_text(slide, "↓", x + 1.30, 4.20, 0.60, 0.35, 20, GOLD, True, align=PP_ALIGN.CENTER)
        add_rect(slide, x, 4.70, 3.48, 1.15, fill=WHITE, line=LINE, radius=True)
        add_text(slide, who, x + 0.18, 4.91, 0.95, 0.28, 12, [GOLD, MUTED, BLUE][i], True)
        add_text(slide, action, x + 1.18, 4.91, 2.05, 0.51, 10.5, INK, True)
    add_footer(slide, 16)

    # A3 — Evidence register
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Appendix A3", "Evidence register: what is supported and what remains a pilot question")
    supported = [
        "High-frequency Malaysian mall visitors report higher per-trip spend.",
        "Established mall programmes combine loyalty qualification and parking privileges.",
        "KL East Mall has 1,300 bays and more than 200 retail outlets.",
        "A gated LPR boundary can produce deterministic entry/exit observations.",
    ]
    hypotheses = [
        "Priority booking causes eligible members to visit more often.",
        "Incremental visits generate a specific GTO-rent outcome at KL East.",
        "Current cost estimates survive procurement and integration discovery.",
        "The operating model replicates economically across other SDP malls.",
    ]
    add_rect(slide, M, 1.70, 5.72, 4.58, fill=PALE_GREEN, line="B7DDCF", radius=True)
    add_text(slide, "SUPPORTED", M + 0.25, 1.99, 1.5, 0.24, 10, GREEN, True)
    add_bullets(slide, supported, M + 0.25, 2.46, 5.15, 2.90, 12, INK, spacing=9)
    add_rect(slide, 6.66, 1.70, 5.40, 4.58, fill=PALE_RED, line="F2C2C5", radius=True)
    add_text(slide, "TO VALIDATE", 6.91, 1.99, 1.5, 0.24, 10, RED, True)
    add_bullets(slide, hypotheses, 6.91, 2.46, 4.83, 2.90, 12, INK, spacing=9)
    add_footer(slide, 17)

    # A4 — Portfolio readiness
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Appendix A4", "Portfolio expansion requires a readiness screen")
    criteria = [
        ("Pressure", "Measured peak occupancy and member pain"),
        ("Geometry", "A controllable Priority Zone boundary"),
        ("Identity", "Member and plate registration capability"),
        ("Data", "Reliable gate and occupancy observations"),
        ("Operator", "Contractual and operational participation"),
        ("Economics", "A site-specific cost and value case"),
    ]
    for i, (title, body) in enumerate(criteria):
        x = M + (i % 3) * 4.08
        y = 1.75 + (i // 3) * 2.05
        add_rect(slide, x, y, 3.76, 1.62, fill=WHITE, line=LINE, radius=True)
        add_text(slide, f"0{i+1}", x + 0.22, y + 0.20, 0.48, 0.25, 10, GOLD, True)
        add_text(slide, title, x + 0.78, y + 0.17, 2.55, 0.34, 15, INK, True)
        add_text(slide, body, x + 0.22, y + 0.73, 3.25, 0.56, 10.5, SLATE)
    add_rect(slide, M, 6.03, 11.88, 0.49, fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "No automatic four-mall rollout: each site must pass all six tests or receive a different intervention.", M + 0.22, 6.16, 11.44, 0.20, 10.5, WHITE, True, align=PP_ALIGN.CENTER)
    add_footer(slide, 18)

    # A5 — Sources
    slide = prs.slides.add_slide(blank)
    add_header(slide, "Appendix A5", "Selected sources and modelling notes")
    sources = [
        "Sime Darby Property — KL East Mall: 1,300 parking bays; 200+ retail outlets.",
        "Vase.ai, Malaysia Shopping Mall Report 2026 — n=500; mean recalled spend RM327 for 5+ visits/month vs RM195 for 1–2.",
        "1 Utama ONECARD official FAQ and Silver T&C — member-only preferred parking; RM20,000 and 100-transaction Silver criteria.",
        "The Gardens Club official programme and T&C — qualified loyalty membership and spend-linked parking privileges.",
        "ParkFlow analysis scripts — forecast backtests and simulated zone operations; results are model evidence, not KL East field outcomes.",
        "BCG (2026) — customer-specific proof of value for enterprise software; Bain — disciplined one-step adjacency and repeatable models; HBR — design pilot replication before scale.",
    ]
    add_bullets(slide, sources, M, 1.70, 11.65, 4.65, 12.2, INK, spacing=10)
    add_rect(slide, M, 6.12, 11.88, 0.48, fill=PALE_GOLD, line="F2D978", radius=True)
    add_text(slide, "All financial outputs in this deck are planning scenarios unless labelled as verified external benchmarks.", M + 0.22, 6.25, 11.44, 0.20, 10.5, "7A5B00", True, align=PP_ALIGN.CENTER)
    add_footer(slide, 19)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PPTX)
    print(f"wrote {OUT_PPTX}")


if __name__ == "__main__":
    build_deck()
