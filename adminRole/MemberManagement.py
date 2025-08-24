from database import Database
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import cv2

class MemberManagement:
    def __init__(self, parent, go_back_callback):
        self.parent = parent
        self.go_back_callback = go_back_callback
        self.db = Database()
        self.photo_data = None  # Store image bytes
        self.create_widgets()

    def create_widgets(self):
        for widget in self.parent.winfo_children():
            widget.destroy()

        self.main_frame = tk.Frame(self.parent, padx=15, pady=15)
        self.main_frame.pack(expand=True, fill="both")

        self.input_frame = tk.LabelFrame(self.main_frame, text="Member Details", padx=15, pady=15)
        self.input_frame.pack(padx=10, pady=10, fill="x")

        self.input_frame.columnconfigure(1, weight=1)
        self.entries = {}

        tk.Label(self.input_frame, text="Member ID", anchor="w").grid(row=0, column=0, sticky="ew", pady=2, padx=5)
        member_id_entry = tk.Entry(self.input_frame)
        member_id_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=5, ipady=4)
        self.entries["member_id"] = member_id_entry

        tk.Label(self.input_frame, text="Name", anchor="w").grid(row=1, column=0, sticky="ew", pady=2, padx=5)
        name_entry = tk.Entry(self.input_frame)
        name_entry.grid(row=1, column=1, sticky="ew", pady=10, padx=5, ipady=4)
        self.entries["name"] = name_entry
        
        tk.Label(self.input_frame, text="Age", anchor="w").grid(row=2, column=0, sticky="ew", pady=2, padx=5)
        name_entry = tk.Entry(self.input_frame)
        name_entry.grid(row=2, column=1, sticky="ew", pady=10, padx=5, ipady=4)
        self.entries["age"] = name_entry

        tk.Label(self.input_frame, text="Email", anchor="w").grid(row=3, column=0, sticky="ew", pady=2, padx=5)
        email_entry = tk.Entry(self.input_frame)
        email_entry.grid(row=3, column=1, sticky="ew", pady=10, padx=5, ipady=4)
        self.entries["email"] = email_entry

        tk.Label(self.input_frame, text="Contact Number", anchor="w").grid(row=4, column=0, sticky="ew", pady=2, padx=5)
        contact_entry = tk.Entry(self.input_frame)
        contact_entry.grid(row=4, column=1, sticky="ew", pady=10, padx=5, ipady=4)
        self.entries["contact"] = contact_entry

        tk.Label(self.input_frame, text="Photo", anchor="w").grid(row=5, column=0, sticky="ew", pady=2, padx=5)
        photo_frame = tk.Frame(self.input_frame)
        photo_frame.grid(row=5, column=1, sticky="w", pady=10, padx=5)

        tk.Button(photo_frame, text="📁 Browse", command=self.browse_photo).pack(side="left", padx=2)
        tk.Button(photo_frame, text="📷 Capture", command=self.capture_photo).pack(side="left", padx=2)

        self.button_frame = tk.Frame(self.main_frame, pady=10)
        self.button_frame.pack(padx=10, pady=5, fill="x")

        button_style = {
            'padx': 10, 'pady': 5, 'width': 11,
            'font': ("Arial", 14), 'bg': "#219653", 'fg': "white", 'bd': 0,
            'activebackground': "#7f8c8d"
        }

        tk.Button(self.button_frame, text="Add Member", command=self.add_member, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Update Member", command=self.update_member, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Delete Member", command=self.delete_member, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Clear Fields", command=self.clear_entries, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Back to Admin Panel", command=self.go_back_callback, font=("Arial", 14), bg="#033974", fg="white", bd=0, padx=10, pady=5).pack(side="right", padx=5)

        self.tree_frame = tk.Frame(self.main_frame, padx=10, pady=5)
        self.tree_frame.pack(expand=True, fill="both")

        tree_scroll = ttk.Scrollbar(self.tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(self.tree_frame, columns=("ID", "Name", "Age","Email", "Contact"), show="headings", yscrollcommand=tree_scroll.set)
        self.tree.pack(expand=True, fill="both")
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("ID", text="Member ID", anchor="w")
        self.tree.heading("Name", text="Name", anchor="w")
        self.tree.heading("Age", text="Age", anchor="w")
        self.tree.heading("Email", text="Email", anchor="w")
        self.tree.heading("Contact", text="Contact No", anchor="w")

        self.tree.column("ID", width=80, stretch=tk.NO)
        self.tree.column("Name", width=100)
        self.tree.column("Age", width=40)
        self.tree.column("Email", width=120)
        self.tree.column("Contact", width=100)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_select)

        self.load_members()

    def browse_photo(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if file_path:
            with open(file_path, 'rb') as f:
                self.photo_data = f.read()
            messagebox.showinfo("Photo Loaded", "Image loaded successfully!")

    def capture_photo(self):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cap.release()
            cv2.destroyAllWindows()
            success, buffer = cv2.imencode('.jpg', frame)
            if success:
                self.photo_data = buffer.tobytes()
                messagebox.showinfo("Photo Captured", "Camera image captured successfully!")
        else:
            cap.release()
            messagebox.showerror("Camera Error", "Could not access camera.")

    def clear_entries(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.photo_data = None

    def on_tree_select(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, 'values')
            self.clear_entries()
            self.entries["member_id"].insert(0, values[0])
            self.entries["name"].insert(0, values[1])
            self.entries["age"].insert(0, values[2])
            self.entries["email"].insert(0, values[3])
            self.entries["contact"].insert(0, values[4])

    def validate_inputs(self):
        member_id = self.entries["member_id"].get().strip()
        name = self.entries["name"].get().strip()
        age = self.entries["age"].get().strip()
        email = self.entries["email"].get().strip()
        contact = self.entries["contact"].get().strip()

        if not re.fullmatch(r'\d{3}', member_id):
            messagebox.showwarning("Input Error", "Member ID must be exactly 3 digits (numbers only).")
            return None
        if not name:
            messagebox.showwarning("Input Error", "Name is required.")
            return None
        if not re.fullmatch(r'\d{2}', age):
            messagebox.showwarning("Input Error", "Invalid Age format.")
            return None
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showwarning("Input Error", "Invalid email format.")
            return None
        if not re.fullmatch(r'\d{10}', contact):
            messagebox.showwarning("Input Error", "Contact number must be exactly 10 digits (numbers only).")
            return None

        return member_id, name,age, email, contact

    def add_member(self):
        data = self.validate_inputs()
        if not data:
            return
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO members (member_id, name,age, email, contact, photo) VALUES (%s, %s,%s, %s, %s, %s)", (*data, self.photo_data))
            conn.commit()
            messagebox.showinfo("Success", "Member added successfully!")
            self.load_members()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add member: {e}")
        finally:
            conn.close()

    def update_member(self):
        data = self.validate_inputs()
        if not data:
            return
        member_id, name, age,email, contact = data
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("UPDATE members SET name=%s, age=%s,email=%s, contact=%s, photo=%s WHERE member_id=%s", (name, age,email, contact, self.photo_data, member_id))
            conn.commit()
            if cursor.rowcount:
                messagebox.showinfo("Success", "Member updated successfully!")
            else:
                messagebox.showwarning("Not Found", "Member ID not found.")
            self.load_members()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update member: {e}")
        finally:
            conn.close()

    def delete_member(self):
        member_id = self.entries["member_id"].get().strip()
        if not member_id:
            messagebox.showwarning("Select Member", "Please select a member to delete.")
            return
        if not messagebox.askyesno("Confirm", f"Delete member ID: {member_id}?"):
            return
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM members WHERE member_id=%s", (member_id,))
            conn.commit()
            if cursor.rowcount:
                messagebox.showinfo("Deleted", "Member deleted successfully!")
            else:
                messagebox.showwarning("Not Found", "Member not found.")
            self.load_members()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete member: {e}")
        finally:
            conn.close()

    def load_members(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT member_id, name, age,email, contact FROM members ORDER BY member_id")
            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load members: {e}")
        finally:
            conn.close()

