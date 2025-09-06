
import pytest
import tkinter as tk

# --- Import module/class under test (support both paths) ---------------------
try:
    import adminRole.lending as lending_module
    LendingClass = lending_module.lending
except Exception:
    import lending as lending_module
    LendingClass = lending_module.lending


# --- Fakes / helpers ---------------------------------------------------------

class FakeEntry:
    """Tk-like Entry compatible with .get(), .delete(), .insert(), focus_set()."""
    def __init__(self, value=""):
        self._value = value
        self.focused = False
    def get(self):
        return self._value
    def delete(self, *_a, **_k):
        self._value = ""
    def insert(self, _idx, s):
        self._value = str(s)
    def focus_set(self):
        self.focused = True


class MsgSink:
    """Capture messagebox calls (showinfo/showerror) and askyesno prompts."""
    def __init__(self):
        self.infos = []
        self.errors = []
        self.warnings = []  # not used here, but kept for parity
        self.prompts = []
    def showinfo(self, title, msg):
        self.infos.append((title, msg))
    def showerror(self, title, msg):
        self.errors.append((title, msg))
    def showwarning(self, title, msg):
        self.warnings.append((title, msg))
    def askyesno(self, title, msg):
        self.prompts.append((title, msg))
        return True


class FakeCursor:
    """Tracks executed SQL and allows queued fetchone() results."""
    def __init__(self):
        self.executed = []
        self.fetchone_queue = []  # list of values to pop in order
    def execute(self, sql, params=None):
        self.executed.append((sql, params))
    def fetchone(self):
        if self.fetchone_queue:
            return self.fetchone_queue.pop(0)
        return None
    def close(self):
        pass


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()
        self.commits = 0
        self.closed = False
    def cursor(self):
        return self.cur
    def commit(self):
        self.commits += 1
    def close(self):
        self.closed = True


class FakeDB:
    def __init__(self, conn):
        self._conn = conn
    def connect(self):
        return self._conn


class FakeSidebar:
    """Mimic SidebarNotifications; must accept (parent, db, on_confirm, table_name)."""
    def __init__(self, parent, db, on_confirm, table_name):
        self.parent = parent
        self.db = db
        self.on_confirm = on_confirm
        self.table_name = table_name
        self.destroyed = False
    def destroy(self):
        self.destroyed = True


class DummyMySQLError(Exception):
    """Used to simulate mysql.connector.Error"""


# --- Fixtures ----------------------------------------------------------------

@pytest.fixture
def tk_root():
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
def app_under_test(monkeypatch, tk_root):
    """
    Build a lending UI object with:
      - Fake Database
      - Captured messagebox
      - Patched predictor
      - Patched SidebarNotifications
      - Patched mysql.connector.Error
    """
    # Fake DB
    conn = FakeConn()
    monkeypatch.setattr(lending_module, "Database", lambda: FakeDB(conn), raising=True)

    # Messagebox sink
    sink = MsgSink()
    monkeypatch.setattr(lending_module, "messagebox", sink, raising=True)

    # Predictor
    monkeypatch.setattr(lending_module, "predict_holding_days", lambda feats: 5.75, raising=True)

    # Sidebar
    monkeypatch.setattr(lending_module, "SidebarNotifications", FakeSidebar, raising=True)

    # mysql error class
    class _DummyConnector:
        Error = DummyMySQLError
    monkeypatch.setattr(lending_module, "mysql", type("M", (), {"connector": _DummyConnector})(), raising=True)

    # Build object
    parent = tk_root
    content = tk.Frame(parent); content.pack()
    app = LendingClass(
        parent=parent,
        content_frame=content,
        title_font=("Arial", 14, "bold"),
        label_font=("Arial", 12),
        button_font=("Arial", 12, "bold"),
        go_back_callback=lambda: None,
    )

    # Provide DB and sinks for asserts
    app._fake_conn = conn
    app._msg = sink

    # Set entries the way submit_lending() expects
    app.entries = {
        "user_id": FakeEntry("123"),
        "book_id": FakeEntry("456"),
        "borrow_date": "2025-01-01",
        "return_date": "2025-01-15",
        "pages": FakeEntry("321"),
    }
    # Radio values
    app.user_role = tk.StringVar(value="student")
    app.book_category = tk.StringVar(value="science")

    return app


# --- Helper to reset entries quickly -----------------------------------------

def _fill_valid(app):
    app.entries["user_id"] = FakeEntry("123")
    app.entries["book_id"] = FakeEntry("456")
    app.entries["pages"] = FakeEntry("321")
    app.entries["borrow_date"] = "2025-01-01"
    app.entries["return_date"] = "2025-01-15"
    app.user_role.set("student")
    app.book_category.set("science")


# --- Tests: validate_numeric_input -------------------------------------------

def test_validate_numeric_input_accepts_digits(app_under_test):
    app = app_under_test
    assert app.validate_numeric_input("123", "user_id", 3) is True
    assert app._msg.errors == []  # no error dialogs

def test_validate_numeric_input_rejects_letters(app_under_test):
    app = app_under_test
    assert app.validate_numeric_input("12A", "user_id", 3) is False
    assert any("Only numbers are allowed" in m for _, m in app._msg.errors)

def test_validate_numeric_input_rejects_too_long(app_under_test):
    app = app_under_test
    assert app.validate_numeric_input("1234", "user_id", 3) is False
    assert any("Maximum 3 digits allowed" in m for _, m in app._msg.errors)


# --- Tests: submit_lending validation gates ----------------------------------

