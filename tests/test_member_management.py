import builtins
import io
import os
import tkinter as tk
import pytest

# Import the class AND the defining module so we can patch its globals
try:
    from adminRole.MemberManagement import MemberManagement
    MM_MODULE = __import__("adminRole.member_management", fromlist=["*"])
except Exception:
    from  adminRole.MemberManagement import MemberManagement
    MM_MODULE = __import__("member_management", fromlist=["*"])


# -------------------- Fakes & helpers --------------------

class FakeDate:  # (not needed here, but kept for parity)
    def __init__(self, year=2025): self.year = year

class FakeCursor:
    def __init__(self):
        self._results = []
        self.rowcount = 0
        self.executed = []       # history of (sql, params)
        self.last_sql = None
        self.last_params = None
    def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        self.executed.append((sql, params))
    def fetchall(self):
        return list(self._results)

class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.closed = False
    def cursor(self): return self.cursor_obj
    def commit(self): pass
    def close(self): self.closed = True

class FakeDB:
    """Returned by patched Database()"""
    def __init__(self, conn): self._conn = conn
    def connect(self): return self._conn

class MsgSink:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []
        self.prompts = []
    def showinfo(self, t, m): self.infos.append((t, m))
    def showwarning(self, t, m): self.warnings.append((t, m))
    def showerror(self, t, m): self.errors.append((t, m))
    def askyesno(self, t, m):
        self.prompts.append((t, m))
        return True  # can be monkeypatched per test


# Camera fakes for cv2
class FakeBuffer:
    def __init__(self, b=b"abc"):
        self._b = b
    def tobytes(self): return self._b

class FakeCameraOK:
    def __init__(self, *a, **k): self.released = False
    def read(self):
        # return True + a dummy image "frame"
        return True, object()
    def release(self): self.released = True

class FakeCameraFail:
    def __init__(self, *a, **k): self.released = False
    def read(self): return False, None
    def release(self): self.released = True


# -------------------- Fixtures --------------------

@pytest.fixture
def mm_app(monkeypatch, tk_root):
    """
    Build a MemberManagement instance with:
     - Fake DB connection
     - Captured messagebox/filedialog
     - Stubbed cv2 methods
    """
    conn = FakeConn()
    # Replace Database() in the module where MemberManagement is defined
    monkeypatch.setattr(MM_MODULE, "Database", lambda: FakeDB(conn), raising=True)

    # Messagebox + filedialog + cv2 captured/stubbed
    sink = MsgSink()
    monkeypatch.setattr(MM_MODULE, "messagebox", sink, raising=True)

    # filedialog will be controlled per-test; default = cancel
    class FDStub:
        def askopenfilename(self, *a, **k): return ""
    monkeypatch.setattr(MM_MODULE, "filedialog", FDStub(), raising=True)

    # cv2 stubs (can be overridden per-test)
    class CV2Stub:
        VideoCapture = FakeCameraOK
        def imencode(self, ext, frame): return True, FakeBuffer(b"xyz")
        def destroyAllWindows(self): pass
    cv2stub = CV2Stub()
    monkeypatch.setattr(MM_MODULE, "cv2", cv2stub, raising=True)

    # Build widget
    frame = tk.Frame(tk_root); frame.pack()
    app = MemberManagement(frame, go_back_callback=lambda: None)

    # expose fakes
    app._fake_conn = conn
    app._msg = sink
    app._cv2 = cv2stub
    return app


def _fill_valid(app):
    app.entries["member_id"].delete(0, tk.END); app.entries["member_id"].insert(0, "7")
    app.entries["name"].delete(0, tk.END); app.entries["name"].insert(0, "Alice")
    app.entries["age"].delete(0, tk.END); app.entries["age"].insert(0, "22")
    app.entries["email"].delete(0, tk.END); app.entries["email"].insert(0, "a@b.com")
    app.entries["contact"].delete(0, tk.END); app.entries["contact"].insert(0, "0771234567")


# -------------------- Validation --------------------

def test_validate_valid_inputs(mm_app):
    _fill_valid(mm_app)
    assert mm_app.validate_inputs() == ("7", "Alice", "22", "a@b.com", "0771234567")

@pytest.mark.parametrize("field, bad, expected_snippet", [
    ("member_id", "77", "exactly 1 digits"),     # regex \d{1}
    ("member_id", "A",  "digits"),
    ("name",      "",   "Name is required"),
    ("age",       "9",  "Invalid Age"),
    ("email",     "a@b", "Invalid email"),
    ("contact",   "123", "exactly 10 digits"),
])
def test_validate_invalids_trigger_warnings(mm_app, field, bad, expected_snippet):
    _fill_valid(mm_app)
    mm_app.entries[field].delete(0, tk.END)
    mm_app.entries[field].insert(0, bad)
    assert mm_app.validate_inputs() is None
    assert any(expected_snippet in m for _, m in mm_app._msg.warnings)


# -------------------- Browse photo --------------------

def test_browse_photo_cancel_keeps_none(mm_app, monkeypatch):
    mm_app.photo_data = None
    # default filedialog returns "", so just call
    mm_app.browse_photo()
    assert mm_app.photo_data is None
    # no success info message
    assert not any("Photo Loaded" in m for _, m in mm_app._msg.infos)

def test_browse_photo_success_reads_bytes(mm_app, tmp_path, monkeypatch):
    p = tmp_path / "pic.jpg"
    p.write_bytes(b"HELLOIMG")
    monkeypatch.setattr(MM_MODULE.filedialog, "askopenfilename", lambda **k: str(p))
    mm_app.browse_photo()
    assert mm_app.photo_data == b"HELLOIMG"
    assert any("Image loaded successfully" in m for _, m in mm_app._msg.infos)


