"""Search by meaning over the user's files (design scene 07), on device.

An index (sqlite, ~/.local/state/eternity/index.sqlite) holds one vector per file: the
embedding of its name, folders, date and, for text files, the first part of its content.
Embeddings come from the bundled bge-small model through a llama.cpp server in embedding
mode (started on demand on 127.0.0.1:8081); without that model a hashed bag-of-words
embedding keeps the search working (keyword-level). Queries are embedded the same way and
ranked by cosine similarity; results are grouped by month and folder.
"""
import datetime as _dt
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from . import settings as S

TEXT_EXT = {".txt", ".md", ".rst", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv",
            ".html", ".htm", ".css", ".c", ".h", ".cpp", ".rs", ".go", ".java", ".tex", ".org", ".log"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".tif", ".tiff", ".svg"}
DOC_EXT = {".pdf", ".odt", ".docx", ".doc", ".pptx", ".odp", ".xlsx", ".ods"}
AUDIO_EXT = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus"}
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".cache", "venv", ".venv", "site-packages"}
MAX_FILES = 20000
Embedder = Callable[[Sequence[str]], List[List[float]]]


def kind_of(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT:
        return "photo"
    if ext in TEXT_EXT:
        return "text"
    if ext in DOC_EXT:
        return "document"
    if ext in AUDIO_EXT:
        return "music"
    if ext in VIDEO_EXT:
        return "video"
    return "file"


def default_roots() -> List[str]:
    home = os.path.expanduser("~")
    roots = [os.path.join(home, d) for d in ("Documents", "Desktop", "Downloads", "Pictures", "Music", "Videos", "Projects", "Notes")]
    return [r for r in roots if os.path.isdir(r)]


def describe(path: str, mtime: float, kind: str, content: str = "") -> str:
    """The text that stands for a file: words from its name and folders, its month, its content."""
    name = os.path.splitext(os.path.basename(path))[0]
    words = re.sub(r"[_\-\.]+", " ", name)
    words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", words)
    folders = " ".join(p for p in os.path.dirname(path).split(os.sep)[-3:] if p and p not in ("home", os.environ.get("USER", "")))
    when = _dt.datetime.fromtimestamp(mtime).strftime("%B %Y")
    return f"{kind}: {words}. folder {folders}. {when}. {content[:1500]}".strip()


def read_text(path: str, limit: int = 4000) -> str:
    try:
        with open(path, "rb") as f:
            raw = f.read(limit)
        return raw.decode("utf-8", "ignore")
    except OSError:
        return ""


# ------------------------------------------------------------------------ embedders
class HashEmbedder:
    """Hashed bag of words with bigrams, 256 dims, unit length. Needs no model."""

    dims = 256

    def __call__(self, texts: Sequence[str]) -> List[List[float]]:
        out = []
        for t in texts:
            toks = re.findall(r"[a-z0-9]+", t.lower())
            vec = [0.0] * self.dims
            grams = toks + [a + "_" + b for a, b in zip(toks, toks[1:])]
            for g in grams:
                h = int(hashlib.blake2b(g.encode(), digest_size=4).hexdigest(), 16)
                vec[h % self.dims] += 1.0 if "_" not in g else 0.5
            n = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / n for v in vec])
        return out


