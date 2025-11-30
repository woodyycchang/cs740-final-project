#!/usr/bin/env python3
# plot_dns_latency_improved.py
# 改进画法：按 site 先计算 median，再跨站点聚合；误差用 IQR；输出到 new_fig
# 并为每个 mode 单独绘制一张 per-site 图，site 顺序按 config/sites.txt（前10）先，
# 再按 config/unpopular_sites.txt（前10）后；其余 site 放在最后（任意顺序）。

import os, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

INPUT_DIRS = ["new_data/raw", "new_data/unpop_raw"]
PATTERN = "*_dns_*.csv"
OUT_DIR = "new_fig"
os.makedirs(OUT_DIR, exist_ok=True)

# config files (will take first 10 entries from each)
POPULAR_CFG = "config/sites.txt"
UNPOPULAR_CFG = "config/unpopular_sites.txt"
POPULAR_N = 10
UNPOPULAR_N = 10

def read_site_list(path, max_items=None):
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if max_items is not None:
        return lines[:max_items]
    return lines

def mode_from_filename(fname):
    base = os.path.basename(fname)
    parts = base.split('_')
    if len(parts) < 3:
        return None
    if parts[0] == "local" and len(parts) >= 4 and parts[1] == "cache":
        return "local_cache"
    return parts[0]

def kind_from_filename(fname):
    base = os.path.basename(fname).lower()
    if "_cold" in base:
        return "cold"
    if "_warm" in base:
        return "warm"
    return None

# load files
files = []
for d in INPUT_DIRS:
    if os.path.isdir(d):
        files += glob.glob(os.path.join(d, PATTERN))
if not files:
    raise SystemExit("No *_dns_*.csv files found under new_data/raw or new_data/unpop_raw")

# aggregate per mode -> per site -> lists for cold & warm
data = {}
for f in files:
    mode = mode_from_filename(f)
    kind = kind_from_filename(f)
    if mode is None or kind is None:
        print("Skipping", f)
        continue
    df = pd.read_csv(f)
    # normalize
    df.columns = [c.strip() for c in df.columns]
    lowcols = {c: c.lower() for c in df.columns}
    df = df.rename(columns=lowcols)
    if not {'site','ms','trial'}.issubset(set(df.columns)):
        print(f"File {f} missing required columns, skip")
        continue
    df['ms'] = pd.to_numeric(df['ms'], errors='coerce')
    if 'status' in df.columns:
        df = df[df['status'].astype(str).str.lower() == 'ok']
    data.setdefault(mode, {})
    if kind == "cold":
        for site, g in df.groupby('site'):
            cold_vals = g.loc[g['trial'] == 1, 'ms'].dropna().tolist()
            warm_vals = g.loc[g['trial'] != 1, 'ms'].dropna().tolist()
            e = data[mode].setdefault(site, {"cold": [], "warm": []})
            e['cold'].extend(cold_vals)
            e['warm'].extend(warm_vals)
    else: # warm file
        for site, g in df.groupby('site'):
            e = data[mode].setdefault(site, {"cold": [], "warm": []})
            e['warm'].extend(g['ms'].dropna().tolist())

# compute per-site medians, then per-mode summary (median of site-medians + IQR)
modes = sorted(data.keys())
mode_summary = {}
for mode in modes:
    site_stats = {}
    for site, vals in data[mode].items():
        cold_arr = np.array(vals['cold'], dtype=float)
        warm_arr = np.array(vals['warm'], dtype=float)
        # per-site medians (if no samples, produce NaN)
        cold_med = np.nan if cold_arr.size == 0 else float(np.nanmedian(cold_arr))
        warm_med = np.nan if warm_arr.size == 0 else float(np.nanmedian(warm_arr))
        site_stats[site] = {'cold_med': cold_med, 'warm_med': warm_med,
                            'cold_n': int(cold_arr.size), 'warm_n': int(warm_arr.size)}
    # gather arrays of per-site medians (exclude NaN sites)
    cold_meds = np.array([v['cold_med'] for v in site_stats.values() if not np.isnan(v['cold_med'])], dtype=float)
    warm_meds = np.array([v['warm_med'] for v in site_stats.values() if not np.isnan(v['warm_med'])], dtype=float)

    def summarize(arr):
        if arr.size == 0:
            return {'median': np.nan, 'q1': np.nan, 'q3': np.nan, 'n_sites': 0}
        q1 = np.percentile(arr, 25)
        m = np.percentile(arr, 50)
        q3 = np.percentile(arr, 75)
        return {'median': float(m), 'q1': float(q1), 'q3': float(q3), 'n_sites': int(arr.size)}

    mode_summary[mode] = {
        'per_site': site_stats,
        'cold': summarize(cold_meds),
        'warm': summarize(warm_meds)
    }

# print summary for inspection
print("Mode summary (median_of_site_medians, q1, q3, n_sites):")
for mode, s in mode_summary.items():
    print(f"\nMODE: {mode}")
    print("  COLD :", s['cold'])
    print("  WARM :", s['warm'])

# plotting: grouped bar for modes, with asymmetric IQR errorbars (原始总览图)
modes_plot = [m for m in modes if (mode_summary[m]['cold']['n_sites']>0 or mode_summary[m]['warm']['n_sites']>0)]
if not modes_plot:
    raise SystemExit("No modes with data to plot")

cold_heights = [mode_summary[m]['cold']['median'] for m in modes_plot]
warm_heights = [mode_summary[m]['warm']['median'] for m in modes_plot]

