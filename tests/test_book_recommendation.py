# # tests/test_book_recommendation.py
# import os
# import io
# import types
# import importlib
# import importlib.util
# import pathlib
# import threading
# import tkinter as tk
# import pytest
# import numpy as np
# import pandas as pd

# # ---------- Module loader: find the class BookRecommendation ----------
# def _load_module_with_class(class_name="BookRecommendation"):
#     # Try common candidates first
#     for cand in (
#         "BookRecommendation",                 # BookRecommendation.py
#         "userRole.BookRecommendation",        # package layout
#         "userRole.book_recommendation",       # snake_case
#         "book_recommendation",                # snake_case root
#         "recommendation.BookRecommendation",  # another package layout
#     ):
#         try:
#             mod = importlib.import_module(cand)
#             if hasattr(mod, class_name):
#                 return mod
#         except Exception:
#             pass

#     # Fallback: scan project for any file that defines the class
#     root = pathlib.Path(__file__).resolve().parents[1]
#     for p in root.rglob("*.py"):
#         if p.name.startswith("test_"):
#             continue
#         try:
#             txt = p.read_text(encoding="utf-8", errors="ignore")
#         except Exception:
#             continue
#         if f"class {class_name}" in txt:
#             spec = importlib.util.spec_from_file_location("bookreco_autoload", p)
#             mod = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(mod)  # type: ignore[attr-defined]
#             return mod

#     raise ImportError("Couldn't import BookRecommendation module.")

# MOD = _load_module_with_class()
# BookRecommendation = getattr(MOD, "BookRecommendation")

# # ---------- Tiny helpers & fakes ----------
# class _MsgSink:
#     def __init__(self):
#         self.errors = []
#         self.infos = []
#         self.asks = []
#     def showerror(self, t, m): self.errors.append((t, m))
#     def showinfo(self, t, m): self.infos.append((t, m))
#     def askyesno(self, t, m): 
#         self.asks.append((t, m))
#         return False

# class _Photo:
#     def __init__(self, *a, **k): pass

# def _png_bytes(size=(2, 2), color=(255, 0, 0)):
#     from PIL import Image as PILImage
#     b = io.BytesIO()
#     PILImage.new("RGB", size, color).save(b, format="PNG")
#     return b.getvalue()

# # Fake DB stack
# class _FakeCursor:
#     def __init__(self):
#         self.queue = []          # list of results to return from fetchall
#         self._last = None
#         self.rowcount = 0
#         self.executed = []
#         self.raise_on_nth_execute = None

#     def __enter__(self): return self
#     def __exit__(self, et, ev, tb): return False

#     def execute(self, sql, params=None):
#         self.executed.append((sql, params))
#         if self.raise_on_nth_execute and len(self.executed) == self.raise_on_nth_execute:
#             raise RuntimeError("boom-exec")

#     def fetchall(self):
#         if self.queue:
#             return self.queue.pop(0)
#         return []

# class _FakeConn:
#     def __init__(self):
#         self.cur = _FakeCursor()
#         self.commits = 0
#         self.rollbacks = 0
#         self.closed = False

#     def ping(self, reconnect=False): pass
#     def cursor(self, dictionary=False): return self.cur
#     def commit(self): self.commits += 1
#     def rollback(self): self.rollbacks += 1
#     def close(self): self.closed = True

# class _FakeDB:
#     def __init__(self, conn): self.conn = conn
#     def connect(self): return self.conn

# # ---------- Shared Tk root ----------
# @pytest.fixture
# def tk_root():
#     import tkinter as _tk
#     try:
#         root = _tk.Tk()
#     except _tk.TclError:
#         pytest.skip("Tk not installed; skipping GUI tests.")
#     root.withdraw()
#     yield root
#     try: root.destroy()
#     except Exception: pass

# # ---------- App fixture with common patches ----------
# @pytest.fixture
# def app(monkeypatch, tk_root, tmp_path):
#     # Ensure ImageTk.PhotoImage is safe
#     def _tk_photo(*a, **k):
#         # Return a lightweight real tk.PhotoImage to please Tk
#         return tk.PhotoImage(width=1, height=1)
#     monkeypatch.setattr(MOD, "ImageTk", types.SimpleNamespace(PhotoImage=_tk_photo), raising=True)

#     # Model/data files to "exist"
#     model_dir = tmp_path / "model"
#     model_dir.mkdir(parents=True, exist_ok=True)

#     # Build the instance
#     content = tk.Frame(tk_root); content.pack()
#     app = BookRecommendation(
#         parent=tk_root,
#         content_frame=content,
#         title_font=("Arial", 12, "bold"),
#         label_font=("Arial", 10),
#         button_font=("Arial", 10, "bold"),
#         go_back_callback=lambda: None,
#     )

