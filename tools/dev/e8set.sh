#!/bin/bash
# Change one Eternity setting in a running system through the daemon (so the change is validated,
# saved and broadcast like a Settings-window change), falling back to the settings file when the
# daemon is not up. No quotes needed on the VM side:
#   curl -fsS http://HOST:8790/tools/dev/e8set.sh | bash -s trust_level 2
set -u
KEY=${1:?key}; VAL=${2:?value}
python3 - "$KEY" "$VAL" <<'PY'
import json, os, sys
sys.path.insert(0, "/usr/lib/eternity/py")
key, raw = sys.argv[1], sys.argv[2]
try:
    val = json.loads(raw)
except ValueError:
    val = raw
try:
    from eternity import daemon as D
    print("daemon:", D.Client().call("settings.set", key=key, value=val))
except Exception as e:  # noqa: BLE001
    print("daemon call failed:", e)
    from eternity import settings as S
    cfg = S.load(); setattr(cfg, key, val); cfg.validate(); S.save(cfg)
    print("file:", key, "=", getattr(cfg, key))
PY
