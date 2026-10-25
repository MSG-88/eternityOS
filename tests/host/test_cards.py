"""Home-screen card data sources. Run: python3 -m unittest tests/host/test_cards.py"""
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import cards as C  # noqa: E402
from eternity import providers as P  # noqa: E402
from eternity import settings as S  # noqa: E402


class CardsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self.tmp.name
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, ".config")
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, ".local", "state")

    def tearDown(self):
        self.tmp.cleanup()

    def test_cpu_percent_needs_two_samples(self):
        C._last_cpu.update(idle=0, total=0)
        self.assertIsNone(C.cpu_percent())
        time.sleep(0.05)
        v = C.cpu_percent()
        self.assertTrue(v is None or 0 <= v <= 100)

    def test_memory_and_today(self):
        m = C.memory()
        self.assertGreater(m["total_gb"], 0)
        self.assertGreaterEqual(m["total_gb"], m["used_gb"])
        t = C.today()
        self.assertRegex(t["time"], r"^\d\d:\d\d$")
        self.assertIn(t["part"], ("morning", "afternoon", "evening", "night"))

    def test_recent_files_orders_newest_first(self):
        docs = os.path.join(self.tmp.name, "Documents")
        os.makedirs(docs)
        for i, name in enumerate(("old.txt", "new.txt")):
            p = os.path.join(docs, name)
            with open(p, "w") as f:
                f.write(name)
            os.utime(p, (time.time() - 1000 + i * 500, time.time() - 1000 + i * 500))
        with open(os.path.join(docs, ".hidden"), "w") as f:
            f.write("x")
        files = C.recent_files(5, roots=[docs])
        self.assertEqual([f["name"] for f in files], ["new.txt", "old.txt"])
        self.assertIn("ago", files[0]["when"])

    def test_ai_status_reads_remembered_metrics(self):
        C.remember_metrics(P.Metrics(first_token_ms=41, tokens_per_s=170.0, provider="local", on_device=True))
        st = C.ai_status(S.Settings())
        self.assertEqual(st["provider"], "local")
        self.assertIn("41 ms", st["readout"])
        self.assertIn("170 tok/s", st["readout"])
        st = C.ai_status(S.Settings(provider="anthropic", on_device_only=False))
        self.assertEqual(st["label"], "Claude (Anthropic API key)")

    def test_actions_today_counts_only_executed(self):
        from eternity import actions as A
        a = A.Audit()
        a.write(tool="x", args={}, decision="approved", ok=True, summary="")
        a.write(tool="y", args={}, decision="declined", ok=False, summary="")
        self.assertEqual(C.actions_today(), 1)


if __name__ == "__main__":
    unittest.main()


class TestAiCardModel(unittest.TestCase):
    def test_claude_code_card_names_its_own_model(self):
        # 2026-10-26 on the installed VM: the card said "gpt-5.1" under "Claude (your Claude account)"
        import eternity.cards as C, eternity.settings as S
        cfg = S.Settings(provider="claude_code", on_device_only=False, claude_code_model="opus", openai_model="gpt-5.1")
        ai = C.ai_status(cfg)
        self.assertEqual(ai["model"], "opus")