# compute asymmetric yerr = [[median - q1], [q3 - median]]
cold_yerr_lower = [mode_summary[m]['cold']['median'] - mode_summary[m]['cold']['q1'] if not np.isnan(mode_summary[m]['cold']['median']) else 0 for m in modes_plot]
cold_yerr_upper = [mode_summary[m]['cold']['q3'] - mode_summary[m]['cold']['median'] if not np.isnan(mode_summary[m]['cold']['median']) else 0 for m in modes_plot]
warm_yerr_lower = [mode_summary[m]['warm']['median'] - mode_summary[m]['warm']['q1'] if not np.isnan(mode_summary[m]['warm']['median']) else 0 for m in modes_plot]
warm_yerr_upper = [mode_summary[m]['warm']['q3'] - mode_summary[m]['warm']['median'] if not np.isnan(mode_summary[m]['warm']['median']) else 0 for m in modes_plot]

x = np.arange(len(modes_plot))
width = 0.35

fig, ax = plt.subplots(figsize=(max(10, len(modes_plot)*2.0), 6))
bars1 = ax.bar(x - width/2, cold_heights, width, label='Cold (median of site-medians)',
               yerr=[cold_yerr_lower, cold_yerr_upper], capsize=6)
bars2 = ax.bar(x + width/2, warm_heights, width, label='Warm (median of site-medians)',
               yerr=[warm_yerr_lower, warm_yerr_upper], capsize=6)

# annotate sample sizes (n_sites)
for i, m in enumerate(modes_plot):
    cold_n = mode_summary[m]['cold']['n_sites']
    warm_n = mode_summary[m]['warm']['n_sites']
    ax.text(x[i] - width/2, (cold_heights[i] if not np.isnan(cold_heights[i]) else 0) + 1,
            f"n={cold_n}", ha='center', va='bottom', fontsize=8)
    ax.text(x[i] + width/2, (warm_heights[i] if not np.isnan(warm_heights[i]) else 0) + 1,
            f"n={warm_n}", ha='center', va='bottom', fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(modes_plot, rotation=25, ha='right')
ax.set_ylabel("Latency (ms) — median of per-site medians")
ax.set_title("Median DNS Lookup Latency by Mode (cold vs warm)")
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()
out_png = os.path.join(OUT_DIR, "modes_dns_cold_warm_improved.png")
plt.savefig(out_png, dpi=150)
plt.close(fig)
print("Saved improved plot to", out_png)

# ==========================
# 新增：为每个 mode 生成按 sites 顺序排列的 per-site 图
# ==========================
popular_sites = read_site_list(POPULAR_CFG, max_items=POPULAR_N)
unpopular_sites = read_site_list(UNPOPULAR_CFG, max_items=UNPOPULAR_N)

for mode in modes:
    site_stats = mode_summary[mode]['per_site']
    if not site_stats:
        print(f"Mode {mode} has no per-site data, skip per-site plot.")
        continue

    # order: popular (in file order, first POPULAR_N), then unpopular (first UNPOPULAR_N), then remaining sites
    ordered = []
    for s in popular_sites:
        if s in site_stats and s not in ordered:
            ordered.append(s)
    for s in unpopular_sites:
        if s in site_stats and s not in ordered:
            ordered.append(s)
    # append any remaining sites (keeps deterministic order by sorted())
    for s in sorted(site_stats.keys()):
        if s not in ordered:
            ordered.append(s)

    # build arrays for plotting (use NaN->np.nan, matplotlib will handle by leaving gaps; but we'll replace NaN with 0 to draw bars and mark n=0)
    cold_vals = [site_stats[s]['cold_med'] if s in site_stats else np.nan for s in ordered]
    warm_vals = [site_stats[s]['warm_med'] if s in site_stats else np.nan for s in ordered]
    cold_ns = [site_stats[s]['cold_n'] if s in site_stats else 0 for s in ordered]
    warm_ns = [site_stats[s]['warm_n'] if s in site_stats else 0 for s in ordered]

    # for plotting, convert NaN to 0 so bars show; we will annotate n=0 to indicate missing
    cold_plot = [0 if np.isnan(v) else v for v in cold_vals]
    warm_plot = [0 if np.isnan(v) else v for v in warm_vals]

    x = np.arange(len(ordered))
    width = 0.35
    fig, ax = plt.subplots(figsize=(max(12, len(ordered)*0.6), 6))

    bars_cold = ax.bar(x - width/2, cold_plot, width, label='Cold (per-site median)')
    bars_warm = ax.bar(x + width/2, warm_plot, width, label='Warm (per-site median)')

    # annotate sample sizes under the bars
    for i, s in enumerate(ordered):
        ax.text(x[i] - width/2, (cold_plot[i] if cold_plot[i] > 0 else 0) + 1,
                f"n={cold_ns[i]}", ha='center', va='bottom', fontsize=7)
        ax.text(x[i] + width/2, (warm_plot[i] if warm_plot[i] > 0 else 0) + 1,
                f"n={warm_ns[i]}", ha='center', va='bottom', fontsize=7)
        # indicate missing data visibly (if n==0), by shading bar background with hatch
        if cold_ns[i] == 0:
            bars_cold[i].set_hatch('//')
            bars_cold[i].set_alpha(0.4)
        if warm_ns[i] == 0:
            bars_warm[i].set_hatch('\\')
            bars_warm[i].set_alpha(0.4)

    ax.set_xticks(x)
    ax.set_xticklabels(ordered, rotation=25, ha='right', fontsize=8)
    ax.set_ylabel("Latency (ms) — per-site median")
    ax.set_title(f"Per-site DNS Lookup Median for mode '{mode}'\nPopular (top {POPULAR_N}) first, Unpopular (top {UNPOPULAR_N}) next")
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

    out_png = os.path.join(OUT_DIR, f"{mode}_per_site_ordered.png")
    plt.savefig(out_png, dpi=150)
    plt.close(fig)
    print("Saved per-site ordered plot for mode", mode, "->", out_png)
