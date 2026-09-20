#!/bin/zsh

# Open the live Lantern mapping stack in separate macOS Terminal windows.
# Run from the repository root or double-click this file in Finder.
# Export UNITREE_AES_128_KEY before launching for the real Go2.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ -z "${UNITREE_AES_128_KEY:-}" ]]; then
  echo "UNITREE_AES_128_KEY is not exported."
  echo "Run: export UNITREE_AES_128_KEY='your-key'"
  exit 1
fi

ROOT_Q=${(q)ROOT}

osascript <<EOF
tell application "Terminal"
  activate
  do script "cd ${ROOT_Q}; source cloud/.venv/bin/activate; python bus/run_hub.py --port 9000"
  delay 1
  do script "cd ${ROOT_Q}; export LANTERN_ORCH_PUBLISH_URL=http://127.0.0.1:9000; export MAP_SCAN_MODE=live; source cloud/.venv/bin/activate; cd cloud/server; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
  delay 2
  do script "cd ${ROOT_Q}/cloud/web; npm run dev"
  delay 2
  do script "cd ${ROOT_Q}; source /Users/laminegueye/dimensional-applications/.venv/bin/activate; dimos run hackmitdog.aegis-breadcrumb-agentic --robot-ip 192.168.12.1 --unitree-aes-128-key $UNITREE_AES_128_KEY --model openai:muse-spark-1.3"
  delay 3
  do script "cd ${ROOT_Q}; source /Users/laminegueye/dimensional-applications/.venv/bin/activate; python robot/dimos_map_bridge.py --bus-url ws://127.0.0.1:9000/ws --cloud-base http://127.0.0.1:8000 --artifact-dir ${ROOT_Q}/artifacts/maps --artifact-base http://127.0.0.1:8000/api/maps"
  delay 3
  do script "cd ${ROOT_Q}; source /Users/laminegueye/dimensional-applications/.venv/bin/activate; echo 'Human DimOS CLI. Try: dimos mcp status or dimos mcp list-tools'; exec zsh"
end tell
EOF