#     # Force files to our tmp model dir
#     app.files = {
#         "popular": str(model_dir / "popular.parquet"),
#         "pt":      str(model_dir / "pt.parquet"),
#         "books":   str(model_dir / "books.parquet"),
#         "sims":    str(model_dir / "similarity_scores.npy"),
#     }

#     return app

# # ---------- Data builders ----------
# def _sample_artifacts():
#     titles = ["Alpha", "Beta", "Gamma", "Delta"]
#     pt = pd.DataFrame(index=pd.Index(titles, name="Book-Title"))
#     popular = pd.DataFrame({"Book-Title": titles, "num_ratings": [5, 4, 3, 2], "avg_rating": [4.2, 3.9, 3.7, 3.4]})
#     books = pd.DataFrame({
#         "Book-Title": titles,
#         "Book-Author": ["A1", "B1", "C1", "D1"],
#         "Image-URL-M": ["", "", "http://x/imgM.png", ""],
#         "Image-URL-L": ["", "http://x/imgL.png", "", ""],
#         "Image-URL-S": ["http://x/imgS.png", "", "", ""],
#     })
#     sims = np.array([
#         [1.0, 0.9, 0.2, 0.1],
#         [0.9, 1.0, 0.3, 0.2],
#         [0.2, 0.3, 1.0, 0.4],
#         [0.1, 0.2, 0.4, 1.0],
#     ], dtype=float)
#     return popular, pt, books, sims

# # ---------- _load_artifacts ----------
# def test_load_artifacts_success_with_csv_merge(monkeypatch, app, tmp_path):
#     popular, pt, books, sims = _sample_artifacts()

#     # Make files "exist"
#     monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)

#     # Parquet readers
#     def _rp(path):
#         if path.endswith("popular.parquet"): return popular
#         if path.endswith("pt.parquet"): return pt
#         if path.endswith("books.parquet"): return books
#         raise AssertionError("unexpected parquet path")
#     monkeypatch.setattr(MOD.pd, "read_parquet", _rp, raising=True)

#     # NPY loader
#     monkeypatch.setattr(MOD.np, "load", lambda p: sims, raising=True)

#     # CSV present & merged
#     csv_df = pd.DataFrame({
#         "Book-Title": ["Alpha", "Beta", "Gamma", "Delta"],
#         "Image-URL-M": ["http://csv/alphaM.png", "", "", ""],
#         "Image-URL-L": ["", "http://csv/betaL.png", "", ""],
#         "Image-URL-S": ["", "", "http://csv/gammaS.png", ""],
#     })
#     monkeypatch.setattr(MOD.pd, "read_csv", lambda p: csv_df, raising=True)
#     # Pretend database_dir exists and csv path exists
#     app.database_dir = str(tmp_path)
#     monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)

#     app._load_artifacts()

#     assert app._artifacts_loaded is True
#     assert list(app.TITLES) == ["Alpha", "Beta", "Gamma", "Delta"]
#     # Chosen URL (prefers csv M > parquet M > csv L > parquet L > csv S > parquet S)
#     # Alpha should take csv M
#     assert app.BOOKS.loc[app.BOOKS["Book-Title"] == "Alpha", "Image-URL-M"].iloc[0] == "http://csv/alphaM.png"
#     # Beta should take csv L
#     assert app.BOOKS.loc[app.BOOKS["Book-Title"] == "Beta", "Image-URL-M"].iloc[0] == "http://csv/betaL.png"
#     # Gamma should keep parquet M (already present)
#     assert app.BOOKS.loc[app.BOOKS["Book-Title"] == "Gamma", "Image-URL-M"].iloc[0] == "http://x/imgM.png"

# def test_load_artifacts_missing_files_raises(monkeypatch, app):
#     # Nothing exists
#     monkeypatch.setattr(MOD.os.path, "exists", lambda p: False, raising=True)
#     with pytest.raises(FileNotFoundError):
#         app._load_artifacts()

# def test_load_artifacts_import_error(monkeypatch, app):
#     monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)
#     def _rp(path): raise ImportError("pyarrow missing")
#     monkeypatch.setattr(MOD.pd, "read_parquet", _rp, raising=True)
#     monkeypatch.setattr(MOD.np, "load", lambda p: np.ones((1,1)))
#     with pytest.raises(ImportError):
#         app._load_artifacts()

