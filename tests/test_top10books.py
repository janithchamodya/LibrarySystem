# tests/test_top10books.py
import os
import io
import tempfile
import tkinter as tk
import pytest

# ---- Robust import for the app under test -----------------------------------
try:
    from userRole.Top10_Books import Top10_Books
    T10MOD = __import__("userRole.top10books", fromlist=["*"])
except Exception:
    from top10books import Top10_Books
    T10MOD = __import__("top10books", fromlist=["*"])


# ---- Test fakes --------------------------------------------------------------

class MsgSink:
    def __init__(self):
        self.infos, self.warnings, self.errors, self.prompts = [], [], [], []
        self._askyes = True
    def showinfo(self, t, m): self.infos.append((t, m))
    def showwarning(self, t, m): self.warnings.append((t, m))
    def showerror(self, t, m): self.errors.append((t, m))
    def askyesno(self, t, m): 
        self.prompts.append((t, m))
        return self._askyes

class DialogStub:
    def __init__(self, value=None):
        self.value = value
    def askstring(self, *a, **k): return self.value

def _mk_pil_image_bytes(w=4, h=4):
    from PIL import Image
    img = Image.new("RGB", (w, h), color=(123, 45, 67))
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()

class FakeCursorCM:
    """Context-manager cursor; control fetchall() via .queue (list of lists)."""
    def __init__(self):
        self.queue = []          # e.g. [[{"book_id":"1"}], []]
        self.rowcount = 0
        self.executed = []
        self.raise_on_execute = None
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False
    def execute(self, sql, params=None):
        if self.raise_on_execute:
            raise self.raise_on_execute
        self.executed.append((sql, params))
    def fetchall(self):
        return self.queue.pop(0) if self.queue else []
    # For _load_artifacts->not used, but keep for symmetry

class FakeConn:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.cur = FakeCursorCM()
    def ping(self, reconnect=False): pass
    def cursor(self, dictionary=False): return self.cur
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1
    def close(self): self.closed += 1

class FakeDB:
    def __init__(self, conn): self._conn = conn
    def connect(self): return self._conn


# ---- Fixtures ----------------------------------------------------------------

@pytest.fixture
def tk_root():
    """Safe Tk root; skip if Tk isn't available on machine."""
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk not installed properly on this machine; skipping GUI test.")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass

@pytest.fixture
def t10_app(monkeypatch, tk_root):
    # Patch DB with fake connection
    conn = FakeConn()
    monkeypatch.setattr(T10MOD, "Database", lambda: FakeDB(conn), raising=True)

    # Patch messagebox + simpledialog + PhotoImage
    sink = MsgSink()
    monkeypatch.setattr(T10MOD, "messagebox", sink, raising=True)
    dlg = DialogStub()
    monkeypatch.setattr(T10MOD, "simpledialog", dlg, raising=True)
    # Avoid needing a real Tk image object
    monkeypatch.setattr(T10MOD.ImageTk, "PhotoImage", lambda *a, **k: object(), raising=True)

    # Build instance
    cf = tk.Frame(tk_root); cf.pack()
    app = Top10_Books(
        parent=tk_root,
        content_frame=cf,
        title_font=("Arial", 14, "bold"),
        label_font=("Arial", 12),
        button_font=("Arial", 12, "bold"),
        go_back_callback=lambda: None,
    )

    # Expose fakes for assertions
    app._fake_conn = conn
    app._msg = sink
    app._dlg = dlg
    return app


# ---- Tests: _load_artifacts --------------------------------------------------

