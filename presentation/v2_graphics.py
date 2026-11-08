"""SVG exhibit generators for the ParkFlow V2 deck.

Data plots use recorded benchmark outputs and the shared financial model.
Generated standalone SVG files are disposable; the HTML embeds each exhibit.
"""
from pathlib import Path
import io
import json
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
import numpy as np

from booking_economics import economics, UPFRONT

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site-consulting'
ASSETS=SITE/'assets/v2-charts'
NAVY,BLUE,MUTED,RULE='#102a43','#245bd8','#53647a','#d5dde7'
font_manager.fontManager.addfont(str(SITE/'assets/public-sans.ttf'))
plt.rcParams.update({'font.family':'Public Sans','font.size':14,'text.color':NAVY,'axes.labelcolor':MUTED,
                     'axes.edgecolor':RULE,'xtick.color':MUTED,'ytick.color':MUTED,'svg.fonttype':'none',
                     'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,
                     'axes.spines.bottom':False,'xtick.major.size':0,'ytick.major.size':0})


def svg(fig,name):
    stream=io.StringIO()
    with plt.rc_context({'svg.hashsalt':name}):
        fig.savefig(stream,format='svg',transparent=True,metadata={'Date':None},bbox_inches='tight',pad_inches=.25)
    plt.close(fig)
    value=stream.getvalue();value=value[value.index('<svg'):]
    for id in re.findall(r'\bid="([^"]+)"',value):
        new=name+'-'+id
        value=value.replace('id="'+id+'"','id="'+new+'"').replace('url(#'+id+')','url(#'+new+')').replace('href="#'+id+'"','href="#'+new+'"')
    ASSETS.mkdir(parents=True,exist_ok=True)
    (ASSETS/(name+'.svg')).write_text(value,encoding='utf-8')
    return value


def outcomes(result,deck=False):
    p=result['settings']['mixed_100']['policies']
    fig,ax=plt.subplots(figsize=(14.5,4.5) if deck else (12.6,5.7))
    selected=[('guard','Guard only'),('calibrated_fixed','Calibrated fixed buffer'),('lp_adaptive','Adaptive forecast + LP'),
              ('lp_linear','Linear forecast + LP'),('lp_ml','Learned forecast + LP'),('request_oracle','Request oracle reference')]
    offsets=[(-15,-35),(-120,24),(20,24),(20,-30),(-210,-12),(15,45)]
    for (key,label),(ox,oy) in zip(selected,offsets):
        x,y=p[key]['walkins'],p[key]['fulfilled']
        color=BLUE if key=='lp_ml' else (NAVY if key in ['calibrated_fixed','lp_adaptive'] else '#8795a7')
        ax.scatter(x,y,s=135 if key=='lp_ml' else 75,color=color,zorder=4,edgecolor='white',linewidth=1.5)
        ax.annotate(label,(x,y),xytext=(ox,oy),textcoords='offset points',fontsize=15 if deck else 13,color=color,
                    arrowprops={'arrowstyle':'-','color':color,'lw':.8},zorder=5)
    xs=[p[k]['walkins'] for k,_ in selected];ys=[p[k]['fulfilled'] for k,_ in selected]
    ax.set_xlim(min(xs)-max(20,(max(xs)-min(xs))*.28),max(xs)+max(20,(max(xs)-min(xs))*.32))
    ax.set_ylim(min(ys)-max(6,(max(ys)-min(ys))*.3),max(ys)+max(6,(max(ys)-min(ys))*.4))
    ax.grid(color=RULE,linewidth=.65,zorder=0)
    ax.set_xlabel('Walk-ins admitted per day',labelpad=18)
    ax.set_ylabel('Member arrivals served per day',labelpad=18)
    fig.subplots_adjust(left=.09,right=.95,top=.92,bottom=.16)
    return svg(fig,'operating-tradeoff-deck' if deck else 'operating-tradeoff')


