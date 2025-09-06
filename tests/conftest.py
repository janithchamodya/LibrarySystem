# tests/conftest.py
import sys
import types
import pytest


# ---- Robust alias for top10books -------------------------------------------
import importlib, importlib.util, pathlib, sys, os

def _alias_top10books():
    # Ensure project root is importable
    root = pathlib.Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Try common module names (different casings/variants)
    candidates = [
        "userRole.top10books",
        "userRole.top10_books",
        "userRole.Top10books",
        "userRole.Top10_Books",
        "top10books",
        "top10_books",
        "Top10_Books",
    ]
    for name in candidates:
        try:
            mod = importlib.import_module(name)
            sys.modules["userRole.top10books"] = mod
            sys.modules["top10books"] = mod
            return
        except Exception:
            pass

    # Fallback: search the repo for a matching file
    patterns = ["top10books.py", "top10_books.py", "Top10_Books.py", "*top10*book*.py"]
    for pat in patterns:
        for p in root.rglob(pat):
            try:
                spec = importlib.util.spec_from_file_location("top10books", p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                sys.modules["top10books"] = mod
                sys.modules["userRole.top10books"] = mod
                return
            except Exception:
                continue

_alias_top10books()

# ---- Make tkcalendar optional (stub) ----------------------------------------
if "tkcalendar" not in sys.modules:
    stub = types.ModuleType("tkcalendar")
    class _StubDateEntry:
        def __init__(self, *a, **k): pass
        def grid(self, *a, **k): pass
        def get_date(self):
            class _D: year = 2025
            return _D()
    stub.DateEntry = _StubDateEntry
    sys.modules["tkcalendar"] = stub

# ---- Alias `lending` to your actual module path -----------------------------
# If your file is adminRole/lending.py this will work. If it lives elsewhere,
# just change the import below accordingly.
try:
    import adminRole.lending as _lending
    sys.modules["lending"] = _lending
except Exception:
    # If you don't have lending yet or it's elsewhere, tests that need it will
    # still fail — tell me the path and I'll adjust.
    pass

# Alias `member_management` to the real module (userRole preferred)
try:
    import adminRole.MemberManagement as _mm
    sys.modules["member_management"] = _mm
except Exception:
    try:
        import adminRole.MemberManagement as _mm
        sys.modules["member_management"] = _mm
    except Exception:
        pass

# ---- Safe Tk root: skip GUI tests if Tk isn't usable ------------------------
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