def test_load_artifacts_success_merges_images(monkeypatch, t10_app):
    import pandas as pd

    # Make os.path.exists true for both parquet files
    pop_path = t10_app.files["popular"]
    books_path = t10_app.files["books"]

    def fake_exists(p):
        return (p == pop_path) or (p == books_path)

    monkeypatch.setattr(T10MOD.os.path, "exists", fake_exists, raising=True)

    # POPULAR lacks "Image-URL-M" (forces merge)
    popular_df = pd.DataFrame({
        "Book-Title": ["T1", "T2", "T3"],
        "Book-Author": ["A1", "A2", "A3"],
        "num_ratings": [10, 20, 30],
        "avg_rating": [4.2, 4.3, 4.4],
    })
    books_df = pd.DataFrame({
        "Book-Title": ["T1", "T2", "T3"],
        "Image-URL-M": ["http://ex/t1.jpg", "http://ex/t2.jpg", "http://ex/t3.jpg"],
    })

    def fake_read_parquet(path):
        return books_df if path == books_path else popular_df

    monkeypatch.setattr(T10MOD.pd, "read_parquet", fake_read_parquet, raising=True)

    t10_app._load_artifacts()
    assert "Image-URL-M" in t10_app.TOP10.columns
    assert t10_app.TOP10["Image-URL-M"].notna().all()


def test_load_artifacts_missing_popular_raises(monkeypatch, t10_app):
    # Make popular file appear missing
    monkeypatch.setattr(T10MOD.os.path, "exists", lambda p: False, raising=True)
    with pytest.raises(FileNotFoundError):
        t10_app._load_artifacts()


def test_load_artifacts_missing_required_column(monkeypatch, t10_app):
    import pandas as pd
    # Exists returns True so we reach read_parquet
    monkeypatch.setattr(T10MOD.os.path, "exists", lambda p: True, raising=True)
    # Return df without 'num_ratings'
    bad_df = pd.DataFrame({"Book-Title": ["X"], "Book-Author": ["Y"], "avg_rating": [4.0]})
    monkeypatch.setattr(T10MOD.pd, "read_parquet", lambda p: bad_df, raising=True)
    with pytest.raises(ValueError):
        t10_app._load_artifacts()


# ---- Tests: show_top10 flow --------------------------------------------------

def test_show_top10_calls_cards_and_builds_ui(monkeypatch, t10_app):
    import pandas as pd

    # Stub loader to set TOP10
    def fake_load():
        t10_app.TOP10 = pd.DataFrame({
            "Book-Title": ["T1"],
            "Book-Author": ["A1"],
            "num_ratings": [11],
            "avg_rating": [4.4],
            "Image-URL-M": [""],
        })
    monkeypatch.setattr(t10_app, "_load_artifacts", fake_load, raising=True)

    # Capture records passed to _show_cards
    seen = {}
    monkeypatch.setattr(t10_app, "_top10_records", lambda: [{"title": "T1", "author": "A1"}], raising=True)
    def cap_show(recs):
        seen["recs"] = recs
    monkeypatch.setattr(t10_app, "_show_cards", cap_show, raising=True)

    t10_app.show_top10(member_id="007")
    assert seen["recs"] == [{"title": "T1", "author": "A1"}]
    # info_label created
    assert t10_app.info_label is not None


def test_show_top10_load_error_shows_messagebox(monkeypatch, t10_app):
    monkeypatch.setattr(t10_app, "_load_artifacts", lambda: (_ for _ in ()).throw(RuntimeError("boom")), raising=True)
    t10_app.show_top10(member_id="123")
    assert any("Failed to load Top 10 data" in m for _, m in t10_app._msg.errors)


# ---- Tests: _top10_records ---------------------------------------------------

def test_top10_records_formats_fields(t10_app):
    import pandas as pd
    t10_app.TOP10 = pd.DataFrame({
        "Book-Title": ["T1"],
        "Book-Author": ["A1"],
        "num_ratings": [5],
        "avg_rating": [3.9],
        "Image-URL-M": [float("nan")],  # becomes empty string
    })
    recs = t10_app._top10_records()
    assert recs == [{"title": "T1", "author": "A1", "image": "", "votes": "5", "rating": "3.9"}]


# ---- Tests: _fetch_image branches -------------------------------------------

def test_fetch_image_none_returns_placeholder(t10_app):
    img = t10_app._fetch_image(None, size=(10, 12))
    assert img.size == (10, 12)

