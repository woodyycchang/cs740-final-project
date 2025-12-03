# boxplot_dns_cold_vs_warm.py
"""
Boxplot: DNS Lookup Time (or Page Load Time) cold vs warm per mode
- Each mode has two boxes: cold (blue), warm (orange)
- Shows data distribution (min, Q1, median, Q3, max, outliers)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------
# Paths & modes
# ---------------------------
DATA_DIR = "data_for_submission/pop_raw"  # 修改为你数据路径
OUT_DIR = "use_this_fig"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PNG = os.path.join(OUT_DIR, "boxplot_dns_cold_vs_warm.png")

MODES = ["public_udp", "doh", "dot", "local_cache"]

# ---------------------------
# Load data
# ---------------------------
def load_dns_data(directory, mode):
    """Return two lists: cold_ms_values, warm_ms_values"""
    cold_file = os.path.join(directory, f"{mode}_dns_cold.csv")
    warm_file = os.path.join(directory, f"{mode}_dns_warm.csv")

    cold_vals, warm_vals = [], []

    for f, is_cold in [(cold_file, True), (warm_file, False)]:
        if not os.path.exists(f):
            continue
        df = pd.read_csv(f)
        df.columns = [c.strip() for c in df.columns]
        df = df[df['status'].str.lower() == 'ok']
        df = df[df['ms'] > 0]

        if is_cold:
            cold_vals.extend(df[df['trial']==1]['ms'].tolist())
            warm_vals.extend(df[df['trial']>1]['ms'].tolist())
        else:
            warm_vals.extend(df['ms'].tolist())

    return cold_vals, warm_vals

# ---------------------------
# Aggregate data for plotting
# ---------------------------
all_data = []
labels = []
colors = []

for mode in MODES:
    cold_vals, warm_vals = load_dns_data(DATA_DIR, mode)
    all_data.extend([cold_vals, warm_vals])
    labels.extend([f"{mode}\nCold", f"{mode}\nWarm"])
    colors.extend(['#1f77b4', '#ff7f0e'])  # blue=cold, orange=warm

# ---------------------------
# Plot boxplot
# ---------------------------
plt.figure(figsize=(12,6))
bp = plt.boxplot(all_data, patch_artist=True, labels=labels, widths=0.6)


for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)


plt.ylabel("DNS Lookup Time (ms)")
plt.title("DNS Lookup Time: Cold vs Warm per Mode")
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=300)
plt.show()
print(f"Saved figure to {OUT_PNG}")
