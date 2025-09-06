

import tkinter as tk
import pytest

# Import BookManagement from your project
try:
    from adminRole.book_management import BookManagement
    BM_MODULE = __import__("adminRole.book_management", fromlist=["*"])
except Exception:
    from book_management import BookManagement
    BM_MODULE = __import__("book_management", fromlist=["*"])


# ------------------ Fake helpers ------------------

class _FakeDate:
    def __init__(self, year=2025): self.year = year

class _FakeYearEntry:
    def __init__(self, year=2025): self._y = year
    def get_date(self): return _FakeDate(self._y)

class _FakeCursor:
    def __init__(self):
        self.rowcount = 0
        self._results = []
        self.executed = []
        self.last_sql = None
        self.last_params = None
    def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        self.executed.append((sql, params))
    def fetchall(self): return list(self._results)

class _FakeConn:
    def __init__(self): self.cursor_obj = _FakeCursor()
    def cursor(self): return self.cursor_obj
    def commit(self): pass
    def close(self): pass

class _FakeDB:
    def __init__(self, conn): self._conn = conn
    def connect(self): return self._conn

class _MsgSink:
    def __init__(self):
        self.infos, self.warnings, self.errors, self.prompts = [], [], [], []
    def showinfo(self, t, m): self.infos.append((t, m))
    def showwarning(self, t, m): self.warnings.append((t, m))
    def showerror(self, t, m): self.errors.append((t, m))
    def askyesno(self, t, m):
        self.prompts.append((t, m))
        return True


# ------------------ Fixtures ------------------

@pytest.fixture
def bm_app(monkeypatch, tk_root):
    conn = _FakeConn()
    monkeypatch.setattr(BM_MODULE, "Database", lambda: _FakeDB(conn))
    sink = _MsgSink()
    monkeypatch.setattr(BM_MODULE, "messagebox", sink)

    frame = tk.Frame(tk_root); frame.pack()
    app = BookManagement(frame, go_back_callback=lambda: None)
    app.year_entry = _FakeYearEntry(2025)
    app._fake_conn, app._msg = conn, sink
    return app


def _fill_valid(bm):
    bm.book_id_entry.delete(0, tk.END); bm.book_id_entry.insert(0, "123")
    bm.title_entry.set("science")
    bm.name_entry.delete(0, tk.END); bm.name_entry.insert(0, "Cosmos")
    bm.author_entry.delete(0, tk.END); bm.author_entry.insert(0, "Carl Sagan")


# ------------------ Tests: Validation ------------------

def test_validate_inputs_success(bm_app):
    _fill_valid(bm_app)
    result = bm_app.validate_inputs()
    assert result[0] == "123"
    assert result[1] == "science"



@pytest.mark.parametrize("field,value,msgpart", [
    ("book_id", "abc", "Book ID must be numeric"),
    ("title", "romance", "Title must be selected"),
    ("book_name", "x"*301, "Book Name cannot exceed"),
    ("author", "y"*301, "Author name cannot exceed"),
])
def test_validate_inputs_invalids(bm_app, field, value, msgpart):
    _fill_valid(bm_app)
    if field == "title":
        bm_app.title_entry.set(value)  # Combobox requires .set()
    else:
        e = bm_app.entries[field]
        e.delete(0, tk.END)
        e.insert(0, value)

    result = bm_app.validate_inputs()
    assert result is None
    assert any(msgpart in m for _, m in bm_app._msg.warnings)

def test_validate_inputs_invalid_year(bm_app):
    _fill_valid(bm_app)

    class BadYearEntry:
        def get_date(self):
            class D: year = 99
            return D()

    bm_app.year_entry = BadYearEntry()
    bm_app.entries["year"] = BadYearEntry()

    result = bm_app.validate_inputs()
    assert result is None
    assert any("Year must be a 4-digit" in m for _, m in bm_app._msg.warnings)
    

def test_validate_inputs_invalid_year(bm_app):
    _fill_valid(bm_app)
    bm_app.year_entry = _FakeYearEntry(50)  # bad year
    assert bm_app.validate_inputs() is None
    assert any("Year must be a 4-digit" in m for _, m in bm_app._msg.warnings)


# ------------------ Tests: Add ------------------

def test_add_book_success(bm_app):
    _fill_valid(bm_app)
    cur = bm_app._fake_conn.cursor_obj
    bm_app.add_book()
    assert "INSERT INTO books" in cur.last_sql
    assert any("Book added successfully" in m for _, m in bm_app._msg.infos)