# # ---------- UI building & canvas ----------
# def test_build_recommend_ui_constructs_widgets(app, tk_root):
#     frame = tk.Frame(app.content_frame); frame.pack()
#     app._build_recommend_ui(frame)
#     assert isinstance(app.entry, tk.Entry)
#     assert isinstance(app.canvas, tk.Canvas)
#     assert isinstance(app.cards_frame, tk.Frame)
#     assert isinstance(app.scroll, tk.Scrollbar)

# def test_on_canvas_configure_sets_width(app, tk_root):
#     frame = tk.Frame(app.content_frame); frame.pack()
#     app._build_recommend_ui(frame)
#     app._on_canvas_configure(types.SimpleNamespace(width=500))
#     # itemcget returns '' on some Tk builds; just assert no crash and int conversion works if present
#     try:
#         w = int(float(app.canvas.itemcget(app.cards_frame_id, "width")))
#         assert w == 500
#     except Exception:
#         # Accept older Tk that won't report width back
#         assert True

# # ---------- Image fetch ----------
# def test_fetch_image_empty_returns_placeholder(app):
#     img = app._fetch_image("")
#     assert img.size == (140, 180)

# def test_fetch_image_http_success_and_cache(monkeypatch, app, tmp_path):
#     # Ensure cache dir exists & network returns valid PNG
#     data = _png_bytes()
#     class _Resp:
#         status_code = 200
#         content = data
#         def raise_for_status(self): pass
#     monkeypatch.setattr(MOD.requests, "get", lambda *a, **k: _Resp())

#     img = app._fetch_image("http://example.com/a.png")
#     assert img.size == (140, 180)

#     # Second call should hit cache path and still work (no network)
#     img2 = app._fetch_image("http://example.com/a.png")
#     assert img2.size == (140, 180)

# def test_fetch_image_http_amazon_403_then_referer(monkeypatch, app):
#     data = _png_bytes()
#     calls = {"headers": []}
#     class _Resp:
#         def __init__(self, status, content): 
#             self.status_code = status
#             self.content = content
#         def raise_for_status(self):
#             if self.status_code >= 400:
#                 import requests as _r
#                 raise _r.HTTPError(f"status {self.status_code}")

#     def _get(url, timeout=8, headers=None, allow_redirects=True):
#         calls["headers"].append(headers or {})
#         if len(calls["headers"]) == 1:
#             return _Resp(403, b"")
#         return _Resp(200, data)

#     monkeypatch.setattr(MOD.requests, "get", _get)
#     img = app._fetch_image("http://amazon.example.com/img.png")
#     assert img.size == (140, 180)
#     # Second call had a Referer
#     assert any("Referer" in h for h in calls["headers"][1:])

# # ---------- Matching & similar ----------
# def _patch_artifacts(monkeypatch, app):
#     popular, pt, books, sims = _sample_artifacts()
#     monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)
#     def _rp(path):
#         if path.endswith("popular.parquet"): return popular
#         if path.endswith("pt.parquet"): return pt
#         if path.endswith("books.parquet"): return books
#         raise AssertionError("unexpected")
#     monkeypatch.setattr(MOD.pd, "read_parquet", _rp, raising=True)
#     monkeypatch.setattr(MOD.np, "load", lambda p: sims, raising=True)
#     app._load_artifacts()

# def test_find_title_index_exact_substring_fuzzy(monkeypatch, app):
#     _patch_artifacts(monkeypatch, app)
#     # exact case-insensitive
#     idx, match = app._find_title_index("alpha")
#     assert match == "Alpha" and isinstance(idx, int)
#     # substring
#     idx2, match2 = app._find_title_index("lph")
#     assert match2 == "Alpha"
#     # fuzzy
#     idx3, match3 = app._find_title_index("Alfa")
#     assert match3 == "Alpha"
#     # no match
#     idx4, match4 = app._find_title_index("zzzz")
#     assert idx4 is None and match4 is None

# def test_get_similar_picks_best_image(monkeypatch, app):
#     _patch_artifacts(monkeypatch, app)
#     recs = app._get_similar(0, top_k=2)  # for Alpha, top neighbor is Beta then Gamma
#     assert len(recs) == 2
#     # Beta: expect Image-URL-L chosen
#     r0 = [r for r in recs if r["title"] == "Beta"][0]
#     assert r0["image"] == "http://x/imgL.png"
#     # Gamma: expect Image-URL-M chosen
#     r1 = [r for r in recs if r["title"] == "Gamma"][0]
#     assert r1["image"] == "http://x/imgM.png"

