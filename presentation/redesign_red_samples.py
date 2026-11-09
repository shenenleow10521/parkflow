"""Redesign 4 sample slides of site-consulting/index.html in the red consulting style."""
import re, sys

PATH = sys.argv[1]
h = open(PATH, encoding="utf-8").read()

CSS = """<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600&display=swap" rel="stylesheet">
<style id="redx-style">
/* Red consulting redesign (sample slides) */
.redx .frame { --rx-ink:#1F2937; --rx-slate:#6B7280; --rx-rule:#E5E7EB; --rx-r9:#7F1D1D; --rx-r7:#B91C1C; --rx-r1:#FEE2E2; --rx-r05:#FEF2F2; --rx-bar:#D1D5DB;
  color:var(--rx-ink); font-variant-numeric:tabular-nums; }
/* Header flows, so two-line titles push the content down instead of overlapping */
.redx .frame { display:flex; flex-direction:column; padding:36px 64px 104px; }
.redx .rx-tracker { display:flex; justify-content:space-between; align-items:center;
  font-size:13px; font-weight:650; letter-spacing:.1em; text-transform:uppercase; }
.redx .rx-tracker .sec { color:var(--rx-r7); }
.redx .rx-tracker .proj { color:var(--rx-slate); }
.redx .slide-title { position:static; margin-top:14px; color:var(--rx-ink); font-family:'Source Serif 4',Georgia,serif; font-weight:600; font-size:38px;
  line-height:1.15; letter-spacing:-.01em; max-width:none; }
.redx .rx-sub { margin-top:8px; font-size:18px; color:var(--rx-slate); }
.redx .rx-rule { position:relative; flex:none; margin-top:18px; height:1px; background:var(--rx-rule); }
.redx .rx-rule::before { content:""; position:absolute; left:0; top:-1px; width:90px; height:3px; background:var(--rx-r7); }
.redx .content { position:static; flex:1; min-height:0; margin-top:26px; gap:22px; }
.redx .source { color:var(--rx-slate); }
.redx .footer .active { color:var(--rx-r7); }
.redx .rx-label { font-size:13px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--rx-slate); }
.redx .rx-label b { color:var(--rx-ink); }

/* Ask panel + numbered list (slides 3, 25) */
.redx .rx-split { flex:1; display:grid; grid-template-columns:560px 1fr; gap:56px; min-height:0; }
.redx .rx-ask { background:var(--rx-r9); color:#fff; padding:40px 44px; display:flex; flex-direction:column; }
.redx .rx-ask .rx-label { color:var(--rx-r1); }
.redx .rx-ask h3 { font-family:'Source Serif 4',Georgia,serif; font-weight:600; font-size:42px; line-height:1.12; margin-top:18px; }
.redx .rx-ask p { font-size:20px; line-height:1.45; margin-top:18px; color:var(--rx-r1); }
.redx .rx-ask .rx-budget { margin-top:auto; padding-top:22px; border-top:1px solid rgba(255,255,255,.3); display:flex; align-items:baseline; gap:16px; }
.redx .rx-ask .rx-budget b { font-size:64px; font-weight:700; letter-spacing:-.03em; line-height:1; color:#fff; }
.redx .rx-ask .rx-budget span { font-size:16px; color:var(--rx-r1); }
.redx .rx-list { display:flex; flex-direction:column; }
.redx .rx-list .rx-label { padding-bottom:12px; border-bottom:2px solid var(--rx-ink); }
.redx .rx-item { flex:1; display:grid; grid-template-columns:64px 1fr; align-items:center; border-bottom:1px solid var(--rx-rule); }
.redx .rx-item .n { font-size:30px; font-weight:700; color:var(--rx-r7); }
.redx .rx-item .k { display:block; font-size:13px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--rx-r7); }
.redx .rx-item h4 { font-size:26px; line-height:1.2; font-weight:650; margin:4px 0 0; }
.redx .rx-item p { font-size:18px; line-height:1.4; color:var(--rx-slate); margin-top:4px; }
.redx .rx-check { width:30px; height:30px; border:2px solid var(--rx-r7); display:flex; align-items:center; justify-content:center; color:var(--rx-r7); font-size:18px; font-weight:700; }

/* Exhibits with bar charts (slides 11, 16) */
.redx .rx-cols { flex:1; display:grid; gap:0; min-height:0; }
.redx .rx-col { padding:0 40px; border-left:1px solid var(--rx-rule); display:flex; flex-direction:column; min-width:0; }
.redx .rx-col:first-child { padding-left:0; border-left:0; }
.redx .rx-col:last-child { padding-right:0; }
.redx .rx-kpi { display:flex; align-items:baseline; gap:16px; margin-top:16px; padding-bottom:16px; border-bottom:1px solid var(--rx-rule); }
.redx .rx-kpi .num { font-size:52px; font-weight:700; letter-spacing:-.03em; line-height:1; color:var(--rx-r7); }
.redx .rx-kpi .cap { font-size:17px; color:var(--rx-slate); line-height:1.35; }
.redx .rx-bars { margin-top:16px; }
.redx .rx-row { display:grid; grid-template-columns:var(--lw,250px) 1fr; min-height:60px; font-size:18px; }
.redx .rx-row .lbl { align-self:center; padding-right:14px; line-height:1.2; }
.redx .rx-row .track { display:flex; align-items:center; gap:10px; border-left:1.5px solid var(--rx-ink); }
.redx .rx-row .bar { height:22px; width:calc(var(--w) * .8%); min-width:3px; background:var(--rx-bar); }
.redx .rx-row .val { font-weight:650; }
.redx .rx-row.hl .bar { background:var(--rx-r7); }
.redx .rx-row.hl .lbl,.redx .rx-row.hl .val { color:var(--rx-r7); font-weight:700; }
.redx .rx-axis { font-size:14px; color:var(--rx-slate); margin-top:8px; padding-left:var(--lw,250px); }
.redx .rx-callout { margin-top:18px; padding-left:16px; border-left:3px solid var(--rx-r7); font-size:18px; line-height:1.4; }
.redx .rx-callout b { color:var(--rx-r7); }
.redx .rx-tag { align-self:flex-start; margin-top:14px; padding:5px 12px; font-size:14px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; border:2px solid var(--rx-ink); }
.redx .rx-tag.red { background:var(--rx-r7); border-color:var(--rx-r7); color:#fff; }
.redx .rx-tag.outline { border-color:var(--rx-r7); color:var(--rx-r7); }
.redx .rx-col p.rx-body { font-size:18px; line-height:1.45; margin-top:16px; }

/* Implication bar */
.redx .rx-sowhat { flex:none; display:flex; align-items:stretch; min-height:66px; background:var(--rx-r9); color:#fff; font-size:20px; }
.redx .rx-sowhat .tag { display:flex; align-items:center; padding:0 24px; background:var(--rx-r7); font-size:14px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }
.redx .rx-sowhat .msg { display:flex; align-items:center; padding:0 24px; font-weight:600; }
</style>"""

