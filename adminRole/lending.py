import tkinter as tk
from tkinter import ttk, messagebox
from prediction_model import predict_holding_days
import mysql.connector
from datetime import datetime, timedelta
from database import Database
from adminRole.notification_sidebar import SidebarNotifications

class lending:
    """Class for managing lending records in the library system"""
    
    def __init__(self, parent, content_frame, title_font, label_font, button_font,go_back_callback):
        self.parent = parent
        self.content_frame = content_frame
        self.title_font = title_font
        self.label_font = label_font
        self.button_font = button_font
        self.entries = {}
        self.validation_frame = None
        self.go_back_callback = go_back_callback
        self.db = Database()
        self.sidebar = None 
        

    def clear_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def validate_numeric_input(self, P, field_name, max_length=None):
           
            if not P:
                self.clear_validation_error(field_name)
                return True
                
            if not P.isdigit():
                self.show_validation_error(field_name, "Only numbers are allowed!")
                return False
                
            if max_length and len(P) > max_length:
                self.show_validation_error(field_name, f"Maximum {max_length} digits allowed!")
                return False
                
            self.clear_validation_error(field_name)
            return True

    def show_validation_error(self, field_name, message):
            """Show an error message for a specific field"""
            full_message = f"{field_name}: {message}"
            messagebox.showerror("Validation Error", full_message)

    def clear_validation_error(self, field_name):
            """Clear any validation error for a field"""
            if hasattr(self, f"{field_name}_error"):
                getattr(self, f"{field_name}_error").config(text="")

    def lending(self):
          
            # Clear the content frame for new form  
            self.clear_frame()

            # Main form container (white with light gray border)
            form_container = tk.Frame(
                self.content_frame, 
                bg="white", 
                bd=0, 
                highlightbackground="#d1d8e0",  # Light gray border color
                highlightthickness=1           # 1px border
            )
            form_container.pack(fill="both", expand=True, padx=20, pady=20)  # 20px padding

            # Form header (blue bar)
            header = tk.Frame(form_container, bg="#3498db", height=50)  # 50px tall
            header.pack(fill="x", pady=(0, 20))  # Fill width with 20px bottom padding

            # Toggle button on the right side of the header
            # toggle_btn = tk.Button(
            #     header,
            #     text="⟨Notifications",
            #     font=self.button_font,
            #     bg="#2c3e50", fg="white", bd=0,
            #     activebackground="#2c3e50", activeforeground="white",
            #     cursor="hand2",
            #     command=lambda: self._toggle_sidebar(parent=body)  # parent=body so it sits to the right of the form
            # )
            # toggle_btn.pack(side="right", padx=10, pady=6)
            
            # Check notification status
            has_notifs = self._has_pending_notifications()

            toggle_btn = tk.Button(
                header,
                text="🔔 Notifications",bd=2, highlightbackground="#000000", 
                font=self.button_font,
                bg=("#e74c3c" if has_notifs else "#27ae60"),  # Red if has pending, Green if none
                fg="white", 
                activebackground="#2c3e50", activeforeground="white",
                cursor="hand2",
                command=lambda: self._toggle_sidebar(parent=body)
            )
            toggle_btn.pack(side="right", padx=10, pady=6)
            
            


            # Form title
            tk.Label(header, text="Lending Management", 
                    font=self.title_font, bg="#3498db", fg="white").pack(pady=10)  # Centered with 10px padding

          
            body = tk.Frame(form_container, bg="white")
            body.pack(fill="both", expand=True)

            # Form area lives on the left side of body
            form_fields = tk.Frame(body, bg="white", padx=30, pady=20)
            form_fields.pack(side="left", fill="both", expand=True)

            # Left column inside the form area
            left_column = tk.Frame(form_fields, bg="white")
            left_column.pack(side="left", fill="both", expand=True, padx=(0, 20))

            # Field definitions: (Label text, field name, max length)
            fields = [
                ("User ID", "user_id", 3),      
                ("Book ID", "book_id", 10),      
                ("Borrow Date", "borrow_date", None),  
                ("Return Date", "return_date", None),
                ("Number of Pages", "pages", 7)  
            ]

            self.entries = {}  
            today = datetime.now()
            return_date = today + timedelta(days=14)  
            
            # Frame for validation messages
            self.validation_frame = tk.Frame(left_column, bg="white")
            self.validation_frame.pack(fill="x", pady=(0, 10))  
            
            # Create each form field
            for label_text, field_name, max_len in fields:
                # Container frame for label + input
                frame = tk.Frame(left_column, bg="white")
                frame.pack(fill="x", pady=8)  # 8px vertical padding between fields

                # Field label (left-aligned, 25 characters wide)
                tk.Label(frame, text=label_text, font=self.label_font, 
                        bg="white", fg="#2c3e50", width=25, anchor="w").pack(side="left")

                # Handle date fields differently (display only)
                if field_name == "borrow_date":
                    date_str = today.strftime("%Y-%m-%d")
                    date_label = tk.Label(frame, text=date_str, font=self.label_font, 
                                        bg="#ecf0f1", fg="#2c3e50", relief="flat", 
                                        width=20, anchor="w", padx=5)
                    date_label.pack(side="right", fill="x", expand=True, ipady=4)
                    self.entries[field_name] = date_str
                    
                elif field_name == "return_date":
                    return_str = return_date.strftime("%Y-%m-%d")
                    return_label = tk.Label(frame, text=return_str, font=self.label_font, 
                                        bg="#ecf0f1", fg="#2c3e50", relief="flat", 
                                        width=20, anchor="w", padx=5)
                    return_label.pack(side="right", fill="x", expand=True, ipady=4)
                    self.entries[field_name] = return_str
                else:
                    # For editable fields, set up validation
                    vcmd = (self.parent.register(
                        lambda P, field=field_name, ml=max_len: 
                        self.validate_numeric_input(P, field, ml)), '%P')
                    
                    # Create the input field if you need can change lenght size
                    entry = tk.Entry(
                        frame, 
                        font=self.label_font, 
                        bg="#ecf0f1",        
                        fg="#2c3e50",        
                        relief="flat",       
                        highlightthickness=1, 
                        highlightbackground="#bdc3c7",  
                        highlightcolor="#3498db",     
                        validate="key",      
                        validatecommand=vcmd, 
                        
                    )
                    entry.pack(side="right", fill="x", expand=True, ipady=4)  # Right-aligned input
                    self.entries[field_name] = entry  # Store reference

            # Right column for radio buttons
            right_column = tk.Frame(form_fields, bg="white", width=250)
            right_column.pack(side="right", fill="both", padx=(20, 0)) 

            # User Role selection frame
            role_frame = tk.LabelFrame(
                right_column, 
                text="User Role", 
                font=self.label_font, 
                bg="white", 
                fg="#2c3e50",
                padx=10,  
                pady=10   
            )
            role_frame.pack(fill="x", pady=(0, 15))  # 15px bottom padding

            self.user_role = tk.StringVar(value="student")  # Default selection
            roles = [("Staff", "staff"), ("Student", "student")]
            
            # Create radio buttons for user roles
            for text, value in roles:
                rb = tk.Radiobutton(
                    role_frame, 
                    text=text, 
                    variable=self.user_role, 
                    value=value, 
                    font=self.label_font, 
                    bg="white", 
                    fg="#2c3e50", 
                    selectcolor="#3498db",  
                    activebackground="white", 
                    activeforeground="#2c3e50"
                )
                rb.pack(anchor="w", pady=3)  

            # Book Category selection frame
            category_frame = tk.LabelFrame(
                right_column, 
                text="Book Category", 
                font=self.label_font, 
                bg="white", 
                fg="#2c3e50",
                padx=10, 
                pady=10
            )
            category_frame.pack(fill="x")

            self.book_category = tk.StringVar(value="fiction")  # Default selection
            categories = [
                ("Fiction", "fiction"),
                ("History", "history"),
                ("Non-Fiction", "non-fiction"),
                ("Science", "science")
            ]
            
            # Create radio buttons for categories
            for text, value in categories:
                rb = tk.Radiobutton(
                    category_frame, 
                    text=text, 
                    variable=self.book_category, 
                    value=value, 
                    font=self.label_font, 
                    bg="white", 
                    fg="#2c3e50", 
                    selectcolor="#3498db", 
                    activebackground="white", 
                    activeforeground="#2c3e50"
                )
                rb.pack(anchor="w", pady=3)  # Left-aligned with 3px vertical padding

            # Button container at bottom of form
            button_frame = tk.Frame(form_container, bg="white", pady=20)  # 20px vertical padding
            button_frame.pack(fill="x")

            # Submit button (green)
            tk.Button(
                button_frame, 
                text="Submit & Predict", 
                font=self.button_font, 
                bg="#27ae60",  # Green
                fg="white", 
                bd=0, 
                padx=25,       # 25px horizontal padding
                pady=10,       # 10px vertical padding
                activebackground="#219653",  # Darker green when clicked
                activeforeground="white",
                cursor="hand2", 
                command=self.submit_lending
            ).pack(side="left", padx=10)  # Left-aligned with 10px padding

            # Back button (dark blue)
            tk.Button(
                button_frame, 
                text="Back to Admin Panel", 
                font=self.button_font, 
                bg="#033974",  # Dark blue
                fg="white", 
                bd=0, 
                padx=25, 
                pady=10,
                activebackground="#7f8c8d",  # Gray when clicked
                activeforeground="white",
                cursor="hand2", 
                command=self.go_back_callback
            ).pack(side="right", padx=10)  # Right-aligned with 10px padding
    
        
       
    
    def submit_lending(self):
            """Handle form submission for lending records"""
            try:
                # Get values from form fields
                user_id = self.entries["user_id"].get().strip()
                book_id = self.entries["book_id"].get().strip()
                borrow_date = self.entries["borrow_date"]
                return_date = self.entries["return_date"]
                pages_str = self.entries["pages"].get().strip()

                # Validate all required fields
                if not user_id:
                    self.show_validation_error("user_id", "User ID is required!")
                    return
                if len(user_id) > 3:
                    self.show_validation_error("user_id", "User ID must be 3 digits or less!")
                    return
                if not user_id.isdigit():
                    self.show_validation_error("user_id", "User ID must be numeric!")
                    return

                if not book_id:
                    self.show_validation_error("book_id", "Book ID is required!")
                    return
                if len(book_id) > 10:
                    self.show_validation_error("book_id", "Book ID must be 10 digits or less!")
                    return
                if not book_id.isdigit():
                    self.show_validation_error("book_id", "Book ID must be numeric!")
                    return

                if not pages_str:
                    self.show_validation_error("pages", "Pages is required!")
                    return
                if len(pages_str) > 7:
                    self.show_validation_error("pages", "Pages must be 7 digits or less!")
                    return
                if not pages_str.isdigit():
                    self.show_validation_error("pages", "Pages must be numeric!")
                    return

                pages = int(pages_str)
                if pages <= 0:
                    self.show_validation_error("pages", "Pages must be greater than 0!")
                    return

                # Get selected values from radio buttons
                user_role = self.user_role.get()
                book_category = self.book_category.get()

                # Prepare features for prediction
                features = [
                    pages,
                    1 if user_role == "staff" else 0,
                    1 if user_role == "student" else 0,
                    1 if book_category == "fiction" else 0,
                    1 if book_category == "history" else 0,
                    1 if book_category == "non-fiction" else 0,
                    1 if book_category == "science" else 0,
                    int(user_id),
                    int(book_id)
                ]

            
                conn = self.db.connect()
                cursor = conn.cursor()

            
                
                # --- Normalize IDs once ---
                uid_int = int(user_id)          # e.g. 1
                bid_int = int(book_id)          # e.g. 239
                uid_pad = str(uid_int).zfill(3) # '001' style
                bid_pad = str(bid_int).zfill(3) # '239' -> '239' (still fine)

                # --- Check existence (works whether columns are VARCHAR like '001' or INT like 1) ---
                cursor.execute("""SELECT 1 FROM members WHERE member_id = %s            
                    OR CAST(member_id AS UNSIGNED) = %s  -- numeric match (handles 1)
                    LIMIT 1
                """, (uid_pad, uid_int))
                user_exists = cursor.fetchone() is not None

                cursor.execute("""
                    SELECT 1
                    FROM books
                    WHERE book_id = %s
                    OR CAST(book_id AS UNSIGNED) = %s
                    LIMIT 1
                """, (bid_pad, bid_int))
                book_exists = cursor.fetchone() is not None

                if not user_exists:
                    messagebox.showerror("Error", f"User ID {user_id} does not exist.")
                    return

                if not book_exists:
                    messagebox.showerror("Error", f"Book ID {book_id} does not exist.")
                    return
                

                # Get prediction and show success message
                prediction = predict_holding_days(features)
                messagebox.showinfo(
                    "Success", 
                    f"Lending record created successfully!\n\n"
                    f"Predicted Holding Days: {prediction:.2f} days"
                )
                

                # SQL query to insert lending record
                sql = """
                INSERT INTO lending_records (user_id, book_id, borrow_date, return_date, predict_date,pages,
                    user_role_staff, user_role_student, book_category_fiction, book_category_history,
                    book_category_nonfiction, book_category_science)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s)
                """
                 
                # Values for the SQL query
                values = (
                    user_id,  # user_id
                    book_id,  # book_id
                    borrow_date,
                    return_date,
                    int(prediction),
                    pages,
                    features[1],  # user_role_staff
                    features[2],  # user_role_student
                    features[3],  # book_category_fiction
                    features[4],  # book_category_history
                    features[5],  # book_category_nonfiction
                    features[6]   # book_category_science
                )
                cursor.execute(sql, values)
                conn.commit()
                cursor.close()
                conn.close()

                messagebox.showinfo("Success","Insert Success")
            except ValueError as ve:
                messagebox.showerror("Input Error", str(ve))
            except mysql.connector.Error as err:
                messagebox.showerror("Database Error", f"Error: {err}")
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")


    def _toggle_sidebar(self, parent):
        """Show/hide the right sidebar with notifications."""
        # If sidebar exists -> destroy (hide). Else -> create (show).
        if self.sidebar and hasattr(self.sidebar, "destroy"):
            self.sidebar.destroy()
            self.sidebar = None
            return

        # Create a new sidebar on the right side of 'parent' (the body frame)
        self.sidebar = SidebarNotifications(
            parent=parent,              # <-- packs to side="right" inside this body
            db=self.db,
            on_confirm=self._prefill_from_notification,  # callback into this form
            table_name="user_notifications"              # adjust if your table differs
        )

    def _prefill_from_notification(self, user_id: str, book_id: str):
        """Callback used by the sidebar 'Confirm' button to prefill form fields."""
        # Ensure entries exist and are editable
        if "user_id" in self.entries and hasattr(self.entries["user_id"], "delete"):
            self.entries["user_id"].delete(0, tk.END)
            self.entries["user_id"].insert(0, user_id)

        if "book_id" in self.entries and hasattr(self.entries["book_id"], "delete"):
            self.entries["book_id"].delete(0, tk.END)
            self.entries["book_id"].insert(0, book_id)

        try:
            self.entries["pages"].focus_set()
        except Exception:
            pass


    def _has_pending_notifications(self):
        """Return True if there are pending notifications in the table."""
        try:
            conn = self.db.connect()
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM user_notifications WHERE status='PENDING'")
            count = cur.fetchone()[0]
            cur.close(); conn.close()
            return count > 0
        except Exception as e:
            print("DB check failed:", e)
            return False
    
  