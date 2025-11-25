#!/usr/bin/env python3
"""
CS740 DNS Performance Analysis — Complete Pipeline
Consolidates data → Computes stats → Generates figures
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# CONFIG
# ============================================================
RAW_DIR = "/home/claude/data/raw"
OUT_DATA = "/mnt/user-data/outputs/data_clean"
OUT_FIGS = "/mnt/user-data/outputs/figs"
os.makedirs(OUT_DATA, exist_ok=True)
os.makedirs(OUT_FIGS, exist_ok=True)

DNS_HEADER = ["timestamp", "mode", "site", "trial", "ms", "status"]
WEB_HEADER = ["timestamp", "mode", "site", "ttfb_ms", "dom_ms", "load_ms", "status"]

# ============================================================
# CHUNK 2: DATA CONSOLIDATION
# ============================================================
print("=" * 60)
print("CHUNK 2: Consolidating raw data...")
print("=" * 60)

def load_dns(filename, mode_override=None, cache_state="cold"):
    """Load DNS CSV, handle with/without headers."""
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        print(f"  [SKIP] {filename} not found")
        return pd.DataFrame()
    
    # Check if has header
    with open(path) as f:
        first = f.readline()
    has_header = first.startswith("iso") or first.startswith("timestamp")
    
    if has_header:
        df = pd.read_csv(path)
        df.columns = DNS_HEADER[:len(df.columns)]
    else:
        df = pd.read_csv(path, header=None, names=DNS_HEADER)
    
    if mode_override:
        df["mode"] = mode_override
    df["cache_state"] = cache_state
    df = df[df["status"] == "ok"]
    df["ms"] = pd.to_numeric(df["ms"], errors="coerce")
    print(f"  [OK] {filename}: {len(df)} rows")
    return df

def load_web(filename, mode_override=None):
    """Load web CSV."""
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        print(f"  [SKIP] {filename} not found")
        return pd.DataFrame()
    
    with open(path) as f:
        first = f.readline()
    has_header = first.startswith("iso") or first.startswith("ts")
    
    if has_header:
        df = pd.read_csv(path)
        df.columns = WEB_HEADER[:len(df.columns)]
    else:
        df = pd.read_csv(path, header=None, names=WEB_HEADER)
    
    if mode_override:
        df["mode"] = mode_override
    df = df[df["status"] == "ok"]
    for col in ["ttfb_ms", "dom_ms", "load_ms"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"  [OK] {filename}: {len(df)} rows")
    return df

# Load all DNS data
dns_frames = [
    load_dns("dns_public_cold.csv", "public_udp", "cold"),
    load_dns("dns_public_warm.csv", "public_udp", "warm"),
    load_dns("dns_isp.csv", "isp_udp", "cold"),  # ISP data treated as cold
    load_dns("dns_dot_cold.csv", "dot", "cold"),
    load_dns("dns_dot_warm.csv", "dot", "warm"),
    load_dns("dns_doh.csv", "doh", "cold"),
]
dns_all = pd.concat([df for df in dns_frames if len(df) > 0], ignore_index=True)

# Load all web data
web_frames = [
    load_web("web_public.csv", "public_udp"),
    load_web("web_isp.csv", "isp_udp"),
    load_web("web_dot.csv", "dot"),
    load_web("web_doh.csv", "doh"),
]
web_all = pd.concat([df for df in web_frames if len(df) > 0], ignore_index=True)

# Save consolidated
dns_all.to_csv(f"{OUT_DATA}/dns_all.csv", index=False)
web_all.to_csv(f"{OUT_DATA}/web_all.csv", index=False)
print(f"\n  Saved: dns_all.csv ({len(dns_all)} rows), web_all.csv ({len(web_all)} rows)")

# ============================================================
# CHUNK 3: CORE ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("CHUNK 3: Computing statistics...")
print("=" * 60)

# --- DNS Statistics ---
# Filter out 0ms (cached) for cold analysis, keep for warm
dns_cold = dns_all[(dns_all["cache_state"] == "cold") & (dns_all["ms"] > 0)]
dns_warm = dns_all[dns_all["cache_state"] == "warm"]

dns_summary = []
for mode in ["public_udp", "isp_udp", "dot", "doh"]:
    cold_data = dns_cold[dns_cold["mode"] == mode]["ms"]
    warm_data = dns_warm[dns_warm["mode"] == mode]["ms"]
    
    cold_med = cold_data.median() if len(cold_data) > 0 else np.nan
    warm_med = warm_data.median() if len(warm_data) > 0 else np.nan
    improvement = ((cold_med - warm_med) / cold_med * 100) if cold_med > 0 else np.nan
    
    dns_summary.append({
        "mode": mode,
        "cold_median_ms": round(cold_med, 1) if not np.isnan(cold_med) else "N/A",
        "warm_median_ms": round(warm_med, 1) if not np.isnan(warm_med) else "N/A",
        "cold_mean_ms": round(cold_data.mean(), 1) if len(cold_data) > 0 else "N/A",
        "cold_std_ms": round(cold_data.std(), 1) if len(cold_data) > 0 else "N/A",
        "samples_cold": len(cold_data),
        "samples_warm": len(warm_data),
        "improvement_%": round(improvement, 1) if not np.isnan(improvement) else "N/A"
    })

dns_summary_df = pd.DataFrame(dns_summary)
print("\n📊 DNS Latency Summary:")
print(dns_summary_df.to_string(index=False))

# --- Web Statistics ---
web_summary = []
for mode in ["public_udp", "isp_udp", "dot", "doh"]:
    mode_data = web_all[web_all["mode"] == mode]
    if len(mode_data) == 0:
        continue
    web_summary.append({
        "mode": mode,
        "ttfb_median_ms": round(mode_data["ttfb_ms"].median(), 0),
        "dom_median_ms": round(mode_data["dom_ms"].median(), 0),
        "load_median_ms": round(mode_data["load_ms"].median(), 0),
        "samples": len(mode_data)
    })

web_summary_df = pd.DataFrame(web_summary)
print("\n📊 Page Load Summary:")
print(web_summary_df.to_string(index=False))

# --- Encrypted vs Unencrypted Comparison ---
print("\n📊 Encrypted vs Unencrypted DNS:")
unenc = dns_cold[dns_cold["mode"].isin(["public_udp", "isp_udp"])]["ms"]
enc = dns_cold[dns_cold["mode"].isin(["dot", "doh"])]["ms"]
print(f"  Unencrypted (public+isp) median: {unenc.median():.1f} ms")
print(f"  Encrypted (DoT+DoH) median:      {enc.median():.1f} ms")
print(f"  Overhead: {enc.median() - unenc.median():.1f} ms ({(enc.median()/unenc.median()-1)*100:.1f}%)")

# Save summaries
dns_summary_df.to_csv(f"{OUT_DATA}/dns_summary.csv", index=False)
web_summary_df.to_csv(f"{OUT_DATA}/web_summary.csv", index=False)
print(f"\n  Saved: dns_summary.csv, web_summary.csv")

# ============================================================
# CHUNK 4: VISUALIZATIONS
# ============================================================
print("\n" + "=" * 60)
print("CHUNK 4: Generating figures...")
print("=" * 60)

plt.style.use('seaborn-v0_8-whitegrid')
COLORS = {'public_udp': '#2ecc71', 'isp_udp': '#3498db', 'dot': '#9b59b6', 'doh': '#e74c3c'}
LABELS = {'public_udp': 'Public UDP', 'isp_udp': 'ISP UDP', 'dot': 'DoT', 'doh': 'DoH'}

# --- Figure 1: DNS Latency by Mode (Cold) ---
fig1, ax1 = plt.subplots(figsize=(8, 5))
modes = ["public_udp", "isp_udp", "dot", "doh"]
medians = [dns_cold[dns_cold["mode"] == m]["ms"].median() for m in modes]
stds = [dns_cold[dns_cold["mode"] == m]["ms"].std() for m in modes]

bars = ax1.bar([LABELS[m] for m in modes], medians, color=[COLORS[m] for m in modes], 
               yerr=stds, capsize=5, edgecolor='black', linewidth=1.2)
ax1.set_ylabel("DNS Latency (ms)", fontsize=12)
ax1.set_xlabel("DNS Mode", fontsize=12)
ax1.set_title("DNS Resolution Time by Mode (Cold Cache)", fontsize=14, fontweight='bold')
ax1.set_ylim(0, max(medians) * 1.3)
for bar, med in zip(bars, medians):
    ax1.annotate(f'{med:.0f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                 ha='center', va='bottom', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUT_FIGS}/fig1_dns_latency_by_mode.png", dpi=150)
print("  [OK] fig1_dns_latency_by_mode.png")

# --- Figure 2: Cold vs Warm Comparison ---
fig2, ax2 = plt.subplots(figsize=(8, 5))
x = np.arange(len(modes))
width = 0.35

cold_meds = [dns_cold[dns_cold["mode"] == m]["ms"].median() for m in modes]
warm_meds = []
for m in modes:
    w = dns_warm[dns_warm["mode"] == m]["ms"]
    warm_meds.append(w.median() if len(w) > 0 else 0)

bars1 = ax2.bar(x - width/2, cold_meds, width, label='Cold', color='#e74c3c', edgecolor='black')
bars2 = ax2.bar(x + width/2, warm_meds, width, label='Warm', color='#2ecc71', edgecolor='black')

ax2.set_ylabel("DNS Latency (ms)", fontsize=12)
ax2.set_xlabel("DNS Mode", fontsize=12)
ax2.set_title("Cold vs Warm DNS Lookup Time", fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([LABELS[m] for m in modes])
ax2.legend()
ax2.set_ylim(0, max(cold_meds) * 1.2)
plt.tight_layout()
plt.savefig(f"{OUT_FIGS}/fig2_cold_vs_warm.png", dpi=150)
print("  [OK] fig2_cold_vs_warm.png")

# --- Figure 3: Page Load Breakdown ---
fig3, ax3 = plt.subplots(figsize=(9, 5))
web_modes = web_summary_df["mode"].tolist()
ttfb = web_summary_df["ttfb_median_ms"].tolist()
dom_only = (web_summary_df["dom_median_ms"] - web_summary_df["ttfb_median_ms"]).tolist()
load_only = (web_summary_df["load_median_ms"] - web_summary_df["dom_median_ms"]).tolist()

x = np.arange(len(web_modes))
ax3.bar(x, ttfb, label='TTFB', color='#3498db', edgecolor='black')
ax3.bar(x, dom_only, bottom=ttfb, label='DOM Load', color='#f39c12', edgecolor='black')
ax3.bar(x, load_only, bottom=[t+d for t,d in zip(ttfb, dom_only)], label='Full Load', color='#e74c3c', edgecolor='black')

ax3.set_ylabel("Time (ms)", fontsize=12)
ax3.set_xlabel("DNS Mode", fontsize=12)
ax3.set_title("Page Load Time Breakdown by DNS Mode", fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels([LABELS[m] for m in web_modes])
ax3.legend(loc='upper right')
plt.tight_layout()
plt.savefig(f"{OUT_FIGS}/fig3_pageload_breakdown.png", dpi=150)
print("  [OK] fig3_pageload_breakdown.png")

# --- Figure 4: DNS Box Plot ---
fig4, ax4 = plt.subplots(figsize=(9, 5))
box_data = [dns_cold[dns_cold["mode"] == m]["ms"].dropna().values for m in modes]
bp = ax4.boxplot(box_data, labels=[LABELS[m] for m in modes], patch_artist=True)
for patch, mode in zip(bp['boxes'], modes):
    patch.set_facecolor(COLORS[mode])
    patch.set_alpha(0.7)
ax4.set_ylabel("DNS Latency (ms)", fontsize=12)
ax4.set_xlabel("DNS Mode", fontsize=12)
ax4.set_title("DNS Latency Distribution (Cold Cache)", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUT_FIGS}/fig4_dns_boxplot.png", dpi=150)
print("  [OK] fig4_dns_boxplot.png")

# --- Figure 5: Encrypted vs Unencrypted Summary ---
fig5, ax5 = plt.subplots(figsize=(6, 5))
categories = ['Unencrypted\n(Public+ISP)', 'Encrypted\n(DoT+DoH)']
values = [unenc.median(), enc.median()]
colors = ['#2ecc71', '#9b59b6']
bars = ax5.bar(categories, values, color=colors, edgecolor='black', linewidth=1.5)
ax5.set_ylabel("Median DNS Latency (ms)", fontsize=12)
ax5.set_title("Encrypted vs Unencrypted DNS", fontsize=14, fontweight='bold')
for bar, val in zip(bars, values):
    ax5.annotate(f'{val:.1f} ms', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                 ha='center', va='bottom', fontsize=12, fontweight='bold')
ax5.set_ylim(0, max(values) * 1.25)
plt.tight_layout()
plt.savefig(f"{OUT_FIGS}/fig5_encrypted_comparison.png", dpi=150)
print("  [OK] fig5_encrypted_comparison.png")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("✅ COMPLETE!")
print("=" * 60)
print(f"""
📁 Output Files:
   {OUT_DATA}/dns_all.csv
   {OUT_DATA}/web_all.csv
   {OUT_DATA}/dns_summary.csv
   {OUT_DATA}/web_summary.csv
   
📊 Figures:
   {OUT_FIGS}/fig1_dns_latency_by_mode.png
   {OUT_FIGS}/fig2_cold_vs_warm.png
   {OUT_FIGS}/fig3_pageload_breakdown.png
   {OUT_FIGS}/fig4_dns_boxplot.png
   {OUT_FIGS}/fig5_encrypted_comparison.png

📈 Key Findings:
   • Public UDP median: {dns_cold[dns_cold["mode"]=="public_udp"]["ms"].median():.1f} ms
   • ISP UDP median: {dns_cold[dns_cold["mode"]=="isp_udp"]["ms"].median():.1f} ms  
   • DoT median: {dns_cold[dns_cold["mode"]=="dot"]["ms"].median():.1f} ms
   • DoH median: {dns_cold[dns_cold["mode"]=="doh"]["ms"].median():.1f} ms
   • Encryption overhead: ~{enc.median() - unenc.median():.1f} ms
""")