def test_fetch_image_local_absolute(t10_app, tmp_path):
    # Write a tiny image file
    from PIL import Image
    p = tmp_path / "abs.png"
    Image.new("RGB", (3, 3), color=(1, 2, 3)).save(p)
    out = t10_app._fetch_image(str(p), size=(16, 16))
    assert out.size == (16, 16)

def test_fetch_image_relative_found_in_cwd(t10_app, tmp_path, monkeypatch):
    from PIL import Image
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        rel = "rel.png"
        Image.new("RGB", (3, 3), color=(4, 5, 6)).save(rel)
        out = t10_app._fetch_image(rel, size=(13, 15))
        assert out.size == (13, 15)
    finally:
        os.chdir(old_cwd)

def test_fetch_image_http_success_and_cache(monkeypatch, t10_app, tmp_path):
    # Point cache to a temp dir so we can observe writes
    t10_app._cache_dir = tmp_path.as_posix()
    url = "http://example.com/pic.png"  # will be upgraded to https

    calls = {"n": 0, "last_headers": None}
    def fake_get(u, headers=None, timeout=None):
        calls["n"] += 1
        calls["last_headers"] = headers
        class R:
            status_code = 200
            ok = True
            content = _mk_pil_image_bytes(5, 5)
            def raise_for_status(self): return None
        return R()
    monkeypatch.setattr(T10MOD.requests, "get", fake_get, raising=True)

    img1 = t10_app._fetch_image(url, size=(20, 20))
    assert img1.size == (20, 20)
    # Cached second time (no extra HTTP call)
    img2 = t10_app._fetch_image(url, size=(20, 20))
    assert img2.size == (20, 20)
    assert calls["n"] == 1  # only first call fetched
    # UA header present
    assert "User-Agent" in calls["last_headers"]

def test_fetch_image_http_amazon_referer(monkeypatch, t10_app, tmp_path):
    t10_app._cache_dir = tmp_path.as_posix()
    url = "http://images.amazon.com/some.jpg"

    seen = {"headers": None}
    def fake_get(u, headers=None, timeout=None):
        seen["headers"] = headers
        class R:
            def raise_for_status(self): return None
            content = _mk_pil_image_bytes(6, 6)
        return R()
    monkeypatch.setattr(T10MOD.requests, "get", fake_get, raising=True)

    out = t10_app._fetch_image(url, size=(18, 18))
    assert out.size == (18, 18)
    assert seen["headers"].get("Referer")  # Referer added for Amazon

def test_fetch_image_http_failure_returns_placeholder(monkeypatch, t10_app, tmp_path):
    t10_app._cache_dir = tmp_path.as_posix()
    def bad_get(*a, **k):
        raise RuntimeError("net down")
    monkeypatch.setattr(T10MOD.requests, "get", bad_get, raising=True)

    out = t10_app._fetch_image("http://x/y.png", size=(22, 24))
    assert out.size == (22, 24)


# ---- Tests: _on_canvas_configure --------------------------------------------

def test_on_canvas_configure_sets_width(t10_app, monkeypatch, tk_root):
    # Build enough UI for canvas + frame id
    monkeypatch.setattr(t10_app, "_load_artifacts", lambda: None, raising=True)
    monkeypatch.setattr(t10_app, "_top10_records", lambda: [], raising=True)
    monkeypatch.setattr(t10_app, "_show_cards", lambda recs: None, raising=True)
    t10_app.show_top10(member_id="1")

    class E: width = 321
    # Should not raise
    t10_app._on_canvas_configure(E())




# ---- Tests: _on_card_click & _insert_loan_mysql -----------------------------

def test_on_card_click_no_user_cancels(monkeypatch, t10_app):
    # No current_user_id -> prompt returns None -> early return, no DB insert
    t10_app.current_user_id = None
    t10_app._dlg.value = None
    called = {"n": 0}
    monkeypatch.setattr(t10_app, "_insert_loan_mysql", lambda *a, **k: called.__setitem__("n", called["n"] + 1), raising=True)

    t10_app._on_card_click({"title": "T", "author": "A"})
    assert called["n"] == 0  # not called

