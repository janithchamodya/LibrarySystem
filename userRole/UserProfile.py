
from database import Database
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from io import BytesIO

class UserProfile:
    def __init__(self, parent, content_frame, title_font, label_font, button_font, go_back_callback):
        self.parent = parent
        self.content_frame = content_frame
        self.title_font = title_font
        self.label_font = label_font
        self.button_font = button_font
        self.go_back_callback = go_back_callback
        self.db = Database()

    
    def show_profile(self, member_id):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.content_frame.pack_forget()
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=30)

        profile_frame = tk.Frame(self.content_frame, bg="#e6f2ff", bd=2, relief="groove")
        profile_frame.pack(fill="both", expand=True)

        tk.Label(profile_frame, text="📘 Library Membership Profile", font=self.title_font, bg="#e6f2ff", fg="#033974").pack(pady=(20, 10))

        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, age, email, contact, created_at, photo 
                FROM members WHERE member_id = %s
            """, (member_id,))
            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Not Found", "Member not found!")
                return
            full_name, age, email, contact, joined_date, photo_data = row
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load member data: {e}")
            return
        finally:
            if 'conn' in locals():
                conn.close()

        content = tk.Frame(profile_frame, bg="#e6f2ff")
        content.pack(padx=10, pady=10, fill="both", expand=True)

        # === Left: Photo + Personal Info ===
        left_section = tk.Frame(content, bg="#e6f2ff")
        left_section.pack(side="left", padx=20, fill="y", anchor="n")

        photo_section = tk.Frame(left_section, bg="#e6f2ff")
        photo_section.pack(anchor="n", pady=(0, 20))

        if photo_data:
            try:
                img = Image.open(BytesIO(photo_data)).resize((180, 220), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(photo_section, image=photo, bg="#e6f2ff", bd=2, relief="solid")
                img_label.image = photo
                img_label.pack()
            except Exception as e:
                tk.Label(photo_section, text="🖼️ Error loading photo", bg="#e6f2ff", fg="red").pack()
        else:
            tk.Label(photo_section, text="🖼️ No Photo Available", font=self.label_font, bg="#e6f2ff", fg="#555").pack()

        info_section = tk.Frame(left_section, bg="#e6f2ff")
        info_section.pack(anchor="n", fill="x")

        tk.Label(info_section, text="📋 Personal Details", font=("Segoe UI", 16, "bold"), bg="#e6f2ff", fg="#2c3e50").pack(anchor="w", pady=(10, 5))

        details = [
            f"👤 Full Name: {full_name}",
            f"🎂 Age: {age}",
            f"📧 Email: {email}",
            f"📞 Contact No: {contact}",
            f"📅 Joined On: {joined_date.strftime('%Y-%m-%d')}"
        ]
        for line in details:
            tk.Label(info_section, text=line, font=self.label_font, bg="#e6f2ff", fg="#2c3e50").pack(anchor="w", pady=3)

        # === Right: Library Info + Table ===
        lib_section = tk.Frame(content, bg="#e6f2ff")
        lib_section.pack(side="left", padx=20, fill="both", expand=True)

        tk.Label(lib_section, text="📚 Library Details", font=("Segoe UI", 16, "bold"),
                bg="#e6f2ff", fg="#2c3e50").pack(anchor="w", pady=(10, 5))

        library_data = self.get_library_data(member_id)

        tk.Label(lib_section, text=f"📘 Total Books Borrowed: {library_data['total_borrowed']}",
                font=self.label_font, bg="#e6f2ff", fg="#2c3e50").pack(anchor="w", pady=2)

        tk.Label(lib_section, text=f"💰 Total Fine: Rs. {library_data['total_fine']:.2f}",
                font=self.label_font, bg="#e6f2ff", fg="#2c3e50").pack(anchor="w", pady=2)
        
        tk.Label(lib_section, text=f"💰 Total Read Books: {library_data['read_books']}",
                font=self.label_font, bg="#e6f2ff", fg="#2c3e50").pack(anchor="w", pady=2)

        # === Borrowed Books Table ===
        from tkinter import ttk
        table_frame = tk.Frame(lib_section, bg="#e6f2ff")
        table_frame.pack(pady=5, fill="both", expand=True)

        columns = ("Book ID","Book","Borrow Date" ,"Expected Return Date", "Predicted Return Days")
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=120)

        for book_id,book_name,borrow_date, return_date, predict_date in library_data["borrowed_books"]:
            book_id_str=book_id
            borrow_str = borrow_date.strftime("%Y-%m-%d") if borrow_date else "N/A"
            return_str = return_date.strftime("%Y-%m-%d") if return_date else "N/A"
            tree.insert("", "end", values=(book_id_str,book_name, borrow_str,return_str, predict_date))

        tree.pack(padx=5, pady=5, fill="x")

        # === Back button ===
        button_frame = tk.Frame(content, bg="#e6f2ff")
        button_frame.pack(fill="x", pady=200, padx=20)

        tk.Button(
            button_frame,
            text="⬅ Back",
            command=self.go_back_callback,
            font=self.button_font,
            bg="#033974",
            fg="white",
            bd=0,
            padx=20,
            pady=8,
            activebackground="#7f8c8d",
            activeforeground="white",
            cursor="hand2"
        ).pack(side="right")
        
    def get_library_data(self, member_id):
        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM lending_records WHERE user_id = %s", (member_id,))
            total = cursor.fetchone()[0]

            cursor.execute(""" SELECT b.book_id,b.book_name, l.borrow_date,l.return_date, l.predict_date FROM lending_records l
                JOIN books b ON l.book_id = b.book_id
                WHERE l.user_id = %s
            """, (member_id,))
            books = cursor.fetchall()
            cursor.execute("SELECT SUM(fine), COUNT(user_id) FROM return_records WHERE user_id = %s", (member_id,))

            #cursor.execute("SELECT SUM(fine) ,count (user_id) FROM return_records WHERE user_id = %s", (member_id,))
            fine, read_book = cursor.fetchone()
            fine = fine or 0.0
            read_book = read_book or 0

            return {
                "total_borrowed": total,
                "borrowed_books": books,
                "total_fine": fine,
                "read_books": read_book
            }
        except Exception as e:
            return {
                "total_borrowed": 0,
                "borrowed_books": [],
                "total_fine": 0.0,
                "read_books": 0
            }
        finally:
            cursor.close()
            conn.close()    



