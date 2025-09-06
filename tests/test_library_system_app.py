# tests/test_library_system_app.py
import os
import types
import importlib
import importlib.util
import pathlib
import tkinter as tk
import pytest

# ---- Find & load the module that defines class LibrarySystemApp -------------
def _load_app_module():
    # Try common names first
    for cand in (
        "LibrarySystemApp",          # LibrarySystemApp.py
        "app",                       # app.py
        "library_system_app",        # library_system_app.py
        "library_system",            # library_system.py
        "ui.LibrarySystemApp",       # package layout
        "userRole.LibrarySystemApp",
        "src.LibrarySystemApp",
        "main",                      # main.py (common)
    ):
        try:
            return importlib.import_module(cand)
        except Exception:
            pass

    # Fallback: search the repo for any *.py containing "class LibrarySystemApp"
    root = pathlib.Path(__file__).resolve().parents[1]
    for p in root.rglob("*.py"):
        if p.name.startswith("test_"):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "class LibrarySystemApp" in txt:
            spec = importlib.util.spec_from_file_location("LibrarySystemApp_autoload", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            return mod

    raise ImportError(
        "Couldn't import LibrarySystemApp. Please adjust the import candidates at the top of this test file."
    )

_APP_MODULE = _load_app_module()
LibrarySystemApp = getattr(_APP_MODULE, "LibrarySystemApp")

# ---- Simple sinks/fakes used across tests -----------------------------------
class _MsgSink:
    def __init__(self):
        self.errors = []
        self.infos = []
    def showerror(self, title, msg): self.errors.append((title, msg))
    def showinfo(self, title, msg): self.infos.append((title, msg))

class _FakeCursor:
    def __init__(self, result=None):
        self._result = result
        self.closed = False
        self.last_sql = None
        self.last_params = None
    def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
    def fetchone(self):
        return self._result
    def close(self): self.closed = True

class _FakeConn:
    def __init__(self, result=None, raise_on_cursor=False):
        self._result = result
        self.closed = False
        self.raise_on_cursor = raise_on_cursor
        self.cursor_obj = _FakeCursor(result=result)
        self._is_connected = True
    def cursor(self):
        if self.raise_on_cursor:
            raise RuntimeError("cursor fail")
        return self.cursor_obj
    def is_connected(self): return self._is_connected
    def close(self): self.closed = True

class _FakeDB:
    def __init__(self, conn): self._conn = conn
    def connect(self): return self._conn

class _AskSeq:
    """Returns successive values for simpledialog.askstring calls."""
    def __init__(self, *answers): self._answers = list(answers); self.calls = []
    def __call__(self, *a, **k):
        self.calls.append((a, k))
        return self._answers.pop(0) if self._answers else None

# Tk-backed PhotoImage stub so Labels accept it
def _tk_photo(*a, **k):
    import tkinter as _tk
    return _tk.PhotoImage(width=1, height=1)

# ---- A safe Tk root ---------------------------------------------------------
@pytest.fixture
def tk_root():
    import tkinter as _tk
    try:
        root = _tk.Tk()
    except _tk.TclError:
        pytest.skip("Tk not installed properly on this machine; skipping GUI test.")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass

# ---- Fixture: app instance with common patches ------------------------------
@pytest.fixture
def app(monkeypatch, tk_root):
    # Capture real exists to avoid recursion when patching
    real_exists = os.path.exists

    def _exists(path):
        if os.path.normpath(path).endswith(os.path.normpath(os.path.join("image", "main_frame.jpg"))):
            return True
        return real_exists(path)

    monkeypatch.setattr(_APP_MODULE.os.path, "exists", _exists, raising=True)

    # Patch out PIL Image + ImageTk
    class _FakeImage:
        def resize(self, *a, **k): return self
    monkeypatch.setattr(_APP_MODULE, "Image", types.SimpleNamespace(
        open=lambda *a, **k: _FakeImage(),
        Resampling=types.SimpleNamespace(LANCZOS=1)
    ))
    monkeypatch.setattr(_APP_MODULE, "ImageTk", types.SimpleNamespace(PhotoImage=_tk_photo))

    # No-op AdminPanel/UserPanel
    created = {"admin": 0, "user": 0}
    class _AdminPanel:
        def __init__(self, *a, **k): created["admin"] += 1
    class _UserPanel:
        def __init__(self, *a, **k): created["user"] += 1
    monkeypatch.setattr(_APP_MODULE, "AdminPanel", _AdminPanel)
    monkeypatch.setattr(_APP_MODULE, "UserPanel", _UserPanel)

    # Dialogs / messagebox sinks
    sink = _MsgSink()
    ask = _AskSeq()
    monkeypatch.setattr(_APP_MODULE, "simpledialog", types.SimpleNamespace(askstring=ask))
    monkeypatch.setattr(_APP_MODULE, "messagebox", sink)

    # Build the app
    app = LibrarySystemApp(tk_root)
    app._created_counter = created
    app._msg_sink = sink
    app._ask = ask
    return app

# ----------------------------- Tests -----------------------------------------
def test_init_sets_title_geometry_and_builds_main_menu(app):
    # Title should be set
    assert app.root.title() == "Sri Lankan Library System"
    # Main UI should be constructed with a background label
    assert hasattr(app, "bg_label")
    assert app.bg_label.winfo_exists()
    # And the main frame should contain content
    assert any(isinstance(w, tk.Frame) for w in app.main_frame.winfo_children())


def test_show_main_menu_builds_buttons_and_invokable(app, monkeypatch):
    # Force logo loader to no-op so we don't care about image paths here
    monkeypatch.setattr(_APP_MODULE, "Image", types.SimpleNamespace(
        open=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no-op")),
        Resampling=types.SimpleNamespace(LANCZOS=1)
    ), raising=True)
    app.add_library_logo = lambda parent: None

    app.show_main_menu()
    all_widgets = list(app.main_frame.winfo_children())
    q = list(all_widgets)
    seen_texts = set()
    while q:
        w = q.pop()
        if isinstance(w, tk.Button):
            seen_texts.add(w.cget("text"))
        try:
            q.extend(w.winfo_children())
        except Exception:
            pass

    assert "ADMIN PANEL" in seen_texts
    assert "USER PORTAL" in seen_texts

def test_add_library_logo_success_loads_image(app, monkeypatch):
    # Avoid recursion: capture real exists
    real_exists = os.path.exists
    def _exists(path):
        if os.path.basename(path) == "library logo.jpg":
            return True
        return real_exists(path)
    monkeypatch.setattr(_APP_MODULE.os.path, "exists", _exists, raising=True)

    parent = tk.Frame(app.main_frame, bg="#3498db"); parent.pack()
    app.add_library_logo(parent)

    labels = [w for w in parent.winfo_children() if isinstance(w, tk.Frame)][0].winfo_children()
    assert any(isinstance(w, tk.Label) and "ජාතික" in (w.cget("text") or "") for w in labels)

def test_add_library_logo_missing_uses_fallback(app, monkeypatch):
    monkeypatch.setattr(_APP_MODULE.os.path, "exists", lambda p: False, raising=True)
    parent = tk.Frame(app.main_frame, bg="#3498db"); parent.pack()

    app.add_library_logo(parent)
    frames = [w for w in parent.winfo_children() if isinstance(w, tk.Frame)]
    assert frames
    texts = []
    for f in frames:
        for w in f.winfo_children():
            if isinstance(w, tk.Label):
                texts.append(w.cget("text"))
    assert any("ජාතික" in t for t in texts)
    assert any("National Library" in t for t in texts)

def test_prompt_admin_login_success_navigates_to_admin(app, monkeypatch):
    app._ask._answers = ["admin", "admin"]
    app.prompt_admin_login()
    assert app._created_counter["admin"] == 1
    assert not app._msg_sink.errors

def test_prompt_admin_login_invalid_shows_error(app):
    app._ask._answers = ["foo", "bar"]
    app.prompt_admin_login()
    assert any("Login Failed" in t for t, _ in app._msg_sink.errors)
    assert app._created_counter["admin"] == 0

def test_prompt_user_login_success_builds_user_panel(app, monkeypatch):
    app._ask._answers = ["101", "0123456789"]
    monkeypatch.setattr(_APP_MODULE.LibrarySystemApp, "validate_user", lambda _self, a, b: True)
    app.prompt_user_login()
    assert app._created_counter["user"] == 1
    assert not app._msg_sink.errors

def test_prompt_user_login_invalid_shows_error(app, monkeypatch):
    app._ask._answers = ["101", "0000000000"]
    monkeypatch.setattr(_APP_MODULE.LibrarySystemApp, "validate_user", lambda _self, a, b: False)
    app.prompt_user_login()
    assert any("Login Failed" in t for t, _ in app._msg_sink.errors)
    assert app._created_counter["user"] == 0

def test_validate_user_true_returns_true_and_closes(monkeypatch, tk_root):
    conn = _FakeConn(result=("row",))
    monkeypatch.setattr(_APP_MODULE, "Database", lambda: _FakeDB(conn))

    real_exists = os.path.exists
    monkeypatch.setattr(
        _APP_MODULE.os.path, "exists",
        lambda p: True if p.endswith(os.path.join("image", "main_frame.jpg")) else real_exists(p),
        raising=True
    )
    monkeypatch.setattr(_APP_MODULE, "Image", types.SimpleNamespace(
        open=lambda *a, **k: type("Img", (), {"resize": lambda self, *a, **k: self})(),
        Resampling=types.SimpleNamespace(LANCZOS=1)
    ))
    # Use a real Tk PhotoImage stub
    monkeypatch.setattr(_APP_MODULE, "ImageTk", types.SimpleNamespace(PhotoImage=_tk_photo))
    sink = _MsgSink()
    monkeypatch.setattr(_APP_MODULE, "messagebox", sink)

    app2 = LibrarySystemApp(tk_root)
    ok = app2.validate_user("101", "0123456789")
    assert ok is True
    assert conn.closed
    assert not sink.errors

def test_validate_user_false_when_no_match(monkeypatch, tk_root):
    conn = _FakeConn(result=None)
    monkeypatch.setattr(_APP_MODULE, "Database", lambda: _FakeDB(conn))

    real_exists = os.path.exists
    monkeypatch.setattr(
        _APP_MODULE.os.path, "exists",
        lambda p: True if p.endswith(os.path.join("image", "main_frame.jpg")) else real_exists(p),
        raising=True
    )
    monkeypatch.setattr(_APP_MODULE, "Image", types.SimpleNamespace(
        open=lambda *a, **k: type("Img", (), {"resize": lambda self, *a, **k: self})(),
        Resampling=types.SimpleNamespace(LANCZOS=1)
    ))
    monkeypatch.setattr(_APP_MODULE, "ImageTk", types.SimpleNamespace(PhotoImage=_tk_photo))
    sink = _MsgSink()
    monkeypatch.setattr(_APP_MODULE, "messagebox", sink)

    app2 = LibrarySystemApp(tk_root)
    ok = app2.validate_user("101", "0000000000")
    assert ok is False
    assert conn.closed
    assert not sink.errors

def test_validate_user_db_exception_shows_error_and_returns_false(monkeypatch, tk_root):
    class _BoomDB:
        def connect(self): raise RuntimeError("boom")
    monkeypatch.setattr(_APP_MODULE, "Database", _BoomDB)

    real_exists = os.path.exists
    monkeypatch.setattr(
        _APP_MODULE.os.path, "exists",
        lambda p: True if p.endswith(os.path.join("image", "main_frame.jpg")) else real_exists(p),
        raising=True
    )
    monkeypatch.setattr(_APP_MODULE, "Image", types.SimpleNamespace(
        open=lambda *a, **k: type("Img", (), {"resize": lambda self, *a, **k: self})(),
        Resampling=types.SimpleNamespace(LANCZOS=1)
    ))
    monkeypatch.setattr(_APP_MODULE, "ImageTk", types.SimpleNamespace(PhotoImage=_tk_photo))
    sink = _MsgSink()
    monkeypatch.setattr(_APP_MODULE, "messagebox", sink)

    app2 = LibrarySystemApp(tk_root)
    ok = app2.validate_user("x", "y")
    assert ok is False
    assert any("Database Error" in t for t, _ in sink.errors)

def test_add_fallback_decorations_creates_labels(app):
    parent = tk.Frame(app.main_frame, bg="#3498db"); parent.pack()
    app.add_fallback_decorations(parent)
    labels = [w for w in parent.winfo_children()[0].winfo_children() if isinstance(w, tk.Label)]
    assert any("ජාතික" in (w.cget("text") or "") for w in labels)
    assert any("National Library" in (w.cget("text") or "") for w in labels)
