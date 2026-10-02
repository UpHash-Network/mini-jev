"""Plot all prespecified paid-call replay policies; descriptive point estimates only."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
if args.out.exists():raise ValueError('New figure path required')
data=json.loads(args.results.read_text())['strata']
styles={'pair_entropy_tv_rank':('Entropy + TV','#0072B2','o','-'),
        'pair_mean_entropy':('Entropy','#D55E00','s','--'),
        'pair_random':('Fixed random','#009E73','^',':'),
        'first_entropy':('First-call entropy','#CC79A7','x','-.')}
fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,sharey=True)
for ax,(key,result) in zip(axes.flat,data.items()):
    for policy,(label,color,marker,line) in styles.items():
        rows=[r for r in result['B']['curves'] if r['policy']==policy]
        ax.plot([r['budget_calls_per_item'] for r in rows],[100*r['accuracy'] for r in rows],label=label,color=color,marker=marker,linestyle=line,markersize=5,linewidth=1.7)
    ax.set_title(key.replace('qwen2.5-1.5b','Qwen2.5-1.5B').replace('phi-4-mini','Phi-4-mini (3.8B)'),fontsize=11)
    ax.set_xticks([2,2.5,3,4,5]);ax.set_ylim(0,100);ax.grid(alpha=.22)
    ax.set_xlabel('Paid calls per question (saved-pool replay)');ax.set_ylabel('Correct answers (%)')
handles,labels=axes[0,0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,.025))
fig.suptitle('Fixed-budget replay on 240 questions per task\nSame question panels across models; no online timing or human-performance claim',fontsize=13)
fig.tight_layout(rect=[0,.10,1,.91]);fig.savefig(args.out,dpi=180);plt.close(fig)
