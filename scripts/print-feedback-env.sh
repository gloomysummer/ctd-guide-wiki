#!/bin/sh
# Print the FEISHU_FEEDBACK value for the Cloudflare Pages project.
#
# The site needs one environment variable to write feedback into the Bitable.
# It is a single line so the whole thing is one paste, and it is read from the
# radar profile rather than retyped by hand — a mistyped app secret fails with
# an opaque 99991663 from Feishu instead of anything useful.
#
# Usage:
#   ./scripts/print-feedback-env.sh
#   ./scripts/print-feedback-env.sh <env-file> <table-id>
set -e

ENV_FILE="${1:-$HOME/.hermes-game-radar/profiles/eiraradar/.env}"
TABLE_ID="${2:-tblC667zWFpjQ0Tv}"

[ -f "$ENV_FILE" ] || { echo "missing env file: $ENV_FILE" >&2; exit 1; }

get() {
  /usr/bin/grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' '
}

APP_ID=$(get FEISHU_APP_ID)
APP_SECRET=$(get FEISHU_APP_SECRET)
APP_TOKEN=$(get FEISHU_BITABLE_APP_TOKEN)

[ -n "$APP_ID" ] && [ -n "$APP_SECRET" ] && [ -n "$APP_TOKEN" ] || {
  echo "one of FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_BITABLE_APP_TOKEN is missing in $ENV_FILE" >&2
  exit 1
}

echo "Key:   FEISHU_FEEDBACK"
printf 'Value: %s:%s:%s:%s\n' "$APP_ID" "$APP_SECRET" "$APP_TOKEN" "$TABLE_ID"
echo
echo "Paste that into Cloudflare Pages -> ctd-guide-wiki -> Settings ->"
echo "Variables and Secrets -> Add (type: Secret), then redeploy the project."
