"""AI providers for Eternity 08: the bundled local model (llama.cpp server), Anthropic and
OpenAI over their HTTP APIs. One streaming interface for all three:

    for event in provider.stream(messages, system=..., tools=...):
        kind, payload = event
        # ("text", str) | ("tool_call", {"id", "name", "arguments": dict}) | ("done", Metrics)

Messages use the OpenAI shape ({"role": "user"|"assistant"|"tool", "content": str, ...});
Anthropic's format is converted on the way out. Only the standard library is used.
"""
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

from . import settings as S

Event = Tuple[str, object]


class ProviderError(Exception):
    """A readable reason the provider cannot answer (shown to the user as is)."""


@dataclass
class Metrics:
    first_token_ms: Optional[int] = None
    total_ms: int = 0
    tokens: int = 0
    tokens_per_s: float = 0.0
    provider: str = ""
    model: str = ""
    on_device: bool = True

    def readout(self) -> str:
        parts = ["on device" if self.on_device else f"{self.provider}"]
        if self.first_token_ms is not None:
            parts.append(f"first token {self.first_token_ms} ms")
        if self.tokens_per_s:
            parts.append(f"~{self.tokens_per_s:.0f} tok/s")
        return "  ·  ".join(parts)


@dataclass
class _ToolAcc:
    id: str = ""
    name: str = ""
    arguments: str = ""


def _sse_lines(resp) -> Iterator[str]:
    """Yield the data payloads of a server-sent-events response."""
    for raw in resp:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith("data:"):
            yield line[5:].strip()


class _ThinkFilter:
    """Drops <think>...</think> passages from a streamed text (Qwen reasoning)."""

    def __init__(self):
        self.buf = ""
        self.inside = False

    def feed(self, text: str) -> str:
        self.buf += text
        out = ""
        while self.buf:
            if self.inside:
                end = self.buf.find("</think>")
                if end < 0:
                    self.buf = self.buf[-8:] if len(self.buf) > 8 else self.buf
                    return out
                self.buf = self.buf[end + 8:]
                self.inside = False
                continue
            start = self.buf.find("<think>")
            if start < 0:
                # keep a possible partial tag at the end
                cut = len(self.buf)
                for k in range(1, min(7, len(self.buf)) + 1):
                    if "<think>".startswith(self.buf[-k:]):
                        cut = len(self.buf) - k
                        break
                out += self.buf[:cut]
                self.buf = self.buf[cut:]
                return out
            out += self.buf[:start]
            self.buf = self.buf[start + 7:]
            self.inside = True
        return out


def _json_or_raw(s: str) -> dict:
    try:
        v = json.loads(s) if s.strip() else {}
        return v if isinstance(v, dict) else {"value": v}
    except ValueError:
        return {"_raw": s}