# Replace any earlier copy of the injected fonts + style so reruns pick up CSS changes
h = re.sub(r'<link rel="preconnect" href="https://fonts.googleapis.com">.*?<style id="redx-style">.*?</style>', "", h, flags=re.S)
h = h.replace("</head>", CSS + "</head>", 1)


def bars(rows, lw=None):
    out = []
    for label, val, w, hl in rows:
        out.append(f'<div class="rx-row{" hl" if hl else ""}"><span class="lbl">{label}</span>'
                   f'<div class="track"><div class="bar" style="--w:{w}"></div><span class="val">{val}</span></div></div>')
    style = f' style="--lw:{lw}"' if lw else ""
    return f'<div class="rx-bars"{style}>' + "".join(out) + "</div>"


def head(num, section, title, sub=None):
    s = (f'<div class="rx-tracker"><span class="sec">{num} | {section}</span><span class="proj">ParkFlow · KL East Mall</span></div>'
         f'<h2 class="slide-title">{title}</h2>')
    if sub:
        s += f'<p class="rx-sub">{sub}</p>'
    return s + '<div class="rx-rule"></div>'


SLIDES = {
    "executive": dict(
        title="Pilot one KL East zone for RM92k, then decide whether to scale",
        head=head("03", "Overview", "Pilot one KL East zone for RM92k, then decide whether to scale"),
        content="""<div class="rx-split">
<div class="rx-ask"><span class="rx-label">Recommendation</span><h3>Prove one zone.<br>Then decide to scale.</h3>
<p>Approve site discovery and a measured KL East pilot.</p>
<div class="rx-budget"><b>RM92k</b><span>Initial scope subtotal</span></div></div>
<div class="rx-list"><span class="rx-label"><b>Three tests the pilot must pass</b></span>
<div class="rx-item"><span class="n">01</span><div><span class="k">The opportunity</span><h4>Make arrival part of the member benefit.</h4><p>Add booking and zone capacity on top of KL East’s existing LPR.</p></div></div>
<div class="rx-item"><span class="n">02</span><div><span class="k">The operating test</span><h4>Protect the promise without wasting space.</h4><p>Validate the admission rule, member uptake, cameras and exception SOP.</p></div></div>
<div class="rx-item"><span class="n">03</span><div><span class="k">The investment test</span><h4>Measure complete cost and incremental value.</h4><p>Reconcile installed scope, support and landlord capture against SDP’s return hurdle.</p></div></div>
</div></div>""",
        note=" Final installed cost to be confirmed.",
    ),
    "simulation": dict(
        title="In simulation, the forecast policy honours 100% of bookings with the fewest idle bays",
        head=head("11", "Evidence",
                  "In simulation, the forecast policy honours 100% of bookings with the fewest idle bays",
                  "Recorded policy simulation · 1,000 simulated busy days · 100-bay zone · same synthetic demand"),
        content="""<div class="rx-cols" style="grid-template-columns:1fr 1fr">
<div class="rx-col"><span class="rx-label">Exhibit 1 · <b>Bookings honoured</b></span>
<div class="rx-kpi"><span class="num">100%</span><span class="cap">of bookings honoured by the forecast policy</span></div>"""
        + bars([("No priority control", "85.5%", 27.5, False), ("Fixed VIP section", "99.9%", 99.5, False),
                ("Fixed rule: 5 safety bays", "100.0%", 100, False), ("Forecast policy", "100.0%", 100, True)])
        + """<div class="rx-axis">Axis starts at 80%</div>
<p class="rx-callout"><b>Forecast policy</b> matches the fixed rules on reliability.</p></div>
<div class="rx-col"><span class="rx-label">Exhibit 2 · <b>Idle protected bay-hours*</b></span>
<div class="rx-kpi"><span class="num">5</span><span class="cap">idle bay-hours, the lowest of the policies that honour ≥99.9% of bookings</span></div>"""
        + bars([("No priority control", "0", 0, False), ("Fixed VIP section", "19", 83, False),
                ("Fixed rule: 5 safety bays", "23", 100, False), ("Forecast policy", "5", 22, True)])
        + """<div class="rx-axis">Lower is better</div>
<p class="rx-callout"><b>Forecast policy</b> idles 18 fewer bay-hours than the fixed 5-bay rule.</p></div>
</div>
<div class="rx-sowhat"><span class="tag">Implication</span><span class="msg">The deployed guard is a different rule from the forecast policy, so its efficiency still needs a field test.</span></div>""",
        note="",
    ),
    "sanity-checks": dict(
        title="Bookings cover zone OPEX, but capital recovery needs about 13 extra visits a week",
        head=head("16", "Business", "Bookings cover zone OPEX, but capital recovery needs about 13 extra visits a week"),
        content="""<div class="rx-cols" style="grid-template-columns:1fr 1fr 1fr">
<div class="rx-col"><span class="rx-label">Check 1 · <b>Is zone OPEX covered?</b></span><span class="rx-tag">✓ Covered</span>"""
        + bars([("Break-even", "2,918", 57, False), ("Base case", "5,078", 100, True)], lw="130px")
        + """<div class="rx-axis">Annual paid bookings</div>
<p class="rx-body">About 2,918 paid bookings a year cover the RM10.5k zone OPEX; the base case assumes 5,078.</p></div>
<div class="rx-col"><span class="rx-label">Check 2 · <b>Does booking repay capital?</b></span><span class="rx-tag red">✗ RM8.5k a year short</span>"""
        + bars([("Booking contribution", "7,775", 48, True), ("5-year requirement", "16,300", 100, False)], lw="130px")
        + """<div class="rx-axis">Annual RM</div>
<p class="rx-body">RM7.8k contribution against RM16.3k needed a year for five-year simple recovery: RM8,524.60 short.</p></div>
<div class="rx-col"><span class="rx-label">Check 3 · <b>Can visits close the gap?</b></span><span class="rx-tag outline">→ 13 extra visits a week</span>"""
        + bars([("Recovery gap", "8,525", 97, False), ("13 extra visits", "8,788", 100, True)], lw="130px")
        + """<div class="rx-axis">Annual RM</div>
<p class="rx-body">At RM260 spend and 5% effective net capture, 13 additional visits a week yield RM8,788 a year.</p></div>
</div>
<div class="rx-sowhat"><span class="tag">Implication</span><span class="msg">The pilot must prove incremental visits, not just booking volume.</span></div>""",
        note=" Demand and payment costs still require validation; capture and genuinely incremental visits remain pilot questions.",
    ),
    "decision": dict(
        title="Approve RM92k discovery now; release pilot funding once four inputs are confirmed",
        head=head("25", "Implementation", "Approve RM92k discovery now; release pilot funding once four inputs are confirmed"),
        content="""<div class="rx-split">
<div class="rx-ask"><span class="rx-label">Decision today</span><h3>Authorize discovery.<br>Set the pilot up to decide.</h3>
<p>Nominate a KL East sponsor and operator counterpart; start the site survey, integration talks and baseline measurement.</p>
<div class="rx-budget"><b>RM92k</b><span>Initial planning subtotal</span></div></div>
<div class="rx-list"><span class="rx-label"><b>We return with four decision inputs</b></span>
<div class="rx-item"><span class="rx-check">✓</span><div><h4>Feasible site</h4><p>Zone boundary, incumbent interfaces and approved integration.</p></div></div>
<div class="rx-item"><span class="rx-check">✓</span><div><h4>Complete cost</h4><p>Installed quotes, support, tax and contingency.</p></div></div>
<div class="rx-item"><span class="rx-check">✓</span><div><h4>Ready operator</h4><p>Signed SOP, member terms and fault drills.</p></div></div>
<div class="rx-item"><span class="rx-check">✓</span><div><h4>Credible value test</h4><p>Baseline, cohort, measurement plan and go/adapt/stop criteria.</p></div></div>
</div></div>""",
        note=" Final installed scope pending.",
    ),
}

for sid, d in SLIDES.items():
    m = re.search(r'<section class="slide[^"]*" id="%s"[^>]*>.*?</section>' % sid, h, re.S)
    sec = m.group(0)
    if "redx" in sec.split(">", 1)[0]:
        continue
    source = re.search(r'<div class="source">.*?</div>', sec, re.S).group(0)
    if d["note"]:
        source = source[:-len("</div>")] + d["note"] + "</div>"
    footer = re.search(r'<footer class="footer">.*?</footer>', sec, re.S).group(0)
    open_tag = sec.split(">", 1)[0] + ">"
    open_tag = open_tag.replace('class="slide ', 'class="slide redx ', 1)
    open_tag = re.sub(r'aria-label="[^"]*"', 'aria-label="%s"' % d["title"], open_tag)
    new = (open_tag + '<div class="frame">' + d["head"] + '<div class="content">' + d["content"] + "</div>"
           + source + footer + "</div></section>")
    h = h.replace(sec, new, 1)

open(PATH, "w", encoding="utf-8", newline="").write(h)
print("ok")