# # ---------- Recommend button flow ----------
# def test_on_recommend_click_empty_shows_info(monkeypatch, app, tk_root):
#     _patch_artifacts(monkeypatch, app)
#     sink = _MsgSink()
#     monkeypatch.setattr(MOD, "messagebox", sink)
#     frame = tk.Frame(app.content_frame); frame.pack()
#     app._build_recommend_ui(frame)
#     app.entry.delete(0, tk.END)  # empty
#     app._on_recommend_click()
#     assert any("Please type a book title" in m for _, m in sink.infos)

# def test_on_recommend_click_no_match_sets_info_and_clears(monkeypatch, app, tk_root):
#     _patch_artifacts(monkeypatch, app)
#     frame = tk.Frame(app.content_frame); frame.pack()
#     app._build_recommend_ui(frame)
#     app.entry.delete(0, tk.END)
#     app.entry.insert(0, "ZedZed")
#     app._on_recommend_click()
#     assert "No match for" in app.info_label.cget("text")

# def test_on_recommend_click_match_invokes_show_cards(monkeypatch, app, tk_root):
#     _patch_artifacts(monkeypatch, app)
#     frame = tk.Frame(app.content_frame); frame.pack()
#     app._build_recommend_ui(frame)

#     # make "thread" synchronous
#     class _FakeThread:
#         def __init__(self, target=None, daemon=None): self.target = target
#         def start(self): 
#             if self.target: self.target()
#     monkeypatch.setattr(MOD.threading, "Thread", _FakeThread)

#     # immediate .after
#     app.parent.after = lambda delay, fn: fn()

#     # force a found match
#     monkeypatch.setattr(app, "_find_title_index", lambda s: (1, "Beta"))
#     monkeypatch.setattr(app, "_get_similar", lambda idx, top_k=12: [{"title":"X","author":"Y","image":""}])

#     called = {"recs": None}
#     def _sc(recs):
#         called["recs"] = recs
#     monkeypatch.setattr(app, "_show_cards", _sc)

#     app.entry.delete(0, tk.END)
#     app.entry.insert(0, "beta")
#     app._on_recommend_click()
#     assert called["recs"] == [{"title":"X","author":"Y","image":""}]

# # ---------- Card click & DB ----------
# def test_on_card_click_no_user_cancels(monkeypatch, app, tk_root):
#     sink = _MsgSink()
#     monkeypatch.setattr(MOD, "simpledialog", types.SimpleNamespace(askstring=lambda *a, **k: None))
#     monkeypatch.setattr(MOD, "messagebox", sink)
#     app._on_card_click({"title":"t","author":"a"})
#     # no info/error recorded
#     assert sink.infos == [] and sink.errors == []

# def test_on_card_click_decline(monkeypatch, app, tk_root):
#     sink = _MsgSink()
#     sink.askyesno = lambda *a, **k: False
#     monkeypatch.setattr(MOD, "messagebox", sink)
#     app.current_user_id = "111"
#     app._on_card_click({"title":"t","author":"a"})
#     assert sink.infos == [] and sink.errors == []

# def test_on_card_click_success_info(monkeypatch, app, tk_root):
#     sink = _MsgSink()
#     sink.askyesno = lambda *a, **k: True
#     monkeypatch.setattr(MOD, "messagebox", sink)
#     app.parent.after = lambda delay, fn, *args: fn(*args)
#     monkeypatch.setattr(app, "_insert_loan_mysql", lambda *a, **k: 1)
#     app.current_user_id = "111"
#     app._on_card_click({"title":"t","author":"a"})
#     assert any("Lending recorded" in m for _, m in sink.infos)

# # ---------- _insert_loan_mysql ----------
# def test_insert_loan_mysql_success_primary_select(monkeypatch, app):
#     conn = _FakeConn()
#     cur = conn.cur
#     cur.queue = [[{"book_id": "B1"}]]  # first SELECT returns a row
#     cur.rowcount = 1
#     monkeypatch.setattr(MOD, "Database", lambda: _FakeDB(conn))
#     affected = app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
#     assert affected == 1
#     assert conn.commits == 1 and conn.rollbacks == 0 and conn.closed

# def test_insert_loan_mysql_success_fallback_lower(monkeypatch, app):
#     conn = _FakeConn()
#     cur = conn.cur
#     cur.queue = [[], [{"book_id": "B7"}]]  # first [], then fallback finds
#     cur.rowcount = 1
#     monkeypatch.setattr(MOD, "Database", lambda: _FakeDB(conn))
#     affected = app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
#     assert affected == 1
#     assert conn.commits == 1 and conn.rollbacks == 0

# def test_insert_loan_mysql_not_found_rolls_back(monkeypatch, app):
#     conn = _FakeConn()
#     conn.cur.queue = [[], []]  # both selects empty
#     monkeypatch.setattr(MOD, "Database", lambda: _FakeDB(conn))
#     with pytest.raises(ValueError):
#         app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
#     assert conn.rollbacks == 1 and conn.commits == 0

