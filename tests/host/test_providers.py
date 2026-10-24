"""Provider layer against a fake streaming server (OpenAI/llama-server shape and Anthropic
shape). Run: python3 -m unittest tests/host/test_providers.py"""
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import providers as P  # noqa: E402
from eternity import settings as S  # noqa: E402

LAST = {}


class FakeAPI(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404); self.end_headers()

    def _sse(self, events):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for e in events:
            self.wfile.write(f"data: {e if isinstance(e, str) else json.dumps(e)}\n\n".encode())
        self.wfile.flush()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LAST["path"] = self.path
        LAST["body"] = body
        LAST["headers"] = {k.lower(): v for k, v in self.headers.items()}
        if self.path.endswith("/chat/completions"):
            if body.get("tools") and "volume" in json.dumps(body["messages"]):
                self._sse([
                    {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "set_volume", "arguments": "{\"perc"}}]}}]},
                    {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "ent\": 30}"}}]}}]},
                    {"choices": [{"delta": {}, "finish_reason": "tool_calls"}], "timings": {"predicted_n": 12, "predicted_per_second": 40.0}},
                    "[DONE]"])
            else:
                self._sse([
                    {"choices": [{"delta": {"content": "<think>hmm</think>Hel"}}]},
                    {"choices": [{"delta": {"content": "lo, Maya."}}]},
                    {"choices": [{"delta": {}, "finish_reason": "stop"}], "timings": {"predicted_n": 5, "predicted_per_second": 170.0}},
                    "[DONE]"])
        elif self.path.endswith("/messages"):
            self._sse([
                {"type": "message_start", "message": {"id": "m1"}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Moving it. "}},
                {"type": "content_block_stop", "index": 0},
                {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_1", "name": "write_note", "input": {}}},
                {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "{\"title\": \"Design"}},
                {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": " review\", \"text\": \"moved\"}"}},
                {"type": "content_block_stop", "index": 1},
                {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 21}},
                {"type": "message_stop"}])
        else:
            self.send_response(404); self.end_headers()


class ProviderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), FakeAPI)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def collect(self, provider, messages, tools=None, system=None):
        text, calls, metrics = "", [], None
        for kind, payload in provider.stream(messages, system=system, tools=tools):
            if kind == "text":
                text += payload
            elif kind == "tool_call":
                calls.append(payload)
            elif kind == "done":
                metrics = payload
        return text, calls, metrics

    def test_local_streams_text_and_strips_thinking(self):
        p = P.LocalProvider("auto", base_url=self.url + "/v1")
        text, calls, m = self.collect(p, [{"role": "user", "content": "hi"}], system="You are Eternity.")
        self.assertEqual(text, "Hello, Maya.")
        self.assertEqual(calls, [])
        self.assertTrue(m.on_device)
        self.assertEqual(m.tokens, 5)
        self.assertEqual(m.tokens_per_s, 170.0)
        self.assertIsNotNone(m.first_token_ms)
        self.assertEqual(LAST["body"]["messages"][0], {"role": "system", "content": "You are Eternity."})
        self.assertFalse(LAST["body"]["chat_template_kwargs"]["enable_thinking"])
        self.assertIn("on device", m.readout())

    def test_local_tool_call_is_assembled_from_chunks(self):
        p = P.LocalProvider("auto", base_url=self.url + "/v1")
        tools = [{"name": "set_volume", "description": "d", "parameters": {"type": "object", "properties": {}}}]
        text, calls, m = self.collect(p, [{"role": "user", "content": "lower the volume"}], tools=tools)
        self.assertEqual(text, "")
        self.assertEqual(calls, [{"id": "call_1", "name": "set_volume", "arguments": {"percent": 30}}])
        self.assertEqual(LAST["body"]["tools"][0]["type"], "function")

    def test_openai_sends_bearer_key(self):
        p = P.OpenAICompatible("gpt-5.1", api_key="sk-test", base_url=self.url + "/v1")
        text, _, m = self.collect(p, [{"role": "user", "content": "hi"}])
        self.assertEqual(text, "Hello, Maya.")
        self.assertEqual(LAST["headers"].get("authorization"), "Bearer sk-test")
        self.assertFalse(m.on_device)

    def test_anthropic_text_and_tool_use(self):
        p = P.AnthropicProvider("claude-sonnet-5-5", "sk-ant", base_url=self.url)
        history = [
            {"role": "user", "content": "move my 3pm"},
            {"role": "assistant", "content": "Checking.", "tool_calls": [{"id": "t0", "function": {"name": "find_files", "arguments": "{\"pattern\": \"spec\"}"}}]},
            {"role": "tool", "tool_call_id": "t0", "content": "2 matches"},
            {"role": "user", "content": "go on"},
        ]
        tools = [{"name": "write_note", "description": "n", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}}}]
        text, calls, m = self.collect(p, history, tools=tools, system="sys")
        self.assertEqual(text, "Moving it. ")
        self.assertEqual(calls, [{"id": "toolu_1", "name": "write_note", "arguments": {"title": "Design review", "text": "moved"}}])
        self.assertEqual(m.tokens, 21)
        body = LAST["body"]
        self.assertEqual(LAST["headers"].get("x-api-key"), "sk-ant")
        self.assertEqual(body["system"], "sys")
        self.assertEqual(body["tools"][0]["input_schema"]["type"], "object")
        conv = body["messages"]
        self.assertEqual(conv[1]["content"][1]["type"], "tool_use")
        self.assertEqual(conv[1]["content"][1]["input"], {"pattern": "spec"})
        self.assertEqual(conv[2]["content"][0]["type"], "tool_result")
        self.assertEqual(conv[3], {"role": "user", "content": "go on"})

    def test_get_provider_respects_on_device_only_and_missing_keys(self):
        secrets = S.SecretStore(allow_keyring=False)
        cfg = S.Settings(provider="anthropic", on_device_only=True)
        self.assertIsInstance(P.get_provider(cfg, secrets), P.LocalProvider)
        cfg = S.Settings(provider="anthropic", on_device_only=False)
        with self.assertRaises(P.ProviderError):
            P.get_provider(cfg, secrets)

    def test_think_filter_handles_split_tags(self):
        f = P._ThinkFilter()
        out = f.feed("A<thi") + f.feed("nk>secret</th") + f.feed("ink>B") + f.feed("C")
        self.assertEqual(out, "ABC")


if __name__ == "__main__":
    unittest.main()
