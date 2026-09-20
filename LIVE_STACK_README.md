# Live stack launcher

`run_live_stack.command` is a macOS convenience launcher for the real Go2
mapping path. It opens separate Terminal windows so each process remains
visible and can be stopped independently.

## What it starts

```text
bus hub :9000
  ↓
cloud API :8000  ←  React/Vite :5173
  ↓
map_scan_request → map bridge → DimOS MCP → Go2
```

The final window is a human DimOS/MCP shell for commands such as
`dimos mcp status`, `dimos mcp list-tools`, and manual skill calls.

## Start it

From the repository root:

```bash
export UNITREE_AES_128_KEY='your-unitree-key'
./run_live_stack.command
```

The launcher expects `cloud/.venv`, `cloud/web/node_modules`, and the DimOS
environment at `/Users/laminegueye/dimensional-applications/.venv` to exist.
The Go2 is expected at `192.168.12.1`.

If the editable package is stale, refresh it first:

```bash
VIRTUAL_ENV=/Users/laminegueye/dimensional-applications/.venv uv pip install -e .
```

## Use the mapping flow

Open:

```text
http://127.0.0.1:5173/onboarding
```

Click **Start mapping**. The map bridge invokes DimOS `map_room`, writes the
PLY to `artifacts/maps/`, and sends `map_ready` back to the cloud API.

Manual verification from the human CLI window:

```bash
dimos mcp status
dimos mcp list-tools
dimos mcp call map_room --timeout 300 --json-args '{"room_id":"home","duration_s":30}'
```

## Important notes

- This launcher is macOS-specific and uses Terminal.app.
- It starts the bus hub, not the full orchestrator/mock spine, to avoid running
  `MockRobot` alongside a real Go2.
- The bridge and cloud API should share the filesystem for `artifacts/maps/`.
- Stop each process with `Ctrl-C` in its own Terminal window.

## Troubleshooting

The map bridge window should print:

```text
connected to Lantern bus at ws://127.0.0.1:9000/ws
```

After clicking **Start mapping**, it should print:

```text
starting DimOS map_room request=...
```

If that message does not appear, set this in `cloud/.env` and restart the API:

```dotenv
LANTERN_ORCH_PUBLISH_URL=http://127.0.0.1:9000
```
