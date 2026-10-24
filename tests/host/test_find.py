"""Search by meaning: index build, incremental updates, ranking, grouping (hash embedder, no
model needed). Run: python3 -m unittest tests/host/test_find.py"""
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import find as F  # noqa: E402


class FindTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self.tmp.name
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, ".local", "state")
        self.pics = os.path.join(self.tmp.name, "Pictures", "Lisbon trip")
        self.docs = os.path.join(self.tmp.name, "Documents")
        os.makedirs(self.pics); os.makedirs(self.docs)
        march = time.mktime((2026, 3, 14, 12, 0, 0, 0, 0, -1))
        for i in range(5):
            p = os.path.join(self.pics, f"alfama-walk-{i}.jpg")
            open(p, "wb").write(b"\xff\xd8 fake")
            os.utime(p, (march, march))
        for name, text in (("shell-spec.md", "The shell spec argues for one presence, not many apps; input under 50 ms."),
                           ("groceries.txt", "milk eggs bread"), ("tax-2025.txt", "tax return figures")):
            with open(os.path.join(self.docs, name), "w") as f:
                f.write(text)
        self.idx = F.Index(path=os.path.join(self.tmp.name, "index.sqlite"), embedder=F.HashEmbedder())

    def tearDown(self):
        self.idx.db.close()
        self.tmp.cleanup()

    def test_build_is_incremental(self):
        st = self.idx.build([self.pics, self.docs])
        self.assertEqual((st["indexed"], st["total"]), (8, 8))
        st = self.idx.build([self.pics, self.docs])
        self.assertEqual(st["indexed"], 0, "unchanged files are not re-embedded")
        os.remove(os.path.join(self.docs, "groceries.txt"))
        st = self.idx.build([self.pics, self.docs])
        self.assertEqual((st["removed"], st["total"]), (1, 7))

    def test_search_groups_photos_by_folder_and_month(self):
        self.idx.build([self.pics, self.docs])
        t0 = time.monotonic()
        hits = self.idx.search("photos from the Lisbon trip")
        ms = (time.monotonic() - t0) * 1000
        self.assertTrue(hits)
        self.assertTrue(all(h.kind == "photo" for h in hits[:5]), [h.path for h in hits[:6]])
        g = F.group(hits)
        self.assertEqual(g["top_month"], "March 2026")
        self.assertTrue(str(g["top_folder"]).endswith("Lisbon trip"))
        self.assertIn("Lisbon trip", F.suggestion(g))
        self.assertIn("matches", F.header(g, ms))

    def test_search_finds_text_by_content_words(self):
        self.idx.build([self.pics, self.docs])
        hits = self.idx.search("spec about one presence and input latency")
        self.assertEqual(hits[0].name, "shell-spec.md")

    def test_describe_and_kind(self):
        d = F.describe("/home/u/Documents/DesignReview_notes.md", time.mktime((2026, 10, 25, 1, 0, 0, 0, 0, -1)), "text", "body")
        self.assertIn("Design Review notes", d)
        self.assertIn("October 2026", d)
        self.assertEqual(F.kind_of("a.PNG"), "photo")
        self.assertEqual(F.kind_of("a.pdf"), "document")
        self.assertEqual(F.kind_of("a.bin"), "file")

    def test_hash_embedder_is_unit_length(self):
        v = F.HashEmbedder()(["hello world"])[0]
        self.assertAlmostEqual(sum(x * x for x in v), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