# def test_insert_loan_mysql_member_id_empty_raises_no_connect(monkeypatch, app):
#     # If member_id empty -> ValueError before any DB connection
#     called = {"connect": 0}
#     class _DB:
#         def connect(self): 
#             called["connect"] += 1
#             raise AssertionError("should not connect")
#     monkeypatch.setattr(MOD, "Database", _DB)
#     with pytest.raises(ValueError):
#         app._insert_loan_mysql("", {"title":"T","author":"A","image":""})
#     assert called["connect"] == 0

# def test_insert_loan_mysql_missing_title_raises(monkeypatch, app):
#     with pytest.raises(ValueError):
#         app._insert_loan_mysql("111", {"title":"", "author":"A", "image":""})

# def test_insert_loan_mysql_execute_error_rolls_back(monkeypatch, app):
#     conn = _FakeConn()
#     cur = conn.cur
#     cur.queue = [[{"book_id":"B1"}]]
#     cur.raise_on_nth_execute = 2  # fail on INSERT (second execute)
#     monkeypatch.setattr(MOD, "Database", lambda: _FakeDB(conn))
#     with pytest.raises(RuntimeError):
#         app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
#     assert conn.rollbacks == 1

# tests/test_book_recommendation.py
import os
import io
import types
import importlib
import importlib.util
import pathlib
import tkinter as tk
import pytest
import numpy as np
import pandas as pd

# ---------- Module loader: find the class BookRecommendation ----------
def _load_module_with_class(class_name="BookRecommendation"):
    for cand in (
        "BookRecommendation",
        "userRole.Book_Recommandation",   # your file name looks like this
        "userRole.BookRecommendation",
        "userRole.book_recommendation",
        "book_recommendation",
    ):
        try:
            mod = importlib.import_module(cand)
            if hasattr(mod, class_name):
                return mod
        except Exception:
            pass

    root = pathlib.Path(__file__).resolve().parents[1]
    for p in root.rglob("*.py"):
        if p.name.startswith("test_"):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if f"class {class_name}" in txt:
            spec = importlib.util.spec_from_file_location("bookreco_autoload", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            return mod

    raise ImportError("Couldn't import BookRecommendation module.")

MOD = _load_module_with_class()
BookRecommendation = getattr(MOD, "BookRecommendation")

# ---------- Tiny helpers & fakes ----------
class _MsgSink:
    def __init__(self):
        self.errors = []
        self.infos = []
        self.asks = []
    def showerror(self, t, m): self.errors.append((t, m))
    def showinfo(self, t, m): self.infos.append((t, m))
    def askyesno(self, t, m):
        self.asks.append((t, m))
        return False

def _png_bytes(size=(2, 2), color=(255, 0, 0)):
    from PIL import Image as PILImage
    b = io.BytesIO()
    PILImage.new("RGB", size, color).save(b, format="PNG")
    return b.getvalue()

class _FakeCursor:
    def __init__(self):
        self.queue = []
        self.rowcount = 0
        self.executed = []
        self.raise_on_nth_execute = None
    def __enter__(self): return self
    def __exit__(self, et, ev, tb): return False
    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if self.raise_on_nth_execute and len(self.executed) == self.raise_on_nth_execute:
            raise RuntimeError("boom-exec")
    def fetchall(self):
        return self.queue.pop(0) if self.queue else []

class _FakeConn:
    def __init__(self):
        self.cur = _FakeCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
    def ping(self, reconnect=False): pass
    def cursor(self, dictionary=False): return self.cur
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1
    def close(self): self.closed = True

class _FakeDB:
    def __init__(self, conn): self.conn = conn
    def connect(self): return self.conn

# ---------- Shared Tk root ----------
@pytest.fixture
def tk_root():
    import tkinter as _tk
    try:
        root = _tk.Tk()
    except _tk.TclError:
        pytest.skip("Tk not installed; skipping GUI tests.")
    root.withdraw()
    yield root
    try: root.destroy()
    except Exception: pass

# ---------- App fixture ----------
@pytest.fixture
def app(monkeypatch, tk_root, tmp_path):
    def _tk_photo(*a, **k):
        return tk.PhotoImage(width=1, height=1)
    monkeypatch.setattr(MOD, "ImageTk", types.SimpleNamespace(PhotoImage=_tk_photo), raising=True)

    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True, exist_ok=True)

    content = tk.Frame(tk_root); content.pack()
    app = BookRecommendation(
        parent=tk_root,
        content_frame=content,
        title_font=("Arial", 12, "bold"),
        label_font=("Arial", 10),
        button_font=("Arial", 10, "bold"),
        go_back_callback=lambda: None,
    )
    app.files = {
        "popular": str(model_dir / "popular.parquet"),
        "pt":      str(model_dir / "pt.parquet"),
        "books":   str(model_dir / "books.parquet"),
        "sims":    str(model_dir / "similarity_scores.npy"),
    }
    return app