def forecast_chart(deck=False):
    result=json.loads((ROOT/'analysis/benchmarks/v2/occupancy.json').read_text())
    fig,ax=plt.subplots(figsize=(14.5,4.6) if deck else (12.6,5.3));rows=result['metrics'];x=[v['minutes'] for v in rows]
    for key,label,color in [('last_week','Same time last week','#8795a7'),('adjusted','Adjusted last week','#a8bddd'),('ensemble','Ensemble',BLUE)]:
        y=[v['mae_pct_capacity'][key] for v in rows]
        ax.plot(x,y,'o-',linewidth=2.3,markersize=7,color=color,label=label)
    for key,delta in [('last_week',.1),('adjusted',.27),('ensemble',-.22)]:
        v=rows[-1]['mae_pct_capacity'][key]
        ax.annotate(f'{v:.2f}%',(180,v),xytext=(192,v+delta),color=BLUE if key=='ensemble' else MUTED,fontsize=16 if deck else 14,
                    arrowprops={'arrowstyle':'-','color':RULE,'lw':1})
    ax.set_xlim(20,210);ax.set_ylim(0,7)
    ax.set_xticks(x,[str(t)+' min' for t in x]);ax.set_yticks([0,2,4,6])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y,_:f'{y:g}%'))
    ax.grid(axis='y',color=RULE,linewidth=.65)
    ax.set_ylabel('MAE as percent of capacity',labelpad=18)
    ax.legend(loc='upper left',frameon=False,ncol=3,fontsize=15 if deck else 13)
    fig.subplots_adjust(left=.09,right=.97,top=.92,bottom=.13)
    return svg(fig,'forecast-horizon-deck' if deck else 'forecast-horizon')


def visit_contour(deck=False):
    gap=UPFRONT/5-economics()['contribution']
    capture=np.linspace(3,8,220);spend=np.linspace(195,327,220)
    xx,yy=np.meshgrid(capture,spend)
    visits=gap/(52*yy*xx/100)
    fig,ax=plt.subplots(figsize=(14,4.6) if deck else (12.6,5.6))
    filled=ax.contourf(xx,yy,visits,levels=[0,7,10,13,17,22,30],cmap='Blues_r')
    contours=ax.contour(xx,yy,visits,levels=[7,10,13,17,22],colors='#ffffff',linewidths=.65)
    labels=ax.clabel(contours,inline=True,fontsize=14 if deck else 12,colors=NAVY,fmt=lambda v:f'{v:g} visits')
    for label in labels:
        label.set_rotation(0)
        label.set_bbox({'facecolor':'white','edgecolor':'none','alpha':.96,'pad':2})
    ax.scatter([5],[260],color=BLUE,edgecolors='white',s=115,zorder=5)
    ax.annotate('Base illustration\n13 extra visits/week',(5,260),xytext=(5.7,300),fontsize=16 if deck else 14,color=NAVY,
                bbox={'facecolor':'white','edgecolor':'none','pad':9},arrowprops={'arrowstyle':'-','color':BLUE,'lw':1.2})
    ax.set_xlabel('Illustrative effective mall capture',labelpad=15)
    ax.set_ylabel('Illustrative spend per extra visit',labelpad=15)
    ax.set_xticks([3,4,5,6,7,8],[f'{v}%' for v in [3,4,5,6,7,8]])
    ax.set_yticks([195,220,260,300,327],[f'RM{v}' for v in [195,220,260,300,327]])
    colorbar=fig.colorbar(filled,ax=ax,pad=.035,shrink=.88)
    colorbar.set_label('Extra weekly visits required',labelpad=12)
    fig.subplots_adjust(left=.11,right=.96,top=.95,bottom=.15)
    return svg(fig,'visit-contour-deck' if deck else 'visit-contour')



def horizon_curves():
    """Qualitative roadmap, with early option work and no invented value axis."""
    graphic='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 620" role="img" aria-labelledby="three-horizons-title three-horizons-description">
