
from database import Database
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry  
import re

class BookManagement:
    def __init__(self, parent, go_back_callback):
        self.parent = parent
        self.go_back_callback = go_back_callback
        self.db = Database()
        self.create_widgets()

    def create_widgets(self):
        for widget in self.parent.winfo_children():
            widget.destroy()

        self.main_frame = tk.Frame(self.parent, padx=15, pady=15)
        self.main_frame.pack(expand=True, fill="both")

        self.input_frame = tk.LabelFrame(self.main_frame, text="Book Details", padx=15, pady=15)
        self.input_frame.pack(padx=10, pady=10, fill="x")

        self.input_frame.columnconfigure(1, weight=1)

        labels = ["Book ID", "Title", "Book Name","Author", "Year"]
        self.entries = {}

        # Book ID
        tk.Label(self.input_frame, text="Book ID", anchor="w").grid(row=0, column=0, sticky="ew", pady=2, padx=5)
        book_id_entry = tk.Entry(self.input_frame)
        book_id_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=5,ipady=4 ,)
        self.entries["book_id"] = book_id_entry

        # Title as dropdown
        tk.Label(self.input_frame, text="Title", anchor="w").grid(row=1, column=0, sticky="ew", pady=2, padx=5)
        title_options = ["fiction", "history", "non-fiction", "science"]
        title_combo = ttk.Combobox(self.input_frame, values=title_options, state="readonly")
        title_combo.grid(row=1, column=1, sticky="ew", pady=10, padx=5,ipady=4)
        self.entries["title"] = title_combo

        #Book Name
        tk.Label(self.input_frame, text="Book Name", anchor="w").grid(row=2, column=0, sticky="ew", pady=2, padx=5)
        book_name_entry = tk.Entry(self.input_frame)
        book_name_entry.grid(row=2, column=1, sticky="ew", pady=10, padx=5,ipady=4 ,)
        self.entries["book_name"] = book_name_entry
        
        # Author (300 char limit)
        tk.Label(self.input_frame, text="Author", anchor="w").grid(row=3, column=0, sticky="ew", pady=2, padx=5)
        author_entry = tk.Entry(self.input_frame)
        author_entry.grid(row=3, column=1, sticky="ew", pady=10, padx=5,ipady=4)
        self.entries["author"] = author_entry

        # Year picker
        tk.Label(self.input_frame, text="Year", anchor="w").grid(row=4, column=0, sticky="ew", pady=2, padx=5)
        year_picker = DateEntry(self.input_frame, width=12, background='darkblue', foreground='white', borderwidth=2, year=2025, date_pattern='yyyy-mm-dd')
        year_picker.grid(row=4, column=1, sticky="ew", pady=10, padx=5,ipady=4)
        self.entries["year"] = year_picker

        self.book_id_entry = self.entries["book_id"]
        self.title_entry = self.entries["title"]
        self.name_entry = self.entries["book_name"]
        self.author_entry = self.entries["author"]
        self.year_entry = self.entries["year"]

        self.button_frame = tk.Frame(self.main_frame, pady=10)
        self.button_frame.pack(padx=10, pady=5, fill="x")

        button_style = {'padx': 10, 'pady': 5, 'width': 9, 'font': ("Arial", 16), 'bg': "#219653", 'fg': "white", 'bd': 0, 'activebackground': "#7f8c8d"}

        tk.Button(self.button_frame, text="Add Book", command=self.add_book, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Update Book", command=self.update_book, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Delete Book", command=self.delete_book, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Clear Fields", command=self.clear_entries, **button_style).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Back to Admin Panel", command=self.go_back_callback, font=("Arial", 16), bg="#033974", fg="white", bd=0, padx=10, pady=5, activebackground="#7f8c8d").pack(side="right", padx=5)

        self.tree_frame = tk.Frame(self.main_frame, padx=10, pady=5)
        self.tree_frame.pack(expand=True, fill="both")

        tree_scroll = ttk.Scrollbar(self.tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(self.tree_frame, columns=("ID", "Title", "Name","Author", "Year"), show="headings", yscrollcommand=tree_scroll.set)
        self.tree.pack(expand=True, fill="both")

        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("ID", text="Book ID", anchor="w")
        self.tree.heading("Title", text="Title", anchor="w")
        self.tree.heading("Name", text="Book Name", anchor="w")
        self.tree.heading("Author", text="Author", anchor="w")
        self.tree.heading("Year", text="Year", anchor="w")

        self.tree.column("ID", width=70, minwidth=50, stretch=tk.NO)
        self.tree.column("Title", width=150, minwidth=150, stretch=tk.YES)
        self.tree.column("Name", width=200, minwidth=150, stretch=tk.YES)
        self.tree.column("Author", width=180, minwidth=100, stretch=tk.YES)
        self.tree.column("Year", width=70, minwidth=50, stretch=tk.NO)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_select)

        self.load_books()

    def clear_entries(self):
        for entry in self.entries.values():
            if isinstance(entry, ttk.Combobox):
                entry.set("")
            else:
                entry.delete(0, tk.END)

    def on_tree_select(self, event):
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item, 'values')
            self.clear_entries()
            self.book_id_entry.insert(0, values[0])
            self.title_entry.set(values[1])                  
            self.name_entry.insert(0, values[2])              
            self.author_entry.insert(0, values[3])
            
           

            

    def validate_inputs(self):
        

        book_id = self.book_id_entry.get().strip()
        title = self.title_entry.get().strip()
        book_name = self.name_entry.get().strip()
        author = self.author_entry.get().strip()
        year = self.year_entry.get_date().year  # Only get the year part
        
        if not re.fullmatch(r'\d{1,10}', book_id):
            messagebox.showwarning("Input Error", "Book ID must be numeric and up to 10 digits.")
            return None

        if title not in ["fiction", "history", "non-fiction", "science"]:
            messagebox.showwarning("Input Error", "Title must be selected from the dropdown list.")
            return None
        if len(book_name) > 300:
            messagebox.showwarning("Input Error", "Book Name cannot exceed 300 characters.")
            return None

        if len(author) > 300:
            messagebox.showwarning("Input Error", "Author name cannot exceed 300 characters.")
            return None

        try:
            year_int = int(year)
            if not (1000 <= year_int <= 9999):
                messagebox.showwarning("Input Error", "Year must be a 4-digit number.")
                return None
        except ValueError:
            messagebox.showwarning("Input Error", "Year must be a valid number.")
            return None

        return book_id, title, book_name, author, year


    def add_book(self):
        validated = self.validate_inputs()
        if not validated:
            return
        book_id, title, book_name,author, year = validated
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            sql = "INSERT INTO books (book_id, title, book_name,author, year) VALUES (%s, %s, %s, %s,%s)"
            cursor.execute(sql, (book_id, title, book_name,author, year))
            conn.commit()
            messagebox.showinfo("Success", "Book added successfully!")
            self.load_books()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add book: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def update_book(self):
        validated = self.validate_inputs()
        if not validated:
            return
        book_id, title,book_name, author, year = validated
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            sql = "UPDATE books SET title=%s, book_name=%s,author=%s, year=%s WHERE book_id=%s"
            cursor.execute(sql, (title, book_name,author, year, book_id))
            conn.commit()
            if cursor.rowcount > 0:
                messagebox.showinfo("Success", "Book updated successfully!")
            else:
                messagebox.showwarning("Not Found", "No book found with the given Book ID.")
            self.load_books()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update book: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def delete_book(self):
        book_id = self.book_id_entry.get().strip()
        if not book_id:
            messagebox.showwarning("Selection Error", "Please select a book from the list to delete.")
            return

        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete book ID: {book_id}?"):
            return

        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            sql = "DELETE FROM books WHERE book_id=%s"
            cursor.execute(sql, (book_id,))
            conn.commit()
            if cursor.rowcount > 0:
                messagebox.showinfo("Success", "Book deleted successfully!")
            else:
                messagebox.showwarning("Not Found", "No book found with the given Book ID.")
            self.load_books()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to delete book: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def load_books(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT book_id, title, book_name,author, year FROM books ORDER BY title")
            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load books: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()