@pytest.mark.parametrize("field,value,substr", [
    ("user_id", "", "User ID is required"),
    ("user_id", "1234", "3 digits or less"),
    ("user_id", "12A", "must be numeric"),
    ("book_id", "", "Book ID is required"),
    ("book_id", "9"*11, "10 digits or less"),
    ("book_id", "12A", "must be numeric"),
    ("pages", "", "Pages is required"),
    ("pages", "9"*8, "7 digits or less"),
    ("pages", "12A", "must be numeric"),
])
def test_submit_lending_field_validation_errors(app_under_test, field, value, substr):
    app = app_under_test
    _fill_valid(app)
    # override one field
    if field in ("user_id", "book_id", "pages"):
        app.entries[field] = FakeEntry(value)
    app.submit_lending()
    assert any(substr in msg for _, msg in app._msg.errors)
    # Ensure no INSERT happened
    assert not any("INSERT INTO lending_records" in sql for sql, _ in app._fake_conn.cur.executed)

def test_submit_lending_pages_must_be_positive(app_under_test):
    app = app_under_test
    _fill_valid(app)
    app.entries["pages"] = FakeEntry("0")
    app.submit_lending()
    assert any("greater than 0" in msg for _, msg in app._msg.errors)
    assert not any("INSERT INTO lending_records" in sql for sql, _ in app._fake_conn.cur.executed)


# --- Tests: user/book existence branches -------------------------------------

def test_submit_lending_user_not_found(app_under_test):
    app = app_under_test
    _fill_valid(app)
    cur = app._fake_conn.cur
    # user check -> None (not found)
    cur.fetchone_queue = [None]
    app.submit_lending()
    assert any("User ID 123 does not exist" in msg for _, msg in app._msg.errors)
    # Should not continue to INSERT
    assert not any("INSERT INTO lending_records" in sql for sql, _ in cur.executed)

def test_submit_lending_book_not_found(app_under_test):
    app = app_under_test
    _fill_valid(app)
    cur = app._fake_conn.cur
    # user exists, book not found
    cur.fetchone_queue = [(1,), None]
    app.submit_lending()
    assert any("Book ID 456 does not exist" in msg for _, msg in app._msg.errors)
    assert not any("INSERT INTO lending_records" in sql for sql, _ in cur.executed)

def test_submit_lending_success_flow_executes_insert_and_infos(app_under_test):
    app = app_under_test
    _fill_valid(app)
    cur = app._fake_conn.cur
    cur.fetchone_queue = [(1,), (1,)]  # user exists, book exists
    app.submit_lending()
    # Two infos: prediction success + final "Insert Success"
    assert any("Predicted Holding Days" in msg for _, msg in app._msg.infos)
    assert any("Insert Success" in msg for _, msg in app._msg.infos)
    assert any("INSERT INTO lending_records" in sql for sql, _ in cur.executed)
    assert app._fake_conn.commits >= 1


# --- Tests: DB/prediction error handlers -------------------------------------

def test_submit_lending_mysql_error(app_under_test, monkeypatch):
    app = app_under_test
    _fill_valid(app)
    cur = app._fake_conn.cur
    cur.fetchone_queue = [(1,), (1,)]
    # Make the insert raise mysql.connector.Error
    def bad_execute(sql, params=None):
        if "INSERT INTO lending_records" in sql:
            raise lending_module.mysql.connector.Error("boom!")
        return None
    monkeypatch.setattr(cur, "execute", bad_execute, raising=True)
    app.submit_lending()
    assert any("Database Error" in title for title, _ in app._msg.errors)

# def test_submit_lending_value_error(app_under_test, monkeypatch):
#     app = app_under_test
#     _fill_valid(app)
#     cur = app._fake_conn.cur
#     cur.fetchone_queue = [(1,), (1,)]
#     # Make casting int(user_id) blow up
#     app.entries["user_id"] = FakeEntry("notanint")
#     app.submit_lending()
#     assert any("Input Error" in title for title, _ in app._msg.errors)

# def test_submit_lending_generic_exception(app_under_test, monkeypatch):
#     app = app_under_test
#     _fill_valid(app)
#     cur = app._fake_conn.cur
#     cur.fetchone_queue = [(1,), (1,)]
#     # Blow up Predictor to hit the generic Exception path
#     monkeypatch.setattr(lending_module, "predict_holding_days", lambda _f: (_ for _ in ()).throw(RuntimeError("X")), raising=True)
#     app.submit_lending()
#     assert any(title == "Error" for title, _ in app._msg.errors)


# --- Tests: sidebar toggle + prefill -----------------------------------------

def test_has_pending_notifications_true_false(app_under_test):
    app = app_under_test
    cur = app._fake_conn.cur
    cur.fetchone_queue = [(2,)]  # pending > 0
    assert app._has_pending_notifications() is True
    cur.fetchone_queue = [(0,)]
    assert app._has_pending_notifications() is False

def test_toggle_sidebar_create_destroy(app_under_test, tk_root):
    app = app_under_test
    body = tk.Frame(app.content_frame); body.pack()
    assert app.sidebar is None
    app._toggle_sidebar(parent=body)
    assert isinstance(app.sidebar, FakeSidebar)
    # toggle again -> should destroy and set to None
    app._toggle_sidebar(parent=body)
    assert app.sidebar is None

def test_prefill_from_notification_sets_entries(app_under_test):
    app = app_under_test
    # Ensure entries are focusable/editable
    app.entries["user_id"] = FakeEntry("1")
    app.entries["book_id"] = FakeEntry("2")
    app.entries["pages"] = FakeEntry("10")
    app._prefill_from_notification("777", "888")
    assert app.entries["user_id"].get() == "777"
    assert app.entries["book_id"].get() == "888"
    assert app.entries["pages"].focused is True