<title id="three-horizons-title">Three overlapping horizons for ParkFlow</title>
<desc id="three-horizons-description">Three curves reach progressively higher stages of proposed service scope: one KL East zone, a repeatable SDP operating system, and an external platform. Dashed early segments show discovery in parallel. Heights are schematic, not revenue, adoption or measured performance.</desc>
<g font-family="Public Sans,Arial,sans-serif" fill="#102a43">
<text x="80" y="38" font-size="22" font-weight="600">H1 · KL East member service</text>
<text x="80" y="70" font-size="17" fill="#53647a">Primary focus: 0–6 months</text>
<text x="460" y="38" font-size="22" font-weight="600">H2 · SDP operating system</text>
<text x="460" y="70" font-size="17" fill="#53647a">Primary focus: 6–24 months</text>
<text x="460" y="94" font-size="14" fill="#53647a">Potential sites: Elmina + KLGCC</text>
<text x="840" y="38" font-size="22" font-weight="600">H3 · External platform</text>
<text x="840" y="70" font-size="17" fill="#53647a">Primary focus: 24–60 months</text>
<text x="80" y="116" font-size="15" fill="#53647a">Illustrative expansion of scope: one site → SDP portfolio → external operators</text>
<path d="M80 430 C140 430 180 420 230 385 C270 345 310 328 370 328 L610 328" fill="none" stroke="#102a43" stroke-width="4.5" stroke-linecap="round"/>
<path d="M80 438 C200 438 300 434 350 418" fill="none" stroke="#536c9a" stroke-width="2.4" stroke-dasharray="7 8"/>
<path d="M350 418 C405 410 435 350 500 328 C570 285 615 225 690 225 L1040 225" fill="none" stroke="#536c9a" stroke-width="4.5" stroke-linecap="round"/>
<path d="M80 446 C350 446 600 446 680 425" fill="none" stroke="#245bd8" stroke-width="2.4" stroke-dasharray="7 8"/>
<path d="M680 425 C760 415 800 330 850 285 C885 260 915 245 940 225 C965 205 1020 150 1115 150 L1200 150" fill="none" stroke="#245bd8" stroke-width="4.5" stroke-linecap="round"/>
<circle cx="610" cy="328" r="6" fill="#102a43"/>
<circle cx="1040" cy="225" r="6" fill="#536c9a"/>
<circle cx="1200" cy="150" r="6" fill="#245bd8"/>
<circle cx="500" cy="328" r="7" fill="#fff" stroke="#536c9a" stroke-width="3"/>
<circle cx="940" cy="225" r="7" fill="#fff" stroke="#245bd8" stroke-width="3"/>
<text x="160" y="247" font-size="19" font-weight="550">Reliable member access</text>
<text x="160" y="276" font-size="16" fill="#53647a">Bookings + verified admission</text>
<text x="640" y="260" font-size="19" font-weight="550">Repeatable deployment</text>
<text x="640" y="290" font-size="16" fill="#53647a">Shared interfaces</text>
<text x="640" y="315" font-size="16" fill="#53647a">+ onboarding</text>
<text x="965" y="358" font-size="19" font-weight="550">A contracted platform</text>
<text x="965" y="387" font-size="16" fill="#53647a">Multi-operator APIs + support</text>
<path d="M80 465 H1200 M1192 459 L1200 465 L1192 471" fill="none" stroke="#a8b7ca" stroke-width="1.2"/>
<text x="80" y="493" font-size="15" fill="#53647a">Now</text>
<text x="1200" y="493" text-anchor="end" font-size="15" fill="#53647a">Planning windows · not a linear time axis</text>
<text x="80" y="535" font-size="15" fill="#53647a">Before expansion</text>
<text x="80" y="563" font-size="18">Service readiness + full-cost review</text>
<text x="460" y="535" font-size="15" fill="#53647a">Before wider deployment</text>
<text x="460" y="563" font-size="18">Repeatable delivery at approved sites</text>
<text x="840" y="535" font-size="15" fill="#53647a">Before external rollout</text>
<text x="840" y="563" font-size="18">Signed contracts + viable support</text>
<path d="M80 603 H117" stroke="#102a43" stroke-width="3"/><text x="129" y="608" font-size="14" fill="#53647a">Main development focus</text>
<path d="M430 603 H467" stroke="#245bd8" stroke-width="2" stroke-dasharray="6 5"/><text x="479" y="608" font-size="14" fill="#53647a">Early discovery and option work</text>
<circle cx="850" cy="603" r="5" fill="#fff" stroke="#536c9a" stroke-width="2"/><text x="866" y="608" font-size="14" fill="#53647a">Shared capability link</text>
</g></svg>'''
    ASSETS.mkdir(parents=True,exist_ok=True)
    (ASSETS/'three-horizons.svg').write_text(graphic,encoding='utf-8')
    return graphic
