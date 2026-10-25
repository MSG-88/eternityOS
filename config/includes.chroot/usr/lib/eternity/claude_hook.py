"""Body of /usr/lib/eternity/claude-hook (Claude Code PreToolUse): see that file."""
import json
import os
import sys

sys.path.insert(0, os.environ.get("ETERNITY_PYROOT", "/usr/lib/eternity/py"))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    try:
        from eternity import actions as A
        name = str(data.get("tool_name", ""))
        args = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
        audit = A.Audit()
        if A.escalates_privileges(name, args):
            audit.write(tool=name, args=args, decision="denied (privilege escalation)", ok=False, summary="sudo/pkexec refused",
                        via="claude-code-terminal", session=data.get("session_id"))
            print("Eternity never escalates privileges; ask the user to run this themselves.", file=sys.stderr)
            return 2
        audit.write(tool=name, args=args, decision="interactive", ok=True, summary=A.builtin_tool(name, args).description,
                    via="claude-code-terminal", session=data.get("session_id"))
    except Exception:  # noqa: BLE001
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
