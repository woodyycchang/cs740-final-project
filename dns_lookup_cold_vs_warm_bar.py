# simple_bar_dns_cold_vs_warm_with_labels.py

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------
# Paths & modes
# ---------------------------
DATA_DIRS = ["data_for_submission/pop_raw", "data_for_submission/unpop_raw"]
OUT_DIR = "use_this_fig"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PNG = os.path.join(OUT_DIR, "dns_lookup_cold_vs_warm_bar.png")

MODES = ["public_udp", "doh", "dot", "local_cache"]

# ---------------------------
# Load data
# ---------------------------
def load_dns_data(mode):
    cold_vals, warm_vals = [], []
    for d in DATA_DIRS:
        cold_file = os.path.join(d, f"{mode}_dns_cold.csv")
        warm_file = os.path.join(d, f"{mode}_dns_warm.csv")

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
# Aggregate
# ---------------------------
cold_means, warm_means = [], []
for mode in MODES:
    cold, warm = load_dns_data(mode)
    cold_mean = pd.Series(cold).mean() if cold else 0
    warm_mean = pd.Series(warm).mean() if warm else 0
    cold_means.append(cold_mean)
    warm_means.append(warm_mean)
    print(f"{mode}: cold mean={cold_mean:.2f} ms, warm mean={warm_mean:.2f} ms")

# ---------------------------
# Plot
# ---------------------------
x = np.arange(len(MODES))
width = 0.35

plt.figure(figsize=(10,6))
bars_cold = plt.bar(x - width/2, cold_means, width, color='#1f77b4', label='Cold')
bars_warm = plt.bar(x + width/2, warm_means, width, color='#ff7f0e', label='Warm')

# Add value labels on top
for bar in bars_cold + bars_warm:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, height + 0.2, f'{height:.1f}', ha='center', va='bottom', fontsize=10)

plt.xticks(x, MODES, rotation=20)
plt.ylabel("Mean DNS lookup time (ms)")
plt.title("DNS Lookup Time: Cold vs Warm")
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=300)
plt.show()
print(f"Saved figure to {OUT_PNG}")