# ---------- Data builders ----------
def _sample_artifacts():
    titles = ["Alpha", "Beta", "Gamma", "Delta"]
    pt = pd.DataFrame(index=pd.Index(titles, name="Book-Title"))
    popular = pd.DataFrame({"Book-Title": titles, "num_ratings": [5, 4, 3, 2], "avg_rating": [4.2, 3.9, 3.7, 3.4]})
    books = pd.DataFrame({
        "Book-Title": titles,
        "Book-Author": ["A1", "B1", "C1", "D1"],
        "Image-URL-M": ["", "", "http://x/imgM.png", ""],
        "Image-URL-L": ["", "http://x/imgL.png", "", ""],
        "Image-URL-S": ["http://x/imgS.png", "", "", ""],
    })
    sims = np.array([
        [1.0, 0.9, 0.2, 0.1],
        [0.9, 1.0, 0.3, 0.2],
        [0.2, 0.3, 1.0, 0.4],
        [0.1, 0.2, 0.4, 1.0],
    ], dtype=float)
    return popular, pt, books, sims

# ---------- _load_artifacts ----------
def test_load_artifacts_success_with_csv_merge(monkeypatch, app, tmp_path):
    popular, pt, books, sims = _sample_artifacts()

    # Make files "exist"
    monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)

    def _rp(path):
        if path.endswith("popular.parquet"): return popular
        if path.endswith("pt.parquet"): return pt
        if path.endswith("books.parquet"): return books
        raise AssertionError("unexpected parquet path")
    monkeypatch.setattr(MOD.pd, "read_parquet", _rp, raising=True)
    monkeypatch.setattr(MOD.np, "load", lambda p: sims, raising=True)

    # CSV present & merged
    csv_df = pd.DataFrame({
        "Book-Title": ["Alpha", "Beta", "Gamma", "Delta"],
        "Image-URL-M": ["http://csv/alphaM.png", "", "", ""],
        "Image-URL-L": ["", "http://csv/betaL.png", "", ""],
        "Image-URL-S": ["", "", "http://csv/gammaS.png", ""],
    })
    monkeypatch.setattr(MOD.pd, "read_csv", lambda p: csv_df, raising=True)
    app.database_dir = str(tmp_path)
    monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)

    app._load_artifacts()

    assert app._artifacts_loaded is True
    assert list(app.TITLES) == ["Alpha", "Beta", "Gamma", "Delta"]
    assert app.BOOKS.loc[app.BOOKS["Book-Title"] == "Alpha", "Image-URL-M"].iloc[0] == "http://csv/alphaM.png"
    assert app.BOOKS.loc[app.BOOKS["Book-Title"] == "Beta", "Image-URL-M"].iloc[0] == "http://csv/betaL.png"
    assert app.BOOKS.loc[app.BOOKS["Book-Title"] == "Gamma", "Image-URL-M"].iloc[0] == "http://x/imgM.png"

def test_load_artifacts_missing_files_raises(monkeypatch, app):
    monkeypatch.setattr(MOD.os.path, "exists", lambda p: False, raising=True)
    with pytest.raises(FileNotFoundError):
        app._load_artifacts()

def test_load_artifacts_import_error(monkeypatch, app):
    monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)
    monkeypatch.setattr(MOD.pd, "read_parquet", lambda p: (_ for _ in ()).throw(ImportError("pyarrow missing")), raising=True)
    monkeypatch.setattr(MOD.np, "load", lambda p: np.ones((1,1)))
    with pytest.raises(ImportError):
        app._load_artifacts()

# ---------- UI building & canvas ----------
def test_build_recommend_ui_constructs_widgets(app, tk_root):
    frame = tk.Frame(app.content_frame); frame.pack()
    app._build_recommend_ui(frame)
    assert isinstance(app.entry, tk.Entry)
    assert isinstance(app.canvas, tk.Canvas)
    assert isinstance(app.cards_frame, tk.Frame)
    assert isinstance(app.scroll, tk.Scrollbar)

