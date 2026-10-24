"""User settings for Eternity 08 ("How she shows up") and the secret store for API keys.

Settings live in ~/.config/eternity/settings.json (XDG). Keys never go into that file: they
are stored in the user's keyring through the Secret Service API (gnome-keyring, unlocked at
login by PAM) when it is available, otherwise in ~/.config/eternity/keys.json with mode 0600
and a note in the settings UI that the keyring is not running.
"""
import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass, field, fields
from typing import Dict, List, Optional

PROVIDERS = ("local", "anthropic", "openai")
VERBOSITY = ("brief", "normal", "detailed")
VOICES = ("off", "calm", "bright")
UNLOCK_METHODS = ("passphrase", "pin", "face", "voice")
# Unlock methods that actually work in this build (the others are shown as "coming later").
UNLOCK_AVAILABLE = ("passphrase", "pin")


def config_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "eternity")


def state_dir() -> str:
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "eternity")


@dataclass
class Settings:
    name: str = ""                       # how Eternity addresses the user
    provider: str = "local"              # local | anthropic | openai
    anthropic_model: str = "claude-sonnet-5-5"
    openai_model: str = "gpt-5.1"
    local_model: str = "auto"            # auto | default | small
    verbosity: str = "normal"            # brief | normal | detailed
    proactive: bool = True               # proactive suggestions on the home screen
    on_device_only: bool = True          # when true, cloud providers are refused
    telemetry: bool = False              # there is no telemetry; kept false and shown as such
    voice: str = "off"                   # off | calm | bright (no TTS engine is bundled yet)
    unlock_methods: List[str] = field(default_factory=lambda: ["passphrase"])
    trust_level: int = 0                 # 0: confirm every action, 1: auto-run safe actions
    first_run_done: bool = False
    agent_mode: bool = True              # the assistant may propose actions (tools)
    hotkey: str = "<Super>space"

    def validate(self) -> "Settings":
        if self.provider not in PROVIDERS:
            self.provider = "local"
        if self.verbosity not in VERBOSITY:
            self.verbosity = "normal"
        if self.voice not in VOICES:
            self.voice = "off"
        self.unlock_methods = [m for m in self.unlock_methods if m in UNLOCK_METHODS] or ["passphrase"]
        self.trust_level = max(0, min(1, int(self.trust_level)))
        self.telemetry = False
        if self.on_device_only and self.provider != "local":
            # "Keep everything on this device" wins over a cloud provider choice.
            self.provider = "local"
        return self

    def effective_provider(self) -> str:
        return "local" if self.on_device_only else self.provider


def _atomic_write(path: str, data: str, mode: int = 0o600) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def settings_path() -> str:
    return os.path.join(config_dir(), "settings.json")


def load() -> Settings:
    try:
        with open(settings_path(), encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return Settings().validate()
    known = {f.name for f in fields(Settings)}
    return Settings(**{k: v for k, v in raw.items() if k in known}).validate()


def save(s: Settings) -> None:
    s.validate()
    _atomic_write(settings_path(), json.dumps(asdict(s), indent=2, ensure_ascii=False) + "\n", 0o600)


# ----------------------------------------------------------------------------- secrets
class SecretStore:
    """API keys: Secret Service (keyring) when available, otherwise a 0600 file."""

    SERVICE = "eternity-08"

    def __init__(self, allow_keyring: bool = True, lazy: bool = False):
        self._ss = None
        self._tried = False
        self._allow = allow_keyring and os.environ.get("ETERNITY_NO_KEYRING") is None
        if not lazy:
            self._connect()

    def _connect(self):
        """Talk to the Secret Service once, on first use: opening a collection can prompt the
        user (new keyring), so windows must not do this while starting up."""
        if self._tried:
            return
        self._tried = True
        if not self._allow:
            return
        try:
            import secretstorage  # type: ignore

            conn = secretstorage.dbus_init()
            # never create or unlock a collection here: both raise a GUI prompt that can block
            # a window that is still starting; use an existing unlocked keyring or the file
            colls = list(secretstorage.get_all_collections(conn))
            coll = next((c for c in colls if c.get_label().lower() in ("login", "default")), None) or (colls[0] if colls else None)
            if coll is not None and not coll.is_locked():
                self._ss = (secretstorage, conn, coll)
        except Exception:
            self._ss = None

    @property
    def backend(self) -> str:
        self._connect()
        return "keyring" if self._ss else "file"

    def _file(self) -> str:
        return os.path.join(config_dir(), "keys.json")

    def _read_file(self) -> Dict[str, str]:
        try:
            with open(self._file(), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def get(self, provider: str) -> Optional[str]:
        self._connect()
        if self._ss:
            secretstorage, conn, coll = self._ss
            for item in coll.search_items({"service": self.SERVICE, "provider": provider}):
                return item.get_secret().decode("utf-8")
            return None
        return self._read_file().get(provider)

    def set(self, provider: str, key: str) -> None:
        key = key.strip()
        self._connect()
        if self._ss:
            secretstorage, conn, coll = self._ss
            self.delete(provider)
            coll.create_item(f"Eternity 08 {provider} API key", {"service": self.SERVICE, "provider": provider},
                             key.encode("utf-8"), replace=True)
            return
        keys = self._read_file()
        keys[provider] = key
        _atomic_write(self._file(), json.dumps(keys, indent=2) + "\n", 0o600)

    def delete(self, provider: str) -> None:
        self._connect()
        if self._ss:
            secretstorage, conn, coll = self._ss
            for item in coll.search_items({"service": self.SERVICE, "provider": provider}):
                item.delete()
            return
        keys = self._read_file()
        if provider in keys:
            del keys[provider]
            _atomic_write(self._file(), json.dumps(keys, indent=2) + "\n", 0o600)

    def file_mode_ok(self) -> bool:
        try:
            return stat.S_IMODE(os.stat(self._file()).st_mode) == 0o600
        except OSError:
            return True