# -------------------- Capture photo --------------------

def test_capture_photo_success_sets_bytes(mm_app, monkeypatch):
    # Use OK camera and success imencode
    mm_app.capture_photo()
    assert mm_app.photo_data == b"xyz"
    assert any("captured successfully" in m for _, m in mm_app._msg.infos)

def test_capture_photo_camera_fail_shows_error(mm_app, monkeypatch):
    # Make VideoCapture fail
    mm_app._cv2.VideoCapture = FakeCameraFail
    mm_app.capture_photo()
    assert any("Could not access camera" in m for _, m in mm_app._msg.errors)


# -------------------- CRUD: add / update / delete --------------------

def test_add_member_success_executes_insert(mm_app):
    _fill_valid(mm_app)
    before = len(mm_app._fake_conn.cursor_obj.executed)
    mm_app.add_member()
    cur = mm_app._fake_conn.cursor_obj
    sqls = [s for s, _ in cur.executed[before:]]
    assert any("INSERT INTO members" in s for s in sqls)
    assert any("Member added successfully" in m for _, m in mm_app._msg.infos)
    assert mm_app._fake_conn.closed  # connection closed in finally

def test_add_member_db_error_shows_error(mm_app, monkeypatch):
    _fill_valid(mm_app)
    def boom(sql, params=None): raise RuntimeError("boom")
    monkeypatch.setattr(mm_app._fake_conn.cursor_obj, "execute", boom, raising=True)
    mm_app.add_member()
    assert any("Failed to add member" in m for _, m in mm_app._msg.errors)



def test_update_member_not_found_warning(mm_app):
    _fill_valid(mm_app)
    mm_app._fake_conn.cursor_obj.rowcount = 0
    mm_app.update_member()
    assert any("not found" in m.lower() for _, m in mm_app._msg.warnings)

def test_delete_member_cancel_runs_no_sql(mm_app, monkeypatch):
    _fill_valid(mm_app)
    before = len(mm_app._fake_conn.cursor_obj.executed)
    # Put an id and cancel
    mm_app.entries["member_id"].delete(0, tk.END)
    mm_app.entries["member_id"].insert(0, "7")
    monkeypatch.setattr(mm_app._msg, "askyesno", lambda *a, **k: False)
    mm_app.delete_member()
    assert len(mm_app._fake_conn.cursor_obj.executed) == before



def test_delete_member_not_found_warning(mm_app):
    _fill_valid(mm_app)
    mm_app.entries["member_id"].delete(0, tk.END)
    mm_app.entries["member_id"].insert(0, "7")
    mm_app._fake_conn.cursor_obj.rowcount = 0
    mm_app.delete_member()
    assert any("Member not found" in m for _, m in mm_app._msg.warnings)


# -------------------- Load + selection + clearing --------------------

def test_load_members_populates_tree(mm_app):
    cur = mm_app._fake_conn.cursor_obj
    cur._results = [
        ("1", "Bob", "21", "b@c.com", "0770000000"),
        ("2", "Eve", "20", "e@c.com", "0771111111"),
    ]
    mm_app.load_members()
    rows = [mm_app.tree.item(i, "values") for i in mm_app.tree.get_children()]
    assert rows[0][1] in ("Bob", "Eve")
    assert rows[1][1] in ("Bob", "Eve")

def test_on_tree_select_and_clear_entries(mm_app):
    mm_app.tree.insert("", tk.END, values=("9", "Neo", "25", "n@e.o", "0712345678"))
    iid = mm_app.tree.get_children()[0]
    mm_app.tree.selection_set(iid); mm_app.tree.focus(iid)
    mm_app.on_tree_select(None)

    assert mm_app.entries["member_id"].get() == "9"
    assert mm_app.entries["name"].get() == "Neo"
    assert mm_app.entries["age"].get() == "25"
    assert mm_app.entries["email"].get() == "n@e.o"
    assert mm_app.entries["contact"].get() == "0712345678"

    # Now clear and verify
    mm_app.clear_entries()
    assert all(mm_app.entries[k].get() == "" for k in ("member_id", "name", "age", "email", "contact"))
    assert mm_app.photo_data is None
    
def test_update_member_success_rowcount_positive(mm_app):
    _fill_valid(mm_app)
    cur = mm_app._fake_conn.cursor_obj
    cur.rowcount = 1  # simulate 1 row updated
    before = len(cur.executed)

    mm_app.update_member()

    # Check that an UPDATE ran (load_members() will run a SELECT afterwards)
    sqls = [s for s, _ in cur.executed[before:]]
    assert any("UPDATE members" in s for s in sqls)
    assert any("updated successfully" in m for _, m in mm_app._msg.infos)


def test_delete_member_success_executes_delete(mm_app):
    _fill_valid(mm_app)
    # Ensure an ID is present
    mm_app.entries["member_id"].delete(0, tk.END)
    mm_app.entries["member_id"].insert(0, "7")

    cur = mm_app._fake_conn.cursor_obj
    cur.rowcount = 1  # simulate successful deletion
    before = len(cur.executed)

    mm_app.delete_member()

    # Verify DELETE happened (followed by SELECT from load_members)
    sqls = [s for s, _ in cur.executed[before:]]
    assert any("DELETE FROM members" in s for s in sqls)
    assert any("Member deleted successfully" in m for _, m in mm_app._msg.infos)
    
