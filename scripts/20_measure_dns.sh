#!/usr/bin/env bash
set -euo pipefail

site="$1"
resolver_in="${2:-127.0.0.1}"
mode="$3"
out="$4"
trials="${5:-5}"
mkdir -p "$(dirname "$out")"

# Write header if file does not exist
[[ -f "$out" ]] || echo "iso,mode,site,trial,ms,status" > "$out"

isodate() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

#
# --- Parse resolver and optional port ---
#
resolver_host="$resolver_in"
resolver_port="53"
declare -a port_arg=()

if [[ "$resolver_in" == *"#"* ]]; then
  resolver_host="${resolver_in%%#*}"
  resolver_port="${resolver_in##*#}"
  port_arg=(-p "$resolver_port")
fi

#
# --- Health Check for DoT/DoH (NEW) ---
#
health_check() {
  local test_site="example.com"
  local result

  if [[ "$mode" == "dot" ]]; then
    echo "[dot] Health check: dig @$resolver_host -p $resolver_port"
    result=$(dig +short "$test_site" @"$resolver_host" -p "$resolver_port" 2>/dev/null || true)
    [[ -z "$result" ]] && { echo "[ERROR] DoT resolver not responding."; return 1; }
  fi

  if [[ "$mode" == "doh" ]]; then
    echo "[doh] Health check: dig @$resolver_host -p $resolver_port"
    result=$(dig +short "$test_site" @"$resolver_host" -p "$resolver_port" 2>/dev/null || true)
    [[ -z "$result" ]] && { echo "[ERROR] DoH stub resolver not responding."; return 1; }
  fi

  return 0
}

# Only perform health check once per run
if ! health_check; then
  echo "[FATAL] Resolver $resolver_host:$resolver_port is not working (mode=$mode)"
  exit 2
fi

#
# --- Flush DNS cache (resolver-specific) ---
# (CloudLab: systemd-resolved only clears local cache.)
# We improve the logic to flush DoT/DoH stub too.
#
flush() {
  if [[ "${COLD:-}" != "1" ]]; then return; fi

  echo "[flush] Cold run: flushing DNS caches..."

  # Flush system cache if user set FLUSH_CMD
  if [[ -n "${FLUSH_CMD:-}" ]]; then
    if [[ "$FLUSH_CMD" == *"%s"* ]]; then
      printf -v _cmd "$FLUSH_CMD" "$site"
      eval "$_cmd" >/dev/null 2>&1 || true
    else
      eval "$FLUSH_CMD" >/dev/null 2>&1 || true
    fi
  fi

  # Extra flushing for DoT/DoH stub resolvers (NEW)
  if [[ "$mode" == "dot" ]]; then
    sudo systemctl restart stubby >/dev/null 2>&1 || true
  elif [[ "$mode" == "doh" ]]; then
    sudo systemctl restart cloudflared >/dev/null 2>&1 || true
  fi

  sleep 0.3  # give resolver some time to restart
}

#
# --- Actual DNS timing using dig ---
#
dns_time() {
  dig +tries=1 +time=5 +stats A "$site" @"$resolver_host" \
      ${port_arg+"${port_arg[@]}"} 2>/dev/null \
    | awk '/Query time/ {print $4}'
}

#
# --- Main trials loop ---
#
for t in $(seq 1 "$trials"); do
  flush

  ms="$(dns_time)"
  status="ok"

  if [[ -z "${ms:-}" ]]; then
    ms="NA"
    status="no_response"
  elif ! [[ "$ms" =~ ^[0-9]+$ ]]; then
    status="bad_parse"
    ms="NA"
  fi

  echo "$(isodate),$mode,$site,$t,$ms,$status" >> "$out"
done