def test_add_book_db_error(bm_app, monkeypatch):
    _fill_valid(bm_app)
    def bad_execute(sql, params=None): raise RuntimeError("boom")
    monkeypatch.setattr(bm_app._fake_conn.cursor_obj, "execute", bad_execute)
    bm_app.add_book()
    assert any("Failed to add book" in m for _, m in bm_app._msg.errors)


# ------------------ Tests: Update ------------------

def test_update_book_success(bm_app):
    _fill_valid(bm_app)
    cur = bm_app._fake_conn.cursor_obj
    cur.rowcount = 1
    bm_app.update_book()
    sqls = [s for s, _ in cur.executed]
    assert any("UPDATE books" in s for s in sqls)
    assert any("updated successfully" in m for _, m in bm_app._msg.infos)

def test_update_book_not_found(bm_app):
    _fill_valid(bm_app)
    cur = bm_app._fake_conn.cursor_obj
    cur.rowcount = 0
    bm_app.update_book()
    assert any("No book found" in m for _, m in bm_app._msg.warnings)


# ------------------ Tests: Delete ------------------

def test_delete_book_no_id(bm_app):
    bm_app.book_id_entry.delete(0, tk.END)
    bm_app.delete_book()
    assert any("Please select a book" in m for _, m in bm_app._msg.warnings)

def test_delete_book_cancel(bm_app, monkeypatch):
    _fill_valid(bm_app)
    monkeypatch.setattr(bm_app._msg, "askyesno", lambda *a, **k: False)
    bm_app.delete_book()
    cur = bm_app._fake_conn.cursor_obj
    assert not any("DELETE" in s for s, _ in cur.executed)

def test_delete_book_success(bm_app):
    _fill_valid(bm_app)
    cur = bm_app._fake_conn.cursor_obj
    cur.rowcount = 1
    bm_app.delete_book()
    assert any("DELETE FROM books" in s for s, _ in cur.executed)
    assert any("deleted successfully" in m for _, m in bm_app._msg.infos)

def test_delete_book_not_found(bm_app):
    _fill_valid(bm_app)
    cur = bm_app._fake_conn.cursor_obj
    cur.rowcount = 0
    bm_app.delete_book()
    assert any("No book found" in m for _, m in bm_app._msg.warnings)


# ------------------ Tests: Load Books ------------------

def test_load_books_success(bm_app):
    cur = bm_app._fake_conn.cursor_obj
    cur._results = [(1, "science", "Cosmos", "Carl Sagan", 1980)]
    bm_app.load_books()
    items = bm_app.tree.get_children()
    assert len(items) == 1

def test_load_books_db_error(bm_app, monkeypatch):
    def bad_cursor(): raise RuntimeError("DB fail")
    monkeypatch.setattr(bm_app._fake_conn, "cursor", bad_cursor)
    bm_app.load_books()
    assert any("Failed to load books" in m for _, m in bm_app._msg.errors)


# ------------------ Tests: UI Helpers ------------------


def test_add_book_success(bm_app):
    _fill_valid(bm_app)
    cur = bm_app._fake_conn.cursor_obj
    before = len(cur.executed)

    bm_app.add_book()

    # load_books() runs a SELECT after the INSERT, so check the history
    sqls = [s for s, _ in cur.executed[before:]]
    assert any("INSERT INTO books" in s for s in sqls)
    assert any("Book added successfully" in m for _, m in bm_app._msg.infos)


def test_clear_entries_resets_all(bm_app):
    _fill_valid(bm_app)

    # DateEntry stub has no .delete(); provide a deletable stub for 'year'
    class _DeletableStub:
        def delete(self, *a, **k): pass
    bm_app.entries["year"] = _DeletableStub()

    bm_app.clear_entries()
    assert bm_app.book_id_entry.get() == ""
    assert bm_app.title_entry.get() == ""
    assert bm_app.name_entry.get() == ""
    assert bm_app.author_entry.get() == ""
def test_on_tree_select_populates_entries(bm_app):
    # Ensure clear_entries() won't crash on the 'year' widget
    class _DeletableStub:
        def delete(self, *a, **k): pass
    bm_app.entries["year"] = _DeletableStub()

    bm_app.tree.insert("", tk.END, values=("5", "fiction", "1984", "Orwell", 1949))
    iid = bm_app.tree.get_children()[0]
    bm_app.tree.selection_set(iid)
    bm_app.tree.focus(iid)

    bm_app.on_tree_select(None)

    assert bm_app.book_id_entry.get() == "5"
    assert bm_app.title_entry.get() == "fiction"
    assert bm_app.name_entry.get() == "1984"
    assert bm_app.author_entry.get() == "Orwell"

