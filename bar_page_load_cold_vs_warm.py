# bar_page_load_cold_vs_warm.py
"""
Page Load Time: Cold vs Warm per Mode
- Uses load_ms as metric
- Blue = Cold, Orange = Warm
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------
# Paths & modes
# ---------------------------
DATA_DIR = "data_for_submission/pop_raw"  # or whichever folder has web CSVs
OUT_DIR = "use_this_fig"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PNG = os.path.join(OUT_DIR, "page_load_cold_vs_warm_bar.png")

MODES = ["public_udp", "doh", "dot", "local_cache"]

# ---------------------------
# Load data
# ---------------------------
def load_web_data(directory, mode):
    """Return all load_ms values (cold + warm separate)"""
    cold_file = os.path.join(directory, f"{mode}_web_cold.csv")
    warm_file = os.path.join(directory, f"{mode}_web_warm.csv")

    cold_vals, warm_vals = [], []

    for f, is_cold in [(cold_file, True), (warm_file, False)]:
        if not os.path.exists(f):
            continue
        df = pd.read_csv(f)
        df.columns = [c.strip() for c in df.columns]
        df = df[df['status'].str.lower() == 'ok']
        df = df[df['load_ms'] > 0]

        if is_cold:
            cold_vals.extend(df['load_ms'].tolist())
        else:
            warm_vals.extend(df['load_ms'].tolist())

    return cold_vals, warm_vals

# ---------------------------
# Aggregate mean per mode
# ---------------------------
cold_means, warm_means = [], []

for mode in MODES:
    cold_vals, warm_vals = load_web_data(DATA_DIR, mode)
    cold_mean = pd.Series(cold_vals).mean() if cold_vals else 0
    warm_mean = pd.Series(warm_vals).mean() if warm_vals else 0

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

# Add value labels
for bar in bars_cold + bars_warm:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, height + 50, f'{height:.0f}', ha='center', va='bottom', fontsize=10)

plt.xticks(x, MODES, rotation=20)
plt.ylabel("Mean Page Load Time (ms)")
plt.title("Page Load Time: Cold vs Warm per Mode")
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=300)
plt.show()
print(f"Saved figure to {OUT_PNG}")
