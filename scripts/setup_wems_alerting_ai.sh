#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/bonsaihorn/Projects/wems-mcp-server"
N8N_ENV="${HOME}/.secrets/n8n.env"
GITEA_TOKEN_FILE="${HOME}/.secrets/gitea-helios-token.txt"
WF_JSON="${ROOT}/integrations/n8n/workflows/wems_unified_ingest_v2_6_0.json"

if [[ ! -f "$N8N_ENV" ]]; then
  echo "Missing $N8N_ENV"
  exit 1
fi
if [[ ! -f "$GITEA_TOKEN_FILE" ]]; then
  echo "Missing $GITEA_TOKEN_FILE"
  exit 1
fi

# 1) Install/start relay service
bash "${ROOT}/scripts/install_wems_unified_relay_service.sh"

# 2) Upsert + activate n8n workflow with token injected
python3 - <<'PY'
import json, pathlib, requests

env = {}
for line in pathlib.Path.home().joinpath('.secrets/n8n.env').read_text().splitlines():
    if '=' in line:
        k,v = line.split('=',1)
        env[k]=v

base = env['N8N_URL'].rstrip('/')
headers = {'X-N8N-API-KEY': env['N8N_API_KEY'], 'Content-Type': 'application/json'}
gtok = pathlib.Path.home().joinpath('.secrets/gitea-helios-token.txt').read_text().strip()

wf = json.loads(pathlib.Path('/home/bonsaihorn/Projects/wems-mcp-server/integrations/n8n/workflows/wems_unified_ingest_v2_6_0.json').read_text())
for n in wf['nodes']:
    if n.get('name') == 'Post to Tracker':
        for hp in n['parameters']['headerParameters']['parameters']:
            if hp['name'] == 'Authorization':
                hp['value'] = f'token {gtok}'
payload = {k:wf[k] for k in ['name','nodes','connections','settings'] if k in wf}

lst = requests.get(base+'/api/v1/workflows', headers=headers, params={'limit':200}, timeout=30)
lst.raise_for_status()
items = lst.json().get('data',[])
wid = next((x['id'] for x in items if x.get('name') == payload['name']), None)
if wid:
    r = requests.put(base+f'/api/v1/workflows/{wid}', headers=headers, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
else:
    r = requests.post(base+'/api/v1/workflows', headers=headers, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    wid = r.json()['id']

act = requests.post(base+f'/api/v1/workflows/{wid}/activate', headers=headers, timeout=30)
act.raise_for_status()
print('workflow_active', wid)
PY

echo "WEMS AI alerting setup complete."
