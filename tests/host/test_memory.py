"""The learning layer: what Eternity remembers about its user, on this device only.
Run: python3 -m unittest tests/host/test_memory.py"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import memory as M  # noqa: E402


class MemoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.m = M.Memory(path=os.path.join(self.tmp.name, "memory.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_fact_is_kept_and_survives_reload(self):
        self.m.remember("I work on the Eternity OS in Python and QML")
        again = M.Memory(path=self.m.path)
        self.assertEqual([f["text"] for f in again.facts()], ["I work on the Eternity OS in Python and QML"])

    def test_a_question_that_states_a_preference_becomes_a_fact(self):
        self.m.observe("remember that I prefer dark themes and short answers", actions=[])
        self.assertIn("I prefer dark themes and short answers", [f["text"] for f in self.m.facts()])

    def test_my_name_is_becomes_a_fact(self):
        self.m.observe("my name is Muthu, call me Muthu", actions=[])
        self.assertTrue(any("Muthu" in f["text"] for f in self.m.facts()))

    def test_plain_questions_are_not_stored_as_facts_but_counted(self):
        self.m.observe("how much disk is free?", actions=[{"name": "system_info"}])
        self.assertEqual(self.m.facts(), [])
        self.assertEqual(self.m.recent()[0]["q"], "how much disk is free?")
        self.assertEqual(self.m.tool_counts()["system_info"], 1)

    def test_forget_removes_matching_facts(self):
        self.m.remember("I like coffee")
        self.m.remember("I like tea")
        self.assertEqual(self.m.forget("coffee"), 1)
        self.assertEqual([f["text"] for f in self.m.facts()], ["I like tea"])

    def test_prompt_section_lists_facts_habits_and_recent_questions(self):
        self.m.remember("I am a developer")
        for _ in range(3):
            self.m.observe("open the terminal", actions=[{"name": "launch_app"}])
        self.m.observe("what time is it in Tokyo?", actions=[])
        s = self.m.prompt_section()
        self.assertIn("I am a developer", s)
        self.assertIn("launch_app", s)
        self.assertIn("what time is it in Tokyo?", s)
        self.assertLess(len(s), 1600)

    def test_prompt_section_is_empty_when_nothing_is_known(self):
        self.assertEqual(self.m.prompt_section(), "")

    def test_recent_is_bounded(self):
        for i in range(80):
            self.m.observe(f"question {i}", actions=[])
        self.assertLessEqual(len(self.m.recent()), M.RECENT_MAX)
        self.assertEqual(self.m.recent()[0]["q"], "question 79")

    def test_learning_off_observes_nothing(self):
        self.m.enabled = False
        self.m.observe("my name is Someone", actions=[{"name": "system_info"}])
        self.assertEqual(self.m.facts(), [])
        self.assertEqual(self.m.recent(), [])


if __name__ == "__main__":
    unittest.main()
