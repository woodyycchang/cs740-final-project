# CS740 Final Project — DNS Profiles vs Page Load (Cold vs Warm)

This repo measures DNS resolution time and full page load time across resolver profiles:
- **public_udp**: Public resolvers over UDP (e.g., 8.8.8.8, 1.1.1.1)
- **dot**: DNS-over-TLS (forwarded locally)
- **doh**: DNS-over-HTTPS (forwarded locally)
- **local_cache**: Local recursive cache (e.g., Unbound)

Matrix: 10 sites × 4 profiles × 2 cache states (cold/warm) × N trials → CSV + plots.

## Quick start
```bash
# On both client & resolver VMs (Ubuntu 22.04+)
sudo apt update && sudo apt install -y jq curl bind9-dnsutils knot-dnsutils \
  unbound stubby cloudflared chromium-browser nodejs npm ntpdate tcpdump

# Keep clocks tight
sudo ntpdate pool.ntp.org
```

See `scripts/00_setup.sh` and `scripts/40_run_all.sh`.
