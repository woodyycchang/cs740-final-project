# final_dns_summary_bar.py
"""
Final Summary: which DNS is balanced best?
- Compare average DNS lookup time vs page load time for each mode
- Blue = DNS lookup, Orange = Page Load
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------
# Paths & modes
# ---------------------------
DNS_DIR = "data_for_submission/pop_raw"  # DNS CSV files
WEB_DIR = "data_for_submission/pop_raw"  # Page load CSV files
OUT_DIR = "use_this_fig"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PNG = os.path.join(OUT_DIR, "dns_summary_bar.png")

MODES = ["public_udp", "doh", "dot", "local_cache"]

# ---------------------------
# Helpers
# ---------------------------
def load_dns_avg(directory, mode):
    """Return mean DNS lookup time (ms) for cold+warm"""
    cold_file = os.path.join(directory, f"{mode}_dns_cold.csv")
    warm_file = os.path.join(directory, f"{mode}_dns_warm.csv")
    vals = []

    for f, is_cold in [(cold_file, True), (warm_file, False)]:
        if not os.path.exists(f):
            continue
        df = pd.read_csv(f)
        df.columns = [c.strip() for c in df.columns]
        df = df[df['status'].str.lower()=='ok']
        df = df[df['ms']>0]

        if is_cold:
            vals.extend(df['ms'].tolist())
        else:
            vals.extend(df['ms'].tolist())
    return pd.Series(vals).mean() if vals else 0

def load_web_avg(directory, mode):
    """Return mean page load time (ms) for cold+warm"""
    cold_file = os.path.join(directory, f"{mode}_web_cold.csv")
    warm_file = os.path.join(directory, f"{mode}_web_warm.csv")
    vals = []

    for f, is_cold in [(cold_file, True), (warm_file, False)]:
        if not os.path.exists(f):
            continue
        df = pd.read_csv(f)
        df.columns = [c.strip() for c in df.columns]
        df = df[df['status'].str.lower()=='ok']
        df = df[df['load_ms']>0]

        vals.extend(df['load_ms'].tolist())
    return pd.Series(vals).mean() if vals else 0

# ---------------------------
# Aggregate
# ---------------------------
dns_means, web_means = [], []

for mode in MODES:
    dns_avg = load_dns_avg(DNS_DIR, mode)
    web_avg = load_web_avg(WEB_DIR, mode)
    dns_means.append(dns_avg)
    web_means.append(web_avg)
    print(f"{mode}: DNS={dns_avg:.2f} ms, Page Load={web_avg:.2f} ms")

# ---------------------------
# Plot
# ---------------------------
x = np.arange(len(MODES))
width = 0.35

plt.figure(figsize=(10,6))
bars_dns = plt.bar(x - width/2, dns_means, width, color='#1f77b4', label='DNS Lookup')
bars_web = plt.bar(x + width/2, web_means, width, color='#ff7f0e', label='Page Load')

# Add value labels
for bar in bars_dns + bars_web:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, height + 10, f'{height:.0f}', ha='center', va='bottom', fontsize=10)

plt.xticks(x, MODES, rotation=20)
plt.ylabel("Average Time (ms)")
plt.title("DNS Lookup & Page Load Time")
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=300)
plt.show()
print(f"Saved figure to {OUT_PNG}")