class LlamaEmbedder:
    """bge-small through llama-server --embedding (OpenAI-compatible /v1/embeddings)."""

    def __init__(self, url: Optional[str] = None, model_path: Optional[str] = None):
        self.url = url or os.environ.get("ETERNITY_EMBED_URL", "http://127.0.0.1:8081")
        self.model_path = model_path or os.path.join(os.environ.get("ETERNITY_MODELS_DIR", "/opt/eternity/models"), "embed.gguf")

    def available(self) -> bool:
        return os.path.exists(self.model_path) and shutil.which("llama-server") is not None

    def healthy(self, timeout=0.8) -> bool:
        try:
            with urllib.request.urlopen(self.url + "/health", timeout=timeout) as r:
                return r.status == 200
        except Exception:
            return False

    def ensure_running(self, wait_s: float = 60.0) -> bool:
        if self.healthy():
            return True
        if not self.available():
            return False
        port = self.url.rsplit(":", 1)[-1].strip("/")
        cmd = [shutil.which("llama-server"), "-m", self.model_path, "--embedding", "--pooling", "cls", "--host", "127.0.0.1",
               "--port", port, "-c", "512", "-b", "512", "-ub", "512", "-t", str(max(1, (os.cpu_count() or 2) // 2)), "--log-disable"]
        if shutil.which("systemd-run") and os.environ.get("ETERNITY_NO_SYSTEMD_RUN") is None:
            cmd = ["systemd-run", "--user", "--quiet", "--collect", "--unit", "eternity-embed"] + cmd
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        t0 = time.monotonic()
        while time.monotonic() - t0 < wait_s:
            if self.healthy():
                return True
            time.sleep(0.4)
        return False

    def __call__(self, texts: Sequence[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for i in range(0, len(texts), 16):
            batch = [t[:1800] for t in texts[i:i + 16]]
            req = urllib.request.Request(self.url + "/v1/embeddings", data=json.dumps({"input": batch, "model": "embed"}).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)["data"]
            data.sort(key=lambda d: d.get("index", 0))
            for d in data:
                v = d["embedding"]
                n = math.sqrt(sum(x * x for x in v)) or 1.0
                out.append([x / n for x in v])
        return out


def best_embedder(prefer_model: bool = True) -> Embedder:
    if prefer_model:
        le = LlamaEmbedder()
        if le.available() and le.ensure_running():
            return le
    return HashEmbedder()


# ------------------------------------------------------------------------- the index
@dataclass
class Hit:
    path: str
    score: float
    kind: str
    mtime: float

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def when(self) -> str:
        return _dt.datetime.fromtimestamp(self.mtime).strftime("%d %b %Y")

    @property
    def month(self) -> str:
        return _dt.datetime.fromtimestamp(self.mtime).strftime("%B %Y")


def _pack(v: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(v)}f", *v)


def _unpack(b: bytes) -> List[float]:
    return list(struct.unpack(f"<{len(b) // 4}f", b))


class Index:
    def __init__(self, path: Optional[str] = None, embedder: Optional[Embedder] = None):
        self.path = path or os.path.join(S.state_dir(), "index.sqlite")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # the GTK windows call build() and search() from worker threads
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.lock = threading.RLock()
        self.db.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, mtime REAL, size INTEGER, kind TEXT, embedder TEXT, vec BLOB)")
        self.db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        self.embedder = embedder
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    @property
    def embedder_name(self) -> str:
        return type(self.embedder).__name__ if self.embedder else "none"

    def _emb(self) -> Embedder:
        if self.embedder is None:
            self.embedder = best_embedder()
        return self.embedder

    def scan(self, roots: Optional[Iterable[str]] = None) -> List[str]:
        files = []
        for root in (roots or default_roots()):
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
                for fn in filenames:
                    if fn.startswith("."):
                        continue
                    files.append(os.path.join(dirpath, fn))
                    if len(files) >= MAX_FILES:
                        return files
        return files

    def build(self, roots: Optional[Iterable[str]] = None, progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, int]:
        """Index new and changed files, drop vanished ones. Returns counts."""
        with self.lock:
            return self._build(roots, progress)

    def _build(self, roots, progress) -> Dict[str, int]:
        emb = self._emb()
        name = self.embedder_name
        present = self.scan(roots)
        known = {row[0]: (row[1], row[2], row[3]) for row in self.db.execute("SELECT path, mtime, size, embedder FROM files")}
        todo = []
        for p in present:
            try:
                st = os.stat(p)
            except OSError:
                continue
            k = known.get(p)
            if k and abs(k[0] - st.st_mtime) < 1 and k[1] == st.st_size and k[2] == name:
                continue
            todo.append((p, st.st_mtime, st.st_size))
        gone = set(known) - set(present)
        if gone:
            self.db.executemany("DELETE FROM files WHERE path = ?", [(g,) for g in gone])
        done = 0
        for i in range(0, len(todo), 32):
            batch = todo[i:i + 32]
            texts = []
            for p, mt, sz in batch:
                kind = kind_of(p)
                content = read_text(p) if kind == "text" and sz < 2_000_000 else ""
                texts.append(describe(p, mt, kind, content))
            vecs = emb(texts)
            self.db.executemany("INSERT OR REPLACE INTO files (path, mtime, size, kind, embedder, vec) VALUES (?,?,?,?,?,?)",
                                [(p, mt, sz, kind_of(p), name, _pack(v)) for (p, mt, sz), v in zip(batch, vecs)])
            self.db.commit()
            done += len(batch)
            if progress:
                progress(done, len(todo))
        self.db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('built', ?)", (str(time.time()),))
        self.db.commit()
        return {"indexed": done, "removed": len(gone), "total": self.db.execute("SELECT COUNT(*) FROM files").fetchone()[0]}

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    def search(self, query: str, k: int = 24) -> List[Hit]:
        with self.lock:
            return self._search(query, k)

    def _search(self, query: str, k: int) -> List[Hit]:
        emb = self._emb()
        name = self.embedder_name
        q = emb([f"query: {query}"])[0]
        rows = self.db.execute("SELECT path, mtime, kind, vec FROM files WHERE embedder = ?", (name,)).fetchall()
        hits = []
        for path, mtime, kind, blob in rows:
            v = _unpack(blob)
            if len(v) != len(q):
                continue
            score = sum(a * b for a, b in zip(q, v))
            hits.append(Hit(path, score, kind, mtime))
        hits.sort(key=lambda h: h.score, reverse=True)
        # keyword boost: a name containing a query word always ranks above pure vector neighbours
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2]
        for h in hits:
            low = h.path.lower()
            h.score += 0.15 * sum(1 for w in words if w in low)
        hits.sort(key=lambda h: h.score, reverse=True)
        if hits and words:
            # keep the tail honest: drop results far below the best one
            top = hits[0].score
            hits = [h for h in hits if h.score >= top * 0.55]
        return hits[:k]


def group(hits: List[Hit]) -> Dict[str, object]:
    months: Dict[str, int] = {}
    folders: Dict[str, int] = {}
    kinds: Dict[str, int] = {}
    for h in hits:
        months[h.month] = months.get(h.month, 0) + 1
        folders[os.path.dirname(h.path)] = folders.get(os.path.dirname(h.path), 0) + 1
        kinds[h.kind] = kinds.get(h.kind, 0) + 1
    top_month = max(months, key=months.get) if months else ""
    top_folder = max(folders, key=folders.get) if folders else ""
    top_kind = max(kinds, key=kinds.get) if kinds else "file"
    return {"matches": len(hits), "folders": len(folders), "months": len(months), "top_month": top_month,
            "top_folder": top_folder, "top_kind": top_kind}


def suggestion(g: Dict[str, object]) -> str:
    if not g.get("matches"):
        return "Nothing close enough. Try other words, or index more folders in Settings."
    folder = os.path.basename(str(g["top_folder"])) or "your files"
    kind = {"photo": "photos", "text": "notes", "document": "documents", "music": "tracks", "video": "videos"}.get(str(g["top_kind"]), "files")
    return f"Most of these {kind} are in {folder}, from {g['top_month']}. Want to open that folder?"


def header(g: Dict[str, object], ms: float) -> str:
    return f"Grouped by Eternity  ·  {g['matches']} matches  ·  {g['folders']} folders  ·  {g['top_month']}  ·  {ms:.0f} ms"
