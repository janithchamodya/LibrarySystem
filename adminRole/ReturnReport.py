
import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from database import Database
from datetime import datetime

class ReturnReport:
    def __init__(self, parent, content_frame, title_font, label_font, button_font, go_back_callback):
        self.parent = parent
        self.content_frame = content_frame
        self.title_font = title_font
        self.label_font = label_font
        self.button_font = button_font
        self.go_back_callback = go_back_callback
        self.db = Database()

    def clear_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_report(self):
        self.clear_frame()

        # Heading
        tk.Label(self.content_frame, text="Return Report Summary", font=self.title_font, bg="white", fg="#2c3e50").pack(pady=10)

        # Treeview for return history
        tree_frame = tk.Frame(self.content_frame, bg="white")
        tree_frame.pack(fill="both", expand=True, padx=0, pady=0)

        columns = ("user_id", "book_id", "borrow_date", "expected_return_date", "actual_return_date", "overdue_days", "fine")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Fetch data
        self.populate_treeview()

        # Summary Statistics
        summary_frame = tk.Frame(self.content_frame, bg="white")
        summary_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.total_returns_label = tk.Label(summary_frame, font=self.label_font, bg="white")
        self.total_returns_label.pack(anchor="w")

        self.total_fines_label = tk.Label(summary_frame, font=self.label_font, bg="white")
        self.total_fines_label.pack(anchor="w")

        self.avg_overdue_label = tk.Label(summary_frame, font=self.label_font, bg="white")
        self.avg_overdue_label.pack(anchor="w")

        self.this_month_label = tk.Label(summary_frame, font=self.label_font, bg="white")
        self.this_month_label.pack(anchor="w")

        self.populate_summary()

        # Back Button
        tk.Button(
            self.content_frame,
            text="Back to Admin Panel",
            command=self.go_back_callback,
            font=self.button_font,
            bg="#033974",
            fg="white",
            padx=20,
            pady=10,
            bd=0
        ).pack(pady=10)

    def populate_treeview(self):
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, book_id, borrow_date, expected_return_date, actual_return_date, overdue_days, fine FROM return_records")
            rows = cursor.fetchall()
            for row in rows:
                self.tree.insert("", "end", values=row)
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", str(err))

    def populate_summary(self):
        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*), SUM(fine), AVG(overdue_days) FROM return_records")
            total, total_fine, avg_overdue = cursor.fetchone()

            month_start = datetime.today().replace(day=1).strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) FROM return_records WHERE actual_return_date >= %s", (month_start,))
            monthly_returns = cursor.fetchone()[0]

            self.total_returns_label.config(text=f"Total Returns: {total}")
            self.total_fines_label.config(text=f"Total Fines Collected: Rs. {total_fine:.2f}" if total_fine else "Total Fines Collected: Rs. 0.00")
            self.avg_overdue_label.config(text=f"Average Overdue Days: {avg_overdue:.2f}" if avg_overdue else "Average Overdue Days: 0")
            self.this_month_label.config(text=f"Books Returned This Month: {monthly_returns}")

            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", str(err))
