# CS740 Final Project — DNS Performance Analysis

## Overview
This project measures DNS resolution time and full page load time across resolver profiles:
- **public_udp**: Public resolvers over UDP (8.8.8.8, 1.1.1.1)
- **isp_udp**: ISP resolver over UDP
- **dot**: DNS-over-TLS (via Stubby)
- **doh**: DNS-over-HTTPS (via cloudflared)

**Matrix**: 10 sites × 4 modes × cold/warm cache × N trials

## Key Results

### DNS Latency (Cold Cache)
| Mode | Median (ms) | Mean (ms) | Std Dev |
|------|-------------|-----------|---------|
| ISP UDP | **31** | 32.2 | 3.8 |
| DoT | 36 | 46.7 | 41.7 |
| Public UDP | 40 | 46.8 | 17.2 |
| DoH | 43 | 66.2 | 72.0 |

**Finding**: ISP DNS is fastest (~23% faster than public resolvers). Encrypted DNS (DoT/DoH) adds minimal overhead (~0-7ms median) — aligns with Böttger et al. (2019) findings.

### Cold vs Warm Cache
- **Public UDP**: 40ms → 0ms (100% improvement with caching)
- **DoT**: 36ms → 39ms (no improvement — encrypted connections maintained)

### Page Load (Median)
| Mode | TTFB | DOM | Full Load |
|------|------|-----|-----------|
| DoH | 331ms | 723ms | 1070ms |
| Public UDP | 360ms | 874ms | 1278ms |
| ISP UDP | 469ms | 824ms | 1224ms |
| DoT | 510ms | 730ms | 1093ms |

**Finding**: DNS latency differences have limited impact on total page load time. DoH paradoxically shows faster page loads despite slightly higher DNS latency.

## Repository Structure
```
├── config/
│   ├── sites.txt          # 10 test sites
│   └── modes.yml          # DNS modes config
├── scripts/
│   ├── 00_setup.sh        # Environment setup
│   ├── 10_dns_profiles.sh # Mode switching guide
│   ├── 20_measure_dns.sh  # DNS measurement
│   ├── 30_measure_pageload.js  # Page load measurement
│   └── 40_run_all.sh      # Orchestration
├── data/
│   ├── raw/               # Raw measurements
│   └── clean/             # Consolidated CSVs
├── figs/                  # Generated figures
├── analysis/
│   └── cs740_analysis.py  # Analysis script
└── README.md
```

## Generated Outputs

### Data Files
- `data/clean/dns_all.csv` — Consolidated DNS measurements
- `data/clean/web_all.csv` — Consolidated page load measurements
- `data/clean/dns_summary.csv` — DNS statistics by mode
- `data/clean/web_summary.csv` — Page load statistics by mode

### Figures
1. `fig1_dns_latency_by_mode.png` — Bar chart of DNS latency
2. `fig2_cold_vs_warm.png` — Cold vs warm comparison
3. `fig3_pageload_breakdown.png` — TTFB/DOM/Load breakdown
4. `fig4_dns_boxplot.png` — DNS latency distribution
5. `fig5_encrypted_comparison.png` — Encrypted vs unencrypted

## Quick Start
```bash
# Run analysis on existing data
python3 analysis/cs740_analysis.py

# Or collect new data (requires CloudLab setup)
export RESOLVER_IP=<your-resolver-vm>
./scripts/40_run_all.sh
```

## References
1. Hounsel et al. "Can Encrypted DNS Be Fast?" PAM 2021
2. Böttger et al. "An Empirical Study of the Cost of DNS-over-HTTPS" IMC 2019
