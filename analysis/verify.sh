#!/usr/bin/env bash
set -euo pipefail

echo "=== Repo snapshot (tracked files on main) ===" > analysis/verification_report.txt
git fetch origin main >/dev/null 2>&1 || true
git ls-tree -r --name-only origin/main >> analysis/verification_report.txt 2>/dev/null || true

echo "" >> analysis/verification_report.txt
echo "=== Working tree status (untracked + modified) ===" >> analysis/verification_report.txt
git status --porcelain >> analysis/verification_report.txt

echo "" >> analysis/verification_report.txt
echo "=== Expected files present? ===" >> analysis/verification_report.txt
need=(
  "README.md"
  "config/sites.txt"
  "scripts/20_measure_dns.sh"
  "scripts/30_measure_pageload.js"
  "data/raw/dns_public_cold.csv"
  "data/raw/dns_public_warm.csv"
  "data/raw/dns_isp.csv"
  "data/raw/web_public.csv"
)
for f in "${need[@]}"; do
  if [ -f "$f" ]; then echo "[OK]   $f" >> analysis/verification_report.txt
  else echo "[MISS] $f" >> analysis/verification_report.txt; fi
done

echo "" >> analysis/verification_report.txt
echo "=== Optional (encrypted DNS & all-web) files ===" >> analysis/verification_report.txt
opt=(
  "data/raw/dns_dot_cold.csv"
  "data/raw/dns_dot_warm.csv"
  "data/raw/dns_doh.csv"
  "data/raw/web_isp.csv"
  "data/raw/web_dot.csv"
  "data/raw/web_doh.csv"
)
for f in "${opt[@]}"; do
  if [ -f "$f" ]; then echo "[OK]   $f" >> analysis/verification_report.txt
  else echo "[TODO] $f" >> analysis/verification_report.txt; fi
done

echo "" >> analysis/verification_report.txt
echo "=== Headers sanity (first line) ===" >> analysis/verification_report.txt
for f in data/raw/*.csv; do
  h="$(head -1 "$f" 2>/dev/null || true)"
  echo "$(printf '%-40s' "$f") | $h" >> analysis/verification_report.txt
done

echo "" >> analysis/verification_report.txt
echo "=== Row counts (per CSV) ===" >> analysis/verification_report.txt
for f in data/raw/*.csv; do
  c=$(wc -l < "$f" 2>/dev/null || echo 0)
  echo "$(printf '%-40s' "$f") | rows=$c" >> analysis/verification_report.txt
done

echo "" >> analysis/verification_report.txt
echo "=== Sites covered (from config/sites.txt) ===" >> analysis/verification_report.txt
nsites=$(wc -l < config/sites.txt 2>/dev/null || echo 0)
echo "sites.txt count: $nsites" >> analysis/verification_report.txt
echo "sites.txt preview:" >> analysis/verification_report.txt
sed -n '1,20p' config/sites.txt >> analysis/verification_report.txt

echo "" >> analysis/verification_report.txt
echo "=== Per-mode medians (DNS) ===" >> analysis/verification_report.txt
calc_med(){
  f="$1"; mode="$2"
  awk -F, 'NR>1 && $5!="NA"{a[$3]=a[$3] " " $5}
  END{
    for(s in a){
      n=split(a[s],x," ")
      # simple insertion sort for macOS awk
      for(i=1;i<=n;i++) for(j=i+1;j<=n;j++) if((x[i]+0)>(x[j]+0)){t=x[i];x[i]=x[j];x[j]=t}
      m=(n%2? x[(n+1)/2] : (x[int(n/2)]+x[int(n/2)+1])/2)
      printf "%-18s %-10s %6.1f\n", s, mode, m
    }
  }' "$f" 2>/dev/null | sort
}
[ -f data/raw/dns_public_cold.csv ] && calc_med data/raw/dns_public_cold.csv public_cold >> analysis/verification_report.txt
[ -f data/raw/dns_public_warm.csv ] && calc_med data/raw/dns_public_warm.csv public_warm >> analysis/verification_report.txt
[ -f data/raw/dns_isp.csv ]         && calc_med data/raw/dns_isp.csv         isp_udp     >> analysis/verification_report.txt
[ -f data/raw/dns_dot_cold.csv ]    && calc_med data/raw/dns_dot_cold.csv    dot_cold    >> analysis/verification_report.txt
[ -f data/raw/dns_dot_warm.csv ]    && calc_med data/raw/dns_dot_warm.csv    dot_warm    >> analysis/verification_report.txt
[ -f data/raw/dns_doh.csv ]         && calc_med data/raw/dns_doh.csv         doh         >> analysis/verification_report.txt

echo "" >> analysis/verification_report.txt
echo "=== Page-load availability (TTFB medians, if present) ===" >> analysis/verification_report.txt
calc_web(){
  f="$1"; mode="$2"
  awk -F, 'NR>1 && $7=="ok" && $4!="NA"{a[$3]=a[$3] " " $4}
  END{
    for(s in a){
      n=split(a[s],x," ")
      for(i=1;i<=n;i++) for(j=i+1;j<=n;j++) if((x[i]+0)>(x[j]+0)){t=x[i];x[i]=x[j];x[j]=t}
      m=(n%2? x[(n+1)/2] : (x[int(n/2)]+x[int(n/2)+1])/2)
      printf "%-18s %-10s %6.0f\n", s, mode, m
    }
  }' "$f" 2>/dev/null | sort
}
[ -f data/raw/web_public.csv ] && calc_web data/raw/web_public.csv web_public >> analysis/verification_report.txt
[ -f data/raw/web_isp.csv ]    && calc_web data/raw/web_isp.csv    web_isp    >> analysis/verification_report.txt
[ -f data/raw/web_dot.csv ]    && calc_web data/raw/web_dot.csv    web_dot    >> analysis/verification_report.txt
[ -f data/raw/web_doh.csv ]    && calc_web data/raw/web_doh.csv    web_doh    >> analysis/verification_report.txt

echo "" >> analysis/verification_report.txt
echo "=== Conclusion checklist ===" >> analysis/verification_report.txt
echo "- ISP vs Public DNS: $( [ -f data/raw/dns_isp.csv ] && echo DONE || echo MISSING )" >> analysis/verification_report.txt
echo "- Cold vs Warm (Public): $( [ -f data/raw/dns_public_cold.csv ] && [ -f data/raw/dns_public_warm.csv ] && echo DONE || echo MISSING )" >> analysis/verification_report.txt
echo "- Encrypted (DoT/DoH): $( { [ -f data/raw/dns_dot_cold.csv ] || [ -f data/raw/dns_doh.csv ]; } && echo PARTIAL/OK || echo MISSING )" >> analysis/verification_report.txt
echo "- Page-load data for at least one mode: $( [ -f data/raw/web_public.csv ] && echo DONE || echo MISSING )" >> analysis/verification_report.txt

echo "" >> analysis/verification_report.txt
echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> analysis/verification_report.txt

echo "Wrote analysis/verification_report.txt"