class Provider:
    name = "base"
    on_device = False

    def __init__(self, model: str):
        self.model = model

    def stream(self, messages: List[dict], system: Optional[str] = None,
               tools: Optional[List[dict]] = None, max_tokens: int = 1024) -> Iterator[Event]:
        raise NotImplementedError

    def _request(self, url: str, body: dict, headers: Dict[str, str], timeout: float = 120.0):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise ProviderError(f"{self.name}: HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            raise ProviderError(f"{self.name}: cannot reach {url}: {e.reason}") from None


class OpenAICompatible(Provider):
    """OpenAI chat-completions streaming, also spoken by llama-server."""

    base_url = "https://api.openai.com/v1"
    name = "openai"

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model)
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def extra_body(self) -> dict:
        return {}

    def stream(self, messages, system=None, tools=None, max_tokens=1024):
        msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
        body = {"model": self.model, "messages": msgs, "stream": True, "max_tokens": max_tokens,
                **self.extra_body()}
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in tools]
            body["tool_choice"] = "auto"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        t0 = time.monotonic()
        m = Metrics(provider=self.name, model=self.model, on_device=self.on_device)
        acc: Dict[int, _ToolAcc] = {}
        think = _ThinkFilter()
        chars = 0
        with self._request(f"{self.base_url}/chat/completions", body, headers) as resp:
            for data in _sse_lines(resp):
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except ValueError:
                    continue
                timings = obj.get("timings") or {}
                if timings.get("predicted_n"):
                    m.tokens = int(timings["predicted_n"])
                    m.tokens_per_s = float(timings.get("predicted_per_second") or 0)
                usage = obj.get("usage") or {}
                if usage.get("completion_tokens"):
                    m.tokens = int(usage["completion_tokens"])
                for choice in obj.get("choices") or []:
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if text:
                        text = think.feed(text)
                        if text:
                            if m.first_token_ms is None:
                                m.first_token_ms = int((time.monotonic() - t0) * 1000)
                            chars += len(text)
                            yield ("text", text)
                    for tc in delta.get("tool_calls") or []:
                        idx = int(tc.get("index", 0))
                        a = acc.setdefault(idx, _ToolAcc())
                        if tc.get("id"):
                            a.id = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            a.name = fn["name"]
                        if fn.get("arguments"):
                            a.arguments += fn["arguments"]
                        if m.first_token_ms is None:
                            m.first_token_ms = int((time.monotonic() - t0) * 1000)
        for idx in sorted(acc):
            a = acc[idx]
            if a.name:
                yield ("tool_call", {"id": a.id or f"call_{idx}", "name": a.name, "arguments": _json_or_raw(a.arguments)})
        m.total_ms = int((time.monotonic() - t0) * 1000)
        if not m.tokens:
            m.tokens = max(1, chars // 4)
        if not m.tokens_per_s and m.total_ms:
            gen_ms = max(1, m.total_ms - (m.first_token_ms or 0))
            m.tokens_per_s = m.tokens / (gen_ms / 1000)
        yield ("done", m)


class LocalProvider(OpenAICompatible):
    """The bundled llama.cpp server. Started on demand as a user service and kept warm."""

    name = "local"
    on_device = True
    MODELS_DIR = os.environ.get("ETERNITY_MODELS_DIR", "/opt/eternity/models")
    MIN_MEM_KB = int(os.environ.get("ETERNITY_MIN_MEM_KB", "5500000"))

    def __init__(self, model_choice: str = "auto", base_url: Optional[str] = None):
        url = base_url or os.environ.get("ETERNITY_LLAMA_URL", "http://127.0.0.1:8080/v1")
        super().__init__("local", None, url)
        self.model_choice = model_choice

    def extra_body(self) -> dict:
        # Qwen3.5: answer directly (thinking off) unless the caller wants reasoning.
        return {"chat_template_kwargs": {"enable_thinking": False}, "temperature": 0.6, "top_p": 0.95}

    # -- lifecycle -------------------------------------------------------------------
    def model_path(self) -> str:
        choice = self.model_choice
        if choice == "auto":
            avail = 0
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemAvailable:"):
                            avail = int(line.split()[1])
            except OSError:
                pass
            choice = "small" if avail < self.MIN_MEM_KB else "default"
        return os.path.join(self.MODELS_DIR, f"{choice}.gguf")

    def healthy(self, timeout: float = 1.0) -> bool:
        try:
            with urllib.request.urlopen(self.base_url.rsplit("/v1", 1)[0] + "/health", timeout=timeout) as r:
                return r.status == 200
        except Exception:
            return False

    def ensure_running(self, wait_s: float = 120.0, log=None) -> bool:
        """Start llama-server as a transient user unit if nothing answers on the port."""
        if self.healthy():
            return True
        model = self.model_path()
        if not os.path.exists(model):
            raise ProviderError(f"local model not found: {model} (run 'eternity-ai models')")
        server = shutil.which("llama-server")
        if not server:
            raise ProviderError("llama-server is not installed")
        threads = os.cpu_count() or 4
        host, port = "127.0.0.1", "8080"
        try:
            port = self.base_url.split(":")[2].split("/")[0]
        except IndexError:
            pass
        cmd = [server, "-m", model, "--host", host, "--port", port, "-c", "4096", "-t", str(threads),
               "--jinja", "--log-disable"]
        if shutil.which("systemd-run") and os.environ.get("ETERNITY_NO_SYSTEMD_RUN") is None:
            cmd = ["systemd-run", "--user", "--quiet", "--collect", "--unit", "eternity-llama",
                   "--property", "MemoryMax=80%"] + cmd
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        t0 = time.monotonic()
        while time.monotonic() - t0 < wait_s:
            if self.healthy():
                if log:
                    log(f"local model ready in {time.monotonic() - t0:.0f} s")
                return True
            time.sleep(0.5)
        raise ProviderError("the local model did not start in time")

    def stream(self, messages, system=None, tools=None, max_tokens=1024):
        if not self.healthy():
            yield ("status", "waking the local model …")
        self.ensure_running()
        yield from super().stream(messages, system, tools, max_tokens)


class AnthropicProvider(Provider):
    name = "anthropic"
    base_url = "https://api.anthropic.com/v1"

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        super().__init__(model)
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    @staticmethod
    def _convert(messages: List[dict]) -> List[dict]:
        """OpenAI-shaped history -> Anthropic messages (tool calls and results as blocks)."""
        out: List[dict] = []
        for m in messages:
            role, content = m.get("role"), m.get("content")
            if role == "tool":
                block = {"type": "tool_result", "tool_use_id": m.get("tool_call_id", ""), "content": str(content or "")}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
            elif role == "assistant" and m.get("tool_calls"):
                blocks = [{"type": "text", "text": content}] if content else []
                for tc in m["tool_calls"]:
                    fn = tc.get("function", tc)
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        args = _json_or_raw(args)
                    blocks.append({"type": "tool_use", "id": tc.get("id", ""), "name": fn.get("name", ""), "input": args})
                out.append({"role": "assistant", "content": blocks})
            elif role in ("user", "assistant"):
                out.append({"role": role, "content": content or ""})
        return out

    def stream(self, messages, system=None, tools=None, max_tokens=1024):
        body = {"model": self.model, "max_tokens": max_tokens, "messages": self._convert(messages), "stream": True}
        if system:
            body["system"] = system
        if tools:
            body["tools"] = [{"name": t["name"], "description": t.get("description", ""),
                              "input_schema": t.get("parameters", {"type": "object", "properties": {}})} for t in tools]
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        t0 = time.monotonic()
        m = Metrics(provider=self.name, model=self.model, on_device=False)
        blocks: Dict[int, dict] = {}
        chars = 0
        with self._request(f"{self.base_url}/messages", body, headers) as resp:
            for data in _sse_lines(resp):
                try:
                    obj = json.loads(data)
                except ValueError:
                    continue
                typ = obj.get("type")
                if typ == "content_block_start":
                    cb = obj.get("content_block") or {}
                    blocks[obj.get("index", 0)] = {"type": cb.get("type"), "id": cb.get("id", ""), "name": cb.get("name", ""), "json": ""}
                elif typ == "content_block_delta":
                    d = obj.get("delta") or {}
                    if d.get("type") == "text_delta" and d.get("text"):
                        if m.first_token_ms is None:
                            m.first_token_ms = int((time.monotonic() - t0) * 1000)
                        chars += len(d["text"])
                        yield ("text", d["text"])
                    elif d.get("type") == "input_json_delta":
                        b = blocks.setdefault(obj.get("index", 0), {"type": "tool_use", "id": "", "name": "", "json": ""})
                        b["json"] += d.get("partial_json", "")
                        if m.first_token_ms is None:
                            m.first_token_ms = int((time.monotonic() - t0) * 1000)
                elif typ == "content_block_stop":
                    b = blocks.get(obj.get("index", 0))
                    if b and b["type"] == "tool_use":
                        yield ("tool_call", {"id": b["id"], "name": b["name"], "arguments": _json_or_raw(b["json"])})
                elif typ == "message_delta":
                    usage = obj.get("usage") or {}
                    if usage.get("output_tokens"):
                        m.tokens = int(usage["output_tokens"])
                elif typ == "error":
                    raise ProviderError(f"anthropic: {obj.get('error', {}).get('message', 'error')}")
        m.total_ms = int((time.monotonic() - t0) * 1000)
        if not m.tokens:
            m.tokens = max(1, chars // 4)
        gen_ms = max(1, m.total_ms - (m.first_token_ms or 0))
        m.tokens_per_s = m.tokens / (gen_ms / 1000)
        yield ("done", m)


PROVIDER_LABELS = {"local": "Eternity (on this device)", "anthropic": "Claude (Anthropic)", "openai": "ChatGPT (OpenAI)"}
PROVIDER_KEY_URLS = {"anthropic": "https://console.anthropic.com/settings/keys", "openai": "https://platform.openai.com/api-keys"}


def get_provider(cfg: S.Settings, secrets: Optional[S.SecretStore] = None) -> Provider:
    """The provider the settings ask for, or a readable ProviderError."""
    choice = cfg.effective_provider()
    if choice == "local":
        return LocalProvider(cfg.local_model)
    secrets = secrets or S.SecretStore()
    key = secrets.get(choice)
    if not key:
        raise ProviderError(f"no API key stored for {PROVIDER_LABELS[choice]} (Settings > Eternity > Provider)")
    if choice == "anthropic":
        return AnthropicProvider(cfg.anthropic_model, key)
    return OpenAICompatible(cfg.openai_model, key)
