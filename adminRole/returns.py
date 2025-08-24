
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime, timedelta
import mysql.connector
from database import Database

class Returns:
    
    def __init__(self, parent, content_frame, title_font, label_font, button_font, go_back_callback):
        self.parent = parent
        self.content_frame = content_frame
        self.title_font = title_font
        self.label_font = label_font
        self.button_font = button_font
        self.show_admin_main_menu = go_back_callback
        self.db = Database()
        self.return_entries = {}
        

    def clear_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def returns(self):
        self.clear_frame()

        form_container = tk.Frame(self.content_frame, bg="white", bd=0,
                                  highlightbackground="#d1d8e0", highlightthickness=1)
        form_container.pack(fill="both", expand=True, padx=20, pady=20)

        header = tk.Frame(form_container, bg="#e67e22", height=50)
        header.pack(fill="x", pady=(0, 20))

        tk.Label(header, text="Returns Management",
                 font=self.title_font, bg="#e67e22", fg="white").pack(pady=10)

        form_fields = tk.Frame(form_container, bg="white", padx=30, pady=20)
        form_fields.pack(fill="both", expand=True)

        left_column = tk.Frame(form_fields, bg="white")
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 20))

        fields = [
            ("User ID", "user_id"),
            ("Book ID", "book_id"),
            ("Borrow Date", "borrow_date"),
            ("Expected Return Date", "expected_return_date"),
            ("Actual Return Date", "actual_return_date"),
            ("Predicted Date", "predicted_date"),
            ("Overdue Days", "overdue_days"),
            ("Fine (Rs.)", "fine")
        ]

        today = datetime.now()
        for label_text, field_name in fields:
            frame = tk.Frame(left_column, bg="white")
            frame.pack(fill="x", pady=8)

            tk.Label(frame, text=label_text, font=self.label_font,
                     bg="white", fg="#2c3e50", width=25, anchor="w").pack(side="left")

            entry = tk.Entry(frame, font=self.label_font, bg="#ecf0f1",
                             fg="#2c3e50", relief="flat", highlightthickness=1,
                             highlightbackground="#bdc3c7", highlightcolor="#e67e22")
            entry.pack(side="right", fill="x", expand=True, ipady=4)

            if field_name in ["borrow_date", "expected_return_date", "predicted_date","overdue_days", "fine"]:
                entry.config(state="readonly")

            self.return_entries[field_name] = entry

        right_column = tk.Frame(form_fields, bg="white", width=250)
        right_column.pack(side="right", fill="both", padx=(20, 0))

        tk.Button(right_column, text="Fetch Record",
                  font=self.button_font, bg="#3498db", fg="white",
                  bd=0, padx=10, pady=10,
                  command=self.fetch_borrow_info).pack(fill="x", pady=(0, 15))

        tk.Button(right_column, text="Calculate Fine",
                  font=self.button_font, bg="#e74c3c", fg="white",
                  bd=0, padx=10, pady=10,
                  command=self.calculate_fine).pack(fill="x", pady=(0, 15))

        tk.Button(right_column, text="Submit Return",
                  font=self.button_font, bg="#27ae60", fg="white",
                  bd=0, padx=10, pady=10,
                  command=self.submit_return).pack(fill="x",pady=(0, 190))

    
        tk.Button(right_column, text="Back to Admin Panel",
                  font=self.button_font, bg="#033974", fg="white",
                  bd=0, padx=10, pady=10,
                  activebackground="#7f8c8d", activeforeground="white",
                  cursor="hand2", command=self.show_admin_main_menu).pack(fill="x", pady=(15, 15))

    def submit_return(self):
        try:
            user_id = self.return_entries["user_id"].get().strip()
            book_id = self.return_entries["book_id"].get().strip()
            borrow_date = self.return_entries["borrow_date"].get().strip()
            expected_return_date = self.return_entries["expected_return_date"].get().strip()
            actual_return_date = self.return_entries["actual_return_date"].get().strip()
            predicted_date = self.return_entries["predicted_date"].get().strip()
            overdue_days = self.return_entries["overdue_days"].get().strip()
            fine = self.return_entries["fine"].get().strip()

            if not (user_id and book_id and actual_return_date):
                messagebox.showerror("Validation Error", "Please fetch record and fill required fields.")
                return

            conn = self.db.connect()
            cursor = conn.cursor()
            insert_sql = """
                INSERT INTO return_records (
                    user_id, book_id, borrow_date, expected_return_date, actual_return_date,predicted_date,
                    overdue_days, fine
                ) VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
            """
            values = (
                user_id, book_id, borrow_date, expected_return_date,
                actual_return_date, predicted_date,int(overdue_days), float(fine)
            )

            cursor.execute(insert_sql, values)
            conn.commit()
            
            
            # 2. Delete the lending record after return
            delete_sql = """
                DELETE FROM lending_records
                WHERE user_id = %s AND book_id = %s AND borrow_date = %s
            """
            cursor.execute(delete_sql, (user_id, book_id, borrow_date))

            conn.commit()
            cursor.close()
            conn.close()

            messagebox.showinfo("Success", "Return record submitted successfully.")

            # ✅ Clear all fields after success
            for key, entry in self.return_entries.items():
                entry.config(state="normal")
                entry.delete(0, tk.END)
                if key in ["borrow_date", "expected_return_date", "actual_return_date","predicted_date", "overdue_days", "fine"]:
                    entry.config(state="readonly")

        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")


    def fetch_borrow_info(self):
        try:
            user_id = self.return_entries["user_id"].get().strip()
            book_id = self.return_entries["book_id"].get().strip()

            if not user_id or not book_id:
                messagebox.showwarning("Input Error", "Please enter both User ID and Book ID.")
                return

            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT borrow_date, return_date,predict_date FROM lending_records
                WHERE user_id = %s AND book_id = %s
                ORDER BY borrow_date DESC LIMIT 1
            """, (user_id, book_id))
            row = cursor.fetchone()

            if row:
                self.return_entries["borrow_date"].config(state="normal")
                self.return_entries["expected_return_date"].config(state="normal")
                self.return_entries["predicted_date"].config(state="normal")
                
                self.return_entries["borrow_date"].delete(0, tk.END)
                self.return_entries["expected_return_date"].delete(0, tk.END)
                self.return_entries["predicted_date"].delete(0, tk.END)
                
                self.return_entries["borrow_date"].insert(0, row[0])
                self.return_entries["expected_return_date"].insert(0, row[1])
                self.return_entries["predicted_date"].insert(0, row[2])
                
                self.return_entries["borrow_date"].config(state="readonly")
                self.return_entries["expected_return_date"].config(state="readonly")
                self.return_entries["predicted_date"].config(state="readonly")
            else:
                messagebox.showinfo("Not Found", "No lending record found.")

        except Exception as e:
            messagebox.showerror("Database Error", str(e))
        finally:
            if 'conn' in locals() and conn:
                conn.close()


    def calculate_fine(self):
        try:
            expected_return_date = self.return_entries["expected_return_date"].get().strip()
            if not expected_return_date:
                messagebox.showwarning("Missing Info", "Fetch borrow record first.")
                return

            today = datetime.today().date()
            actual_return = today
            expected_return = datetime.strptime(expected_return_date, "%Y-%m-%d").date()

            overdue_days = (actual_return - expected_return).days
            overdue_days = max(0, overdue_days)
            fine_amount = overdue_days * 5

            self.return_entries["actual_return_date"].config(state="normal")
            self.return_entries["overdue_days"].config(state="normal")
            self.return_entries["fine"].config(state="normal")

            self.return_entries["actual_return_date"].delete(0, tk.END)
            self.return_entries["overdue_days"].delete(0, tk.END)
            self.return_entries["fine"].delete(0, tk.END)

            self.return_entries["actual_return_date"].insert(0, actual_return)
            self.return_entries["overdue_days"].insert(0, overdue_days)
            self.return_entries["fine"].insert(0, f"{fine_amount:.2f}")

            self.return_entries["actual_return_date"].config(state="readonly")
            self.return_entries["overdue_days"].config(state="readonly")
            self.return_entries["fine"].config(state="readonly")

        except Exception as e:
            messagebox.showerror("Calculation Error", str(e))