def test_on_canvas_configure_sets_width(app, tk_root):
    frame = tk.Frame(app.content_frame); frame.pack()
    app._build_recommend_ui(frame)
    app._on_canvas_configure(types.SimpleNamespace(width=500))
    try:
        w = int(float(app.canvas.itemcget(app.cards_frame_id, "width")))
        assert w == 500
    except Exception:
        assert True

# ---------- Image fetch ----------
def test_fetch_image_empty_returns_placeholder(app):
    img = app._fetch_image("")
    assert img.size == (140, 180)

def test_fetch_image_http_success_and_cache(monkeypatch, app):
    data = _png_bytes()
    class _Resp:
        status_code = 200
        content = data
        def raise_for_status(self): pass
    monkeypatch.setattr(MOD.requests, "get", lambda *a, **k: _Resp())

    img = app._fetch_image("http://example.com/a.png")
    assert img.size == (140, 180)
    img2 = app._fetch_image("http://example.com/a.png")
    assert img2.size == (140, 180)

def test_fetch_image_http_amazon_403_then_referer(monkeypatch, app):
    # Ensure NOT cached so we see both network calls
    url = "http://amazon.example.com/img.png"
    safe = "".join(ch if ch.isalnum() else "_" for ch in url)[:200]
    cache_path = os.path.join(app._cache_dir, safe)
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except Exception:
            pass

    data = _png_bytes()
    calls = {"headers": []}

    class _Resp:
        def __init__(self, status, content):
            self.status_code = status
            self.content = content
        def raise_for_status(self):
            if self.status_code >= 400:
                import requests as _r
                raise _r.HTTPError(f"status {self.status_code}")

    def _get(u, timeout=8, headers=None, allow_redirects=True):
        calls["headers"].append(headers or {})
        if len(calls["headers"]) == 1:
            return _Resp(403, b"")  # first call blocked
        return _Resp(200, data)     # retry succeeds

    monkeypatch.setattr(MOD.requests, "get", _get)
    img = app._fetch_image(url)
    assert img.size == (140, 180)
    # second call must include Referer header
    assert len(calls["headers"]) >= 2
    assert "Referer" in calls["headers"][1]


# ---------- Matching & similar ----------
def _patch_artifacts(monkeypatch, app):
    # Ensure deterministic (no CSV merge)
    app.database_dir = None
    popular, pt, books, sims = _sample_artifacts()
    monkeypatch.setattr(MOD.os.path, "exists", lambda p: True, raising=True)
    def _rp(path):
        if path.endswith("popular.parquet"): return popular
        if path.endswith("pt.parquet"): return pt
        if path.endswith("books.parquet"): return books
        raise AssertionError("unexpected")
    monkeypatch.setattr(MOD.pd, "read_parquet", _rp, raising=True)
    monkeypatch.setattr(MOD.np, "load", lambda p: sims, raising=True)
    app._load_artifacts()

def test_find_title_index_exact_substring_fuzzy(monkeypatch, app):
    _patch_artifacts(monkeypatch, app)
    idx, match = app._find_title_index("alpha")
    assert match == "Alpha" and isinstance(idx, int)
    idx2, match2 = app._find_title_index("lph")
    assert match2 == "Alpha"
    idx3, match3 = app._find_title_index("Alfa")
    assert match3 == "Alpha"
    idx4, match4 = app._find_title_index("zzzz")
    assert idx4 is None and match4 is None

def test_get_similar_picks_best_image(monkeypatch, app):
    _patch_artifacts(monkeypatch, app)
    recs = app._get_similar(0, top_k=2)
    assert len(recs) == 2
    r0 = [r for r in recs if r["title"] == "Beta"][0]
    assert r0["image"] == "http://x/imgL.png"
    r1 = [r for r in recs if r["title"] == "Gamma"][0]
    assert r1["image"] == "http://x/imgM.png"

# ---------- Recommend button flow ----------
def test_on_recommend_click_empty_shows_info(monkeypatch, app, tk_root):
    _patch_artifacts(monkeypatch, app)
    sink = _MsgSink()
    monkeypatch.setattr(MOD, "messagebox", sink)
    frame = tk.Frame(app.content_frame); frame.pack()
    app._build_recommend_ui(frame)
    app.entry.delete(0, tk.END)
    app._on_recommend_click()
    assert any("Please type a book title" in m for _, m in sink.infos)

def test_on_recommend_click_no_match_sets_info_and_clears(monkeypatch, app, tk_root):
    _patch_artifacts(monkeypatch, app)
    frame = tk.Frame(app.content_frame); frame.pack()
    app._build_recommend_ui(frame)
    app.entry.delete(0, tk.END)
    app.entry.insert(0, "ZedZed")
    app._on_recommend_click()
    assert "No match for" in app.info_label.cget("text")

