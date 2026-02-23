# WEMS Unified Relay Runbook

## Service
- Name: `wems-unified-relay.service`
- Scope: user systemd service
- Script: `scripts/wems_unified_relay.py`
- Config: `config/wems_alert_config.json`

## Install
```bash
bash scripts/install_wems_unified_relay_service.sh
```

## Operate
```bash
systemctl --user status wems-unified-relay.service
systemctl --user restart wems-unified-relay.service
systemctl --user stop wems-unified-relay.service
journalctl --user -u wems-unified-relay.service -f
```

## Logs
- File log: `reports/wems_unified_relay.service.log`

## Config Tuning
Edit:
- `config/wems_alert_config.json`

Key knobs:
- `radii_miles.*`
- `thresholds.*`
- `enabled_sources.*`
- `source_poll_seconds.*`
- `relay.webhook_url`

After config edits:
```bash
systemctl --user restart wems-unified-relay.service
```
