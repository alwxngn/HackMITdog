# Phone voice walk / take-home runbook

## Where does the bridge run?

`robot/dimos_command_bridge.py` runs **outside** DimOS as a separate process,
normally on the same computer as DimOS. It listens to the Lantern bus and runs
the public `dimos mcp call` command. DimOS itself remains responsible for the
robot hardware and safety controller.

```text
Phone → STT → cloud voice service → bus → orchestrator
      → command bridge → DimOS MCP skill → Go2
```

## One-time setup

```bash
cd cloud
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r ../voice/requirements.txt -r ../orchestrator/requirements.txt
cd web && npm install
cd ../..
```

## Mock run

Start these terminals in order.

### Terminal 1: cloud API

```bash
export LANTERN_ORCH_PUBLISH_URL=http://127.0.0.1:9000
cd cloud
source .venv/bin/activate
cd server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

`LANTERN_ORCH_PUBLISH_URL` is the cloud-to-orchestrator transcript route.

### Terminal 2: portal

```bash
cd cloud/web
npm run dev
```

Open `http://127.0.0.1:5173`.

### Terminal 3: orchestrator, bus, and mock robot

```bash
cd orchestrator
source .venv/bin/activate
python run_spine.py --scenario calm --hub-port 9000
```

Pair the phone, tap **Start Lantern**, then tap **Speak to Lantern** and say:

```text
Take me for a walk
```

Later say `Take me home`, then answer `Yes` when Lantern asks for confirmation.
The expected state flow is:

```text
IDLE → WALK → CONFIRM_HOME → GUIDE_HOME → IDLE
```

## Real DimOS / Go2 run

Run the cloud API and portal as above. Start a bus hub on port `9000`, then
start DimOS on the Go2 computer:

```bash
cd /Users/laminegueye/Desktop/repos/HackMITdog
source cloud/.venv/bin/activate
python bus/run_hub.py --port 9000
```

Leave that bus-hub terminal running. In a separate terminal, start DimOS:

```bash
source /Users/laminegueye/dimensional-applications/.venv/bin/activate
cd /Users/laminegueye/Desktop/repos/HackMITdog
VIRTUAL_ENV=/Users/laminegueye/dimensional-applications/.venv uv pip install -e .
dimos run hackmitdog.aegis-breadcrumb-agentic \
  --robot-ip 192.168.12.1 \
  --unitree-aes-128-key "$UNITREE_AES_128_KEY" \
  --model openai:muse-spark-1.3
```

Verify the DimOS tools:

```bash
dimos mcp status
dimos mcp list-tools
```

Then, in another terminal on the same computer, start the bridge:

```bash
cd /Users/laminegueye/Desktop/repos/HackMITdog
source /Users/laminegueye/dimensional-applications/.venv/bin/activate
python robot/dimos_command_bridge.py \
  --bus-url ws://127.0.0.1:9000/ws \
  --dimos-bin dimos
```

The bridge maps commands like this:

| Lantern command | DimOS calls |
|---|---|
| `follow_person` | `start_breadcrumb_recording`, then `follow_person` |
| `guide_home` | `stop_person_follow`, then `take_me_home` |
| `stop` | `stop_person_follow` |

Do not run `MockRobot` and the real robot consumer at the same time. The
current `run_spine.py` starts `MockRobot`, so use a bus-hub process without the
mock consumer for hardware.

## Phone over HTTPS

Phones cannot use the laptop's `localhost`. Tunnel Vite:

```bash
cloudflared tunnel --protocol http2 --url http://127.0.0.1:5173
```

Put the generated URL in `cloud/web/.env.local` and restart Vite:

```dotenv
VITE_PUBLIC_ORIGIN=https://YOUR-SUBDOMAIN.trycloudflare.com
```

Open the HTTPS portal URL, create the session there, and scan its pairing QR.

## Troubleshooting and verification

```bash
echo "$LANTERN_ORCH_PUBLISH_URL"
curl http://127.0.0.1:9000/
node --check voice/static/phone.js
PYTHONPATH=robot cloud/.venv/bin/python -m unittest discover -s robot/tests -v
cloud/.venv/bin/python -m unittest discover -s orchestrator/tests -v
cloud/.venv/bin/python -m unittest discover -s voice/tests -v
npm --prefix cloud/web run build
```

The orchestrator log should show `transcript`, then `command`. If DimOS tools
are missing, restart `hackmitdog.aegis-breadcrumb-agentic` and run
`dimos mcp list-tools` from the same virtual environment as the bridge.