def test_on_card_click_decline(monkeypatch, t10_app):
    t10_app.current_user_id = "007"
    t10_app._msg._askyes = False
    called = {"n": 0}
    monkeypatch.setattr(t10_app, "_insert_loan_mysql", lambda *a, **k: called.__setitem__("n", called["n"] + 1), raising=True)
    t10_app._on_card_click({"title": "T", "author": "A"})
    assert called["n"] == 0

def test_on_card_click_success_info(monkeypatch, t10_app):
    t10_app.current_user_id = "007"
    t10_app._msg._askyes = True
    monkeypatch.setattr(t10_app, "_insert_loan_mysql", lambda *a, **k: 2, raising=True)
    # Fire callbacks immediately
    monkeypatch.setattr(t10_app.parent, "after", lambda _ms, fn, title, msg: fn(title, msg), raising=True)

    t10_app._on_card_click({"title": "T", "author": "A", "image": ""})
    assert any("Rows affected: 2" in m for _, m in t10_app._msg.infos)

def test_on_card_click_db_error_shows_error(monkeypatch, t10_app):
    t10_app.current_user_id = "123"
    t10_app._msg._askyes = True
    monkeypatch.setattr(t10_app, "_insert_loan_mysql", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")), raising=True)
    monkeypatch.setattr(t10_app.parent, "after", lambda _ms, fn, title, msg: fn(title, msg), raising=True)

    t10_app._on_card_click({"title": "T", "author": "A"})
    assert any("Failed to save" in m for _, m in t10_app._msg.errors)

def test_insert_loan_mysql_success_primary_select(monkeypatch, t10_app):
    conn = t10_app._fake_conn
    cur = conn.cur
    # First SELECT returns one row (no fallback to LOWER)
    cur.queue = [[{"book_id": "B42"}]]
    cur.rowcount = 1
    affected = t10_app._insert_loan_mysql("999", {"title": "Any", "author": "Au", "image": "img"})
    assert affected == 1
    assert conn.commits == 1 and conn.closed == 1

# def test_insert_loan_mysql_success_fallback_lower(monkeypatch, t10_app):
#     conn = t10_app._fake_conn
#     cur = conn.cur
#     # First SELECT returns []; second returns 1 row via LOWER() query
#     cur.queue = [[], [{"book_id": "B7"}]]
#     cur.rowcount = 1
#     affected = t10_app._insert_loan_mysql("111", {"title": "t", "author": "a", "image": ""})
#     assert affected == 1
#     assert conn.commits == 2  # previous + this
#     assert conn.closed >= 2

def test_insert_loan_mysql_not_found_rolls_back(monkeypatch, t10_app):
    conn = t10_app._fake_conn
    cur = conn.cur
    cur.queue = [[], []]  # not found on both queries
    with pytest.raises(ValueError):
        t10_app._insert_loan_mysql("1", {"title": "ZZ", "author": "AA", "image": ""})
    assert conn.rollbacks >= 1
    assert conn.closed >= 1

def test_insert_loan_mysql_member_id_empty_raises_no_connect(monkeypatch, t10_app):
    # If member_id empty, we should not even connect
    called = {"n": 0}
    monkeypatch.setattr(t10_app.db, "connect", lambda: called.__setitem__("n", called["n"] + 1), raising=True)
    with pytest.raises(ValueError):
        t10_app._insert_loan_mysql("", {"title": "T", "author": "A"})
    assert called["n"] == 0

def test_insert_loan_mysql_missing_title_raises(monkeypatch, t10_app):
    with pytest.raises(ValueError):
        t10_app._insert_loan_mysql("5", {"title": "", "author": "A"})

def test_insert_loan_mysql_execute_error_rolls_back(monkeypatch, t10_app):
    conn = t10_app._fake_conn
    cur = conn.cur
    cur.queue = [[{"book_id": "B1"}]]  # so it attempts the INSERT
    cur.raise_on_execute = RuntimeError("insert fail")
    with pytest.raises(RuntimeError):
        t10_app._insert_loan_mysql("5", {"title": "T", "author": "A", "image": ""})
    assert conn.rollbacks >= 1
    assert conn.closed >= 1