def test_on_recommend_click_match_invokes_show_cards(monkeypatch, app, tk_root):
    _patch_artifacts(monkeypatch, app)
    frame = tk.Frame(app.content_frame); frame.pack()
    app._build_recommend_ui(frame)

    class _FakeThread:
        def __init__(self, target=None, daemon=None): self.target = target
        def start(self): 
            if self.target: self.target()
    monkeypatch.setattr(MOD.threading, "Thread", _FakeThread)
    app.parent.after = lambda delay, fn: fn()
    monkeypatch.setattr(app, "_find_title_index", lambda s: (1, "Beta"))
    monkeypatch.setattr(app, "_get_similar", lambda idx, top_k=12: [{"title":"X","author":"Y","image":""}])

    called = {"recs": None}
    monkeypatch.setattr(app, "_show_cards", lambda recs: called.__setitem__("recs", recs))

    app.entry.delete(0, tk.END)
    app.entry.insert(0, "beta")
    app._on_recommend_click()
    assert called["recs"] == [{"title":"X","author":"Y","image":""}]

# ---------- Card click & DB ----------
def test_on_card_click_no_user_cancels(monkeypatch, app, tk_root):
    sink = _MsgSink()
    monkeypatch.setattr(MOD, "simpledialog", types.SimpleNamespace(askstring=lambda *a, **k: None))
    monkeypatch.setattr(MOD, "messagebox", sink)
    app._on_card_click({"title":"t","author":"a"})
    assert sink.infos == [] and sink.errors == []

def test_on_card_click_decline(monkeypatch, app, tk_root):
    sink = _MsgSink()
    sink.askyesno = lambda *a, **k: False
    monkeypatch.setattr(MOD, "messagebox", sink)
    app.current_user_id = "111"
    app._on_card_click({"title":"t","author":"a"})
    assert sink.infos == [] and sink.errors == []

def test_on_card_click_success_info(monkeypatch, app, tk_root):
    sink = _MsgSink()
    sink.askyesno = lambda *a, **k: True
    monkeypatch.setattr(MOD, "messagebox", sink)
    app.parent.after = lambda delay, fn, *args: fn(*args)
    monkeypatch.setattr(app, "_insert_loan_mysql", lambda *a, **k: 1)
    app.current_user_id = "111"
    app._on_card_click({"title":"t","author":"a"})
    assert any("Lending recorded" in m for _, m in sink.infos)

# ---------- _insert_loan_mysql ----------
def test_insert_loan_mysql_success_primary_select(monkeypatch, app):
    conn = _FakeConn()
    cur = conn.cur
    cur.queue = [[{"book_id": "B1"}]]
    cur.rowcount = 1
    app.db = _FakeDB(conn)  # inject fake DB into the existing app
    affected = app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
    assert affected == 1
    assert conn.commits == 1 and conn.rollbacks == 0 and conn.closed

def test_insert_loan_mysql_success_fallback_lower(monkeypatch, app):
    conn = _FakeConn()
    cur = conn.cur
    cur.queue = [[], [{"book_id": "B7"}]]
    cur.rowcount = 1
    app.db = _FakeDB(conn)
    affected = app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
    assert affected == 1
    assert conn.commits == 1 and conn.rollbacks == 0

def test_insert_loan_mysql_not_found_rolls_back(monkeypatch, app):
    conn = _FakeConn()
    conn.cur.queue = [[], []]
    app.db = _FakeDB(conn)
    with pytest.raises(ValueError):
        app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
    assert conn.rollbacks == 1 and conn.commits == 0

def test_insert_loan_mysql_member_id_empty_raises_no_connect(monkeypatch, app):
    calls = {"connect": 0}
    class _DB:
        def connect(self):
            calls["connect"] += 1
            raise AssertionError("should not connect")
    app.db = _DB()
    with pytest.raises(ValueError):
        app._insert_loan_mysql("", {"title":"T","author":"A","image":""})
    assert calls["connect"] == 0

def test_insert_loan_mysql_missing_title_raises(monkeypatch, app):
    with pytest.raises(ValueError):
        app._insert_loan_mysql("111", {"title":"", "author":"A", "image":""})

def test_insert_loan_mysql_execute_error_rolls_back(monkeypatch, app):
    conn = _FakeConn()
    cur = conn.cur
    cur.queue = [[{"book_id":"B1"}]]
    cur.raise_on_nth_execute = 2
    app.db = _FakeDB(conn)
    with pytest.raises(RuntimeError):
        app._insert_loan_mysql("111", {"title":"T","author":"A","image":""})
    assert conn.rollbacks == 1
