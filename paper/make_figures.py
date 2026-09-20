#!/usr/bin/env python3
"""Rebuild paper figures from released CSVs; requires matplotlib.

No model inference, metric fitting, or threshold selection is performed here.
"""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'figures'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,
                     'axes.spines.top':False,'axes.spines.right':False,
                     'axes.labelsize':9,'legend.fontsize':8,
                     'savefig.dpi':220,'pdf.fonttype':42})


def read(name):
    with (ROOT/'analysis'/name).open(encoding='utf-8',newline='') as stream:
        return list(csv.DictReader(stream))


def save(fig,name):
    fig.tight_layout(pad=1.2)
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight',metadata={'Software':'Mini Jev paper figures'})
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
    plt.close(fig)


families = sorted((r for r in read('family_metrics.csv') if r['source']=='generated'),
                  key=lambda r:(float(r['accuracy']),r['family']))
colors = {'choice':'#267594','noul':'#4C9579','score':'#BA7545'}
fig,ax = plt.subplots(figsize=(7,2.9))
values = [100*float(r['accuracy']) for r in families]
ax.bar(range(1,len(families)+1),values,color=[colors[r['types']] for r in families],width=.83)
ax.axhline(sum(values)/len(values),color='#26384A',linestyle='--',linewidth=1.2)
ax.set(xlabel='Observed family rank (sorted by accuracy)',ylabel='Accuracy (%)',
       ylim=(0,105),xlim=(0,46))
ax.set_yticks([0,25,50,75,100])
ax.legend(handles=[Patch(color=v,label=k.title()) for k,v in colors.items()],
          loc='lower right',frameon=False,ncol=3)
ax.grid(axis='y',alpha=.15)
ax.set_axisbelow(True)
save(fig,'family_accuracy')

rows = read('risk_coverage.csv')
fig,ax = plt.subplots(figsize=(7,2.9))
for condition,color,label in [('t1','#267594','T = 1'),('fitted','#BA7545','Local fitted T')]:
    selected = [r for r in rows if r['subset']=='all' and r['condition']==condition
                and r['score']=='max_probability']
    ax.step([100*float(r['coverage']) for r in selected],
            [100*float(r['risk']) for r in selected],where='post',color=color,label=label,linewidth=1.4)
ax.set(xlabel='Accepted coverage (%)',ylabel='Observed error rate (%)',
       xlim=(0,100),ylim=(0,7.2))
ax.legend(loc='upper left',frameon=False)
ax.grid(alpha=.18)
save(fig,'risk_coverage')
print('Wrote family_accuracy and risk_coverage, PNG and SVG')
