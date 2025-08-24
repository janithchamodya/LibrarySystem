import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class SidebarNotifications:
  
    def __init__(self, parent, db, on_confirm=None, table_name="user_notifications"):
        self.db = db
        self.on_confirm = on_confirm
        self.table = table_name
        self._job = None

        # OUTER: still use pack to dock at right
        self.frame = tk.Frame(parent, bg="#f7f9fc", width=340, bd=1, relief="solid")
        self.frame.pack(side="right", fill="y")
        self.frame.pack_propagate(False)

        # ----- INSIDE: use GRID so buttons never disappear -----
        self.frame.grid_columnconfigure(0, weight=1)   # single column
        self.frame.grid_rowconfigure(1, weight=1)      # row 1 (tree area) expands

        # Header (row 0)
        hdr = tk.Frame(self.frame, bg="#2c3e50")
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(
            hdr, text="🔔 Notifications", fg="white", bg="#2c3e50",
            font=("Segoe UI", 11, "bold"), padx=10, pady=8
        ).pack(side="left")

        # Tree area with scrollbar (row 1)
        body = tk.Frame(self.frame, bg="#f7f9fc")
        body.grid(row=1, column=0, sticky="nsew", padx=6, pady=(6, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        cols = ("notification_id", "user_id", "book_id", "book_title", "created_at")
        self.tree = ttk.Treeview(body, columns=cols, show="headings")
        for c, w, a in (
            ("notification_id", 80,  "center"),
            ("user_id",         70,  "center"),
            ("book_id",         70,  "center"),
            ("book_title",     180,  "w"),
            ("created_at",     140,  "center"),
        ):
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=w, anchor=a)

        yscroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        # Buttons (row 2)
        btns = tk.Frame(self.frame, bg="#f7f9fc")
        btns.grid(row=2, column=0, sticky="ew", padx=6, pady=8)

        tk.Button(
            btns, text="Confirm", bg="#27ae60", fg="white", bd=0, padx=12, pady=6,
            activebackground="#219653", command=self._confirm, cursor="hand2"
        ).pack(side="left")

        tk.Button(
            btns, text="Reject", bg="#e74c3c", fg="white", bd=0, padx=12, pady=6,
            activebackground="#c0392b", command=self._reject, cursor="hand2"
        ).pack(side="left", padx=6)

        tk.Button(
            btns, text="Refresh", bg="#34495e", fg="white", bd=0, padx=12, pady=6,
            activebackground="#2c3e50", command=self.refresh, cursor="hand2"
        ).pack(side="right")

        # Initial load + auto-refresh
        self.refresh()
        self._job = self.frame.after(5000, self._tick)

    # ---------- Lifecycle ----------
    def destroy(self):
        if self._job:
            try:
                self.frame.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        self.frame.destroy()

    def _tick(self):
        self.refresh()
        self._job = self.frame.after(5000, self._tick)

    # ---------- Data ops ----------
    def refresh(self):
        try:
            conn = self.db.connect()
            cur = conn.cursor(dictionary=True)
            cur.execute(f"""
                SELECT notification_id, user_id, book_id, book_title, created_at
                FROM {self.table}
                WHERE status='PENDING'
                ORDER BY created_at DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            cur.close(); conn.close()
        except Exception as e:
            messagebox.showerror("DB Error", f"Load failed:\n{e}")
            rows = []

        # Clear + repopulate
        for i in self.tree.get_children():
            self.tree.delete(i)

        for r in rows:
            ts = r.get("created_at")
            if isinstance(ts, datetime):
                ts = ts.strftime("%Y-%m-%d %H:%M")
            self.tree.insert(
                "", "end",
                values=(
                    r.get("notification_id"),
                    r.get("user_id"),
                    r.get("book_id"),
                    r.get("book_title", ""),
                    ts or ""
                )
            )

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a notification row.")
            return None
        # values: [notification_id, user_id, book_id, book_title, created_at]
        return self.tree.item(sel[0])["values"]

    def _confirm(self):
        vals = self._selected()
        if not vals:
            return
        notif_id, user_id, book_id = vals[0], vals[1], vals[2]

        # Send IDs back to lending form first
        if self.on_confirm:
            try:
                self.on_confirm(str(user_id), str(book_id))
            except Exception as e:
                messagebox.showwarning("Prefill", f"Callback failed:\n{e}")

     
        try:
            conn = self.db.connect(); cur = conn.cursor()
            cur.execute(f"UPDATE {self.table} SET status = 'CONFIRMED' WHERE notification_id = %s", (notif_id,))
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            messagebox.showerror("DB Error", f"Status Change failed:\n{e}")
            return

        self.refresh()

    def _reject(self):
        vals = self._selected()
        if not vals:
            return
        notif_id = vals[0]

       
        try:
            conn = self.db.connect(); cur = conn.cursor()
            cur.execute(f"UPDATE {self.table} SET status = 'REJECTED' WHERE notification_id = %s", (notif_id,))
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            messagebox.showerror("DB Error", f"Status Change failed:\n{e}")
            return

        self.refresh()
