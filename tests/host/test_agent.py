"""Agent loop with a scripted provider: tool round trips, consent, undo, provider errors.
Run: python3 -m unittest tests/host/test_agent.py"""
import os
import sys
import tempfile
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import actions as A  # noqa: E402
from eternity import agent as G  # noqa: E402
from eternity import memory as M  # noqa: E402
from eternity import providers as P  # noqa: E402
from eternity import settings as S  # noqa: E402


class ScriptedProvider(P.Provider):
    """Replays scripted turns; records what it was asked."""
    name = "scripted"
    on_device = True

    def __init__(self, turns):
        super().__init__("scripted")
        self.turns = list(turns)
        self.calls = []

    def stream(self, messages, system=None, tools=None, max_tokens=1024):
        self.calls.append({"messages": [dict(m) for m in messages], "system": system, "tools": tools})
        if not self.turns:
            raise P.ProviderError("scripted: out of turns")
        turn = self.turns.pop(0)
        if turn == "ERROR":
            raise P.ProviderError("the local model did not start in time")
        for ev in turn:
            yield ev
        yield ("done", P.Metrics(first_token_ms=41, tokens=17, tokens_per_s=170.0, provider="scripted", model="s"))


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self.tmp.name
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, ".config")
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, ".local", "state")

    def tearDown(self):
        self.tmp.cleanup()

    def run_agent(self, turns, consent=lambda t, a: True, cfg=None):
        prov = ScriptedProvider(turns)
        cfg = cfg or S.Settings(name="Maya")
        agent = G.Agent(consent, cfg=cfg, provider=prov, broker=A.ActionBroker(consent, cfg=cfg, audit=A.Audit()))
        events = list(agent.ask("save a note that the design review moved"))
        return agent, prov, events

    def test_tool_round_trip_then_answer(self):
        turns = [
            [("text", "Saving that. "), ("tool_call", {"id": "c1", "name": "write_note", "arguments": {"title": "Design review", "text": "moved to tomorrow"}})],
            [("text", "Done, the note is in Documents/Notes.")],
        ]
        agent, prov, events = self.run_agent(turns)
        kinds = [k for k, _ in events]
        self.assertEqual(kinds, ["text", "status", "action", "text", "done"])
        action = events[2][1]
        self.assertTrue(action["ok"], action["summary"])
        self.assertTrue(action["undoable"])
        # second provider call carries the assistant tool call and the tool result
        second = prov.calls[1]["messages"]
        self.assertEqual(second[1]["role"], "assistant")
        self.assertEqual(second[1]["tool_calls"][0]["function"]["name"], "write_note")
        self.assertEqual(second[2]["role"], "tool")
        self.assertIn("note saved", second[2]["content"])
        self.assertIn("Maya", prov.calls[0]["system"])
        self.assertTrue(any(t["name"] == "write_note" for t in prov.calls[0]["tools"]))
        self.assertIn("removed", agent.undo_last())
        self.assertEqual(events[-1][1].first_token_ms, 41)

    def test_declined_tool_is_reported_truthfully(self):
        turns = [
            [("tool_call", {"id": "c1", "name": "write_note", "arguments": {"title": "x", "text": "y"}})],
            [("text", "Understood, I did not save it.")],
        ]
        agent, prov, events = self.run_agent(turns, consent=lambda t, a: False, cfg=S.Settings(name="Maya", trust_level=0))
        action = next(p for k, p in events if k == "action")
        self.assertFalse(action["ok"])
        self.assertIn("declined", prov.calls[1]["messages"][2]["content"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "Documents", "Notes")))

    def test_provider_error_becomes_status(self):
        agent, prov, events = self.run_agent(["ERROR"])
        self.assertEqual([k for k, _ in events], ["status", "done"])
        self.assertIn("did not start", events[0][1])

    def test_agent_mode_off_sends_no_tools(self):
        cfg = S.Settings(agent_mode=False)
        agent, prov, events = self.run_agent([[("text", "Hi.")]], cfg=cfg)
        self.assertIsNone(prov.calls[0]["tools"])
        self.assertIn("cannot run actions", prov.calls[0]["system"])

    def test_tool_round_limit(self):
        loop = [[("tool_call", {"id": f"c{i}", "name": "system_info", "arguments": {}})] for i in range(10)]
        agent, prov, events = self.run_agent(loop, cfg=S.Settings(trust_level=1))
        self.assertEqual(len(prov.calls), G.MAX_TOOL_ROUNDS)
        self.assertEqual(events[-1][0], "done")

    def test_agent_prompt_describes_the_jarvis_capabilities(self):
        s = G.system_prompt(S.Settings(agent_mode=True))
        for word in ("routine", "reminder", "brightness", "workspace", "speak"):
            self.assertIn(word, s.lower())
        self.assertNotIn("routine", G.system_prompt(S.Settings(agent_mode=False)).lower())

    def test_os_knowledge_mentions_the_os(self):
        k = G.os_knowledge()
        self.assertIn("CPU threads", k)
        self.assertIn("/opt/eternity/models", k)

    def test_os_knowledge_names_hyprland_in_the_eternity_session(self):
        # in the Eternity session the compositor is Hyprland; the assistant must not go looking for xfwm4
        env = {"XDG_CURRENT_DESKTOP": "Eternity", "HYPRLAND_INSTANCE_SIGNATURE": "abc123"}
        with unittest.mock.patch.dict(os.environ, env):
            k = G.os_knowledge()
        self.assertIn("Hyprland", k)
        self.assertIn("Wayland", k)
        self.assertIn("Eternity shell", k)
        self.assertNotIn("xfwm4", k)

    def test_system_prompt_carries_what_the_user_told_eternity(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = M.Memory(path=os.path.join(tmp, "m.json"))
            mem.remember("I am a developer who prefers short answers")
            s = G.system_prompt(S.Settings(), memory=mem)
        self.assertIn("I am a developer who prefers short answers", s)
        self.assertNotIn("What the user has told you", G.system_prompt(S.Settings()))

    def test_agent_observes_each_ask_into_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = M.Memory(path=os.path.join(tmp, "m.json"))
            prov = ScriptedProvider([[("text", "Noted."), ("done", P.Metrics(provider="scripted"))]])
            agent = G.Agent(consent=lambda t, a: True, cfg=S.Settings(), provider=prov, memory=mem)
            list(agent.ask("remember that I work on Eternity"))
            self.assertEqual([f["text"] for f in mem.facts()], ["I work on Eternity"])
            self.assertEqual(mem.recent()[0]["q"], "remember that I work on Eternity")

    def test_os_knowledge_names_xfce_in_the_classic_session(self):
        env = {"XDG_CURRENT_DESKTOP": "XFCE"}
        with unittest.mock.patch.dict(os.environ, env):
            os.environ.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
            k = G.os_knowledge()
        self.assertIn("xfwm4", k)
        self.assertNotIn("Hyprland", k)


if __name__ == "__main__":
    unittest.main()
