#!/usr/bin/env python3
"""Plot completed matched-study traces; no inference or outcome filtering."""
import json
from collections import defaultdict
from pathlib import Path
import random
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    results = ROOT / 'matched_study' / 'results'
    if not (results / 'COMPLETION.json').exists():
        raise RuntimeError('The complete frozen experiment must finish before plotting')
    rows = [json.loads(line) for line in (results / 'predictions.jsonl').read_text().splitlines()]
    if len(rows) != 4050 or any(row['http_status'] != 200 for row in rows):
        raise RuntimeError('Unexpected row count or failure; do not silently filter results')
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row['dataset'] == 'local_v2':
            grouped[row['id']][row['mode']].append(row['http_ms'])
    modes = ['direct', 'one_token', 'json']
    if len(grouped) != 150 or any(len(g[mode]) != 5 for g in grouped.values() for mode in modes):
        raise RuntimeError('The local paired design does not match the frozen protocol')
    means = {mode: [statistics.mean(grouped[key][mode]) for key in sorted(grouped)] for mode in modes}
    deltas = [[b-a for a,b in zip(means['direct'],means[mode])] for mode in modes[1:]]
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':9,
                         'axes.spines.top':False, 'axes.spines.right':False,
                         'savefig.dpi':220, 'pdf.fonttype':42})
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.1), gridspec_kw={'width_ratios':[1.2,1]})
    colors = ['#267594', '#4C9579', '#BA7545']
    rng = random.Random(20260920)
    for ax, data, labels, palette in [
        (axes[0], [means[m] for m in modes], ['Direct', 'One token', 'JSON'], colors),
        (axes[1], deltas, ['One token\nminus direct', 'JSON\nminus direct'], colors[1:]),
    ]:
        boxes = ax.boxplot(data, tick_labels=labels, patch_artist=True, showfliers=False,
                           medianprops={'color':'#172C3E','linewidth':1.5}, widths=.5)
        for patch,color in zip(boxes['boxes'],palette):
            patch.set_facecolor(color)
            patch.set_alpha(.25)
        for i, (values,color) in enumerate(zip(data,palette),1):
            ax.scatter([i+rng.uniform(-.12,.12) for _ in values], values,
                       s=5, color=color, alpha=.38, linewidths=0, zorder=2)
        ax.grid(axis='y', alpha=.16)
        ax.set_axisbelow(True)
        ax.tick_params(axis='x', labelsize=8)
    axes[0].set(ylabel='Per-item mean HTTP latency (ms)', title='(a) Complete requests')
    axes[1].set(ylabel='Paired mean difference (ms)', title='(b) Difference from direct')
    axes[1].axhline(0, color='#52616F', linestyle='--', linewidth=.9)
    fig.tight_layout(pad=1.1)
    out = ROOT / 'figures'
    out.mkdir(exist_ok=True)
    fig.savefig(out / 'matched_latency.png', bbox_inches='tight',
                metadata={'Software':'Mini Jev empirical paper figures'})
    fig.savefig(out / 'matched_latency.svg', bbox_inches='tight', metadata={'Date':None})
    plt.close(fig)
    print('Wrote matched_latency, PNG and SVG; 150 items, five paired repetitions')


if __name__ == '__main__':
    main()
