# bar_dns_pop_vs_unpop_v2.py
"""
DNS Lookup Time: Popular vs Unpopular Sites per Mode
- Handles unpopular files with "_unpopular" suffix
- Bars show mean DNS lookup time
- Blue = popular, Orange = unpopular
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------
# Paths & modes
# ---------------------------
POP_DIR = "data_for_submission/pop_raw"
UNPOP_DIR = "data_for_submission/unpop_raw"
OUT_DIR = "use_this_fig"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PNG = os.path.join(OUT_DIR, "dns_lookup_pop_vs_unpop_bar.png")

MODES = ["public_udp", "doh", "dot", "local_cache"]

# ---------------------------
# Load data
# ---------------------------
def load_dns_data(directory, mode, unpopular=False):
    """Return all DNS lookup times (cold+warm combined)"""
    suffix = "_unpopular" if unpopular else ""
    cold_vals, warm_vals = [], []

    cold_file = os.path.join(directory, f"{mode}_dns_cold{suffix}.csv")
    warm_file = os.path.join(directory, f"{mode}_dns_warm{suffix}.csv")

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

    return cold_vals + warm_vals

# ---------------------------
# Aggregate mean per mode
# ---------------------------
pop_means, unpop_means = [], []

for mode in MODES:
    pop_vals = load_dns_data(POP_DIR, mode, unpopular=False)
    unpop_vals = load_dns_data(UNPOP_DIR, mode, unpopular=True)

    pop_mean = pd.Series(pop_vals).mean() if pop_vals else 0
    unpop_mean = pd.Series(unpop_vals).mean() if unpop_vals else 0

    pop_means.append(pop_mean)
    unpop_means.append(unpop_mean)

    print(f"{mode}: popular mean={pop_mean:.2f} ms, unpopular mean={unpop_mean:.2f} ms")

# ---------------------------
# Plot
# ---------------------------
x = np.arange(len(MODES))
width = 0.35

plt.figure(figsize=(10,6))
bars_pop = plt.bar(x - width/2, pop_means, width, color='#1f77b4', label='Popular')
bars_unpop = plt.bar(x + width/2, unpop_means, width, color='#ff7f0e', label='Unpopular')

# Add value labels
for bar in bars_pop + bars_unpop:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, height + 0.2, f'{height:.1f}', ha='center', va='bottom', fontsize=10)

plt.xticks(x, MODES, rotation=20)
plt.ylabel("Mean DNS lookup time (ms)")
plt.title("DNS Lookup Time: Popular vs Unpopular Sites")
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=300)
plt.show()
print(f"Saved figure to {OUT_PNG}")
