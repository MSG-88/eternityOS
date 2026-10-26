"""Routines: named task sequences the assistant builds from the user's words and runs on command.
Run: python3 -m unittest tests/host/test_routines.py"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import routines as R  # noqa: E402


class RoutinesStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = R.Routines(path=os.path.join(self.tmp.name, "routines.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_define_and_get_survive_reload(self):
        steps = [{"tool": "open_app", "args": {"name": "firefox"}},
                 {"tool": "open_app", "args": {"name": "terminal"}}]
        self.r.define("morning", steps, description="my start of day")
        again = R.Routines(path=self.r.path)
        got = again.get("morning")
        self.assertEqual(got["steps"], steps)
        self.assertEqual(got["description"], "my start of day")

    def test_name_is_normalized_so_run_my_morning_routine_matches(self):
        self.r.define("Morning Routine", [{"tool": "open_app", "args": {"name": "x"}}])
        self.assertIsNotNone(self.r.get("morning routine"))
        self.assertIsNotNone(self.r.get("  MORNING   routine "))
        self.assertIsNotNone(self.r.get("morning-routine"))

    def test_define_rejects_empty_or_stepless(self):
        with self.assertRaises(R.RoutineError):
            self.r.define("", [{"tool": "x", "args": {}}])
        with self.assertRaises(R.RoutineError):
            self.r.define("empty", [])

    def test_steps_must_name_a_tool(self):
        with self.assertRaises(R.RoutineError):
            self.r.define("bad", [{"args": {}}])

    def test_list_and_forget(self):
        self.r.define("a", [{"tool": "t", "args": {}}])
        self.r.define("b", [{"tool": "t", "args": {}}])
        self.assertEqual(sorted(x["name"] for x in self.r.list()), ["a", "b"])
        self.assertEqual(self.r.forget("a"), 1)
        self.assertEqual([x["name"] for x in self.r.list()], ["b"])
        self.assertEqual(self.r.forget("missing"), 0)

    def test_prompt_section_lists_routines_for_the_model(self):
        self.r.define("morning", [{"tool": "open_app", "args": {"name": "firefox"}}], description="start of day")
        s = self.r.prompt_section()
        self.assertIn("morning", s)
        self.assertIn("run_routine", s)

    def test_prompt_section_empty_when_none(self):
        self.assertEqual(self.r.prompt_section(), "")


if __name__ == "__main__":
    unittest.main()
