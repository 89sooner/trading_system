#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import json
import shlex
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    print("{}")
    raise SystemExit(0)

if data.get("tool_name") != "Bash":
    print("{}")
    raise SystemExit(0)

command = data.get("tool_input", {}).get("command", "") or ""

# Existing explicit exception from settings.local.json
allowed_find_prefixes = [
    "TEAM=phase-4-react-19-typescript-sp find /tmp /home/roqkf -name"
]

try:
    tokens = shlex.split(command, posix=True)
except Exception:
    tokens = command.split()

for prefix in allowed_find_prefixes:
    if command.startswith(prefix):
        print("{}")
        raise SystemExit(0)

for i, tok in enumerate(tokens):
    if tok in {"grep", "egrep", "fgrep"}:
        if tok == "grep" and i > 0 and tokens[i - 1] == "git":
            continue
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Use rg instead of grep/egrep/fgrep. Use git grep only when searching tracked files."
            }
        }))
        raise SystemExit(0)

    if tok == "find":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Use fd or fdfind instead of find for normal repository exploration."
            }
        }))
        raise SystemExit(0)

print("{}")
PY