import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk
from admin_panel import AdminPanel
from user_panel import UserPanel
from tkinter import font, simpledialog, messagebox
import os
from database import Database

class LibrarySystemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sri Lankan Library System")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f0f2f5")
        
        self.db = Database()
        
        # Custom font setup
        self.title_font = font.Font(family="Helvetica", size=28, weight="bold")
        self.button_font = font.Font(family="Arial", size=14, weight="bold")
        self.label_font = font.Font(family="Arial", size=16)
        
        # Create main container with background image
        self.main_frame = tk.Frame(root, bg="#f0f2f5")
        self.main_frame.pack(fill="both", expand=True)
        
        # Load background image
        self.bg_image_path = os.path.join("image", "main_frame.jpg")
        if os.path.exists(self.bg_image_path):
            self.bg_image = Image.open(self.bg_image_path)
            self.bg_image = self.bg_image.resize((1200, 700), Image.Resampling.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(self.bg_image)
            self.bg_label = tk.Label(self.main_frame, image=self.bg_photo)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.show_main_menu()

    def show_main_menu(self):
        # Clear existing content
        for widget in self.main_frame.winfo_children():
            if widget != self.bg_label:  # Keep the background image
                widget.destroy()
        
        # Create content container with shadow effect
        content_frame = tk.Frame(self.main_frame, bg="#ffffff", bd=0, 
                                highlightthickness=0, relief="solid")
        content_frame.place(relx=0.5, rely=0.5, anchor="center", width=900, height=500)
        
        # Add subtle shadow
        shadow_frame = tk.Frame(self.main_frame, bg="#d1d8e0")
        shadow_frame.place(relx=0.5, rely=0.5, anchor="center", width=900, height=500)
        shadow_frame.lower(content_frame)
        
        # Left side - Image panel
        left_panel = tk.Frame(content_frame, bg="#3498db")
        left_panel.pack(side="left", fill="both", expand=True)
        
        # Add library logo image
        self.add_library_logo(left_panel)
        
        # Right side - Content panel
        right_panel = tk.Frame(content_frame, bg="#FFFFFF")
        right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=2)
        
        # Header
        header = tk.Frame(right_panel, bg="#ffffff")
        header.pack(fill="x", pady=(0, 30))
        
        tk.Label(header, text="SRI LANKAN LIBRARY", font=self.title_font,padx=20,pady=10,
                bg="#ffffff", fg="#2c3e50").pack(side="top", anchor="w")
        
        tk.Label(header, text="Knowledge for All", font=self.label_font, padx=350,
                bg="#ffffff", fg="#7f8c8d").pack(side="top", anchor="w", pady=(5, 0))
        
        # Separator
        sep = tk.Frame(right_panel, height=2, bg="#ecf0f1")
        sep.pack(fill="x", pady=10)
        
        # Welcome message
        welcome_frame = tk.Frame(right_panel, bg="#ffffff")
        welcome_frame.pack(fill="x", pady=20)
        
        tk.Label(welcome_frame, text="Welcome to the National Library Portal", padx=50,
                font=self.label_font, bg="#ffffff", fg="#2c3e50").pack(anchor="w")
        
        tk.Label(welcome_frame, 
                text="Access thousands of books and resources from across Sri Lanka", padx=20,
                font=("Arial", 12), bg="#ffffff", fg="#7f8c8d").pack(anchor="w", pady=(5, 20))
        
        # Buttons container
        button_frame = tk.Frame(right_panel, bg="#ffffff")
        button_frame.pack(fill="x", pady=20)
        
        # Admin button
        admin_btn = tk.Button(button_frame, text="ADMIN PANEL", font=self.button_font,
                             bg="#3498db", fg="white", bd=0, padx=30, pady=15,
                             activebackground="#2980b9", activeforeground="white",
                             cursor="hand2", command=self.prompt_admin_login)
        admin_btn.pack(side="left", padx=(20, 20))
        
        # User button
        user_btn = tk.Button(button_frame, text="USER PORTAL", font=self.button_font,
                           bg="#2ecc71", fg="white", bd=0, padx=30, pady=15,
                           activebackground="#27ae60", activeforeground="white",
                           cursor="hand2", command=self.prompt_user_login)
        user_btn.pack(side="left")
        
        
    def add_library_logo(self, parent):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "image", "library logo.jpg")

        if os.path.exists(logo_path):
            try:
                logo_image = Image.open(logo_path)
                panel_width = 450
                panel_height = 400

                img_width, img_height = logo_image.size
                ratio = min(panel_width / img_width, panel_height / img_height)
                new_size = (int(img_width * ratio * 0.9), int(img_height * ratio * 0.9))

                logo_image = logo_image.resize(new_size, Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image)

                logo_frame = tk.Frame(parent, bg="#3498db")
                logo_frame.pack(fill="both", expand=True)

                logo_label = tk.Label(logo_frame, image=self.logo_photo, bg="#3498db")
                logo_label.pack(pady=20)

                tk.Label(logo_frame, text=" ජාතික පුස්තකාලය ",
                        font=("Iskoola Pota", 22), bg="#3498db", fg="white").pack(pady=10)
            except Exception as e:
                print(f"[ERROR] Failed to load logo image: {e}")
                self.add_fallback_decorations(parent)
        else:
            print(f"[WARNING] Logo image not found at: {logo_path}")
            self.add_fallback_decorations(parent)

    def add_fallback_decorations(self, parent):
        # Fallback decorative elements if image fails
        decorative_frame = tk.Frame(parent, bg="#3498db")
        decorative_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        tk.Label(decorative_frame, text=" ජාතික පුස්තකාලය ",  # "National Library" in Sinhala
                font=("Iskoola Pota", 22), bg="#3498db", fg="white").pack(pady=20)
        
        tk.Label(decorative_frame, text="National Library\nof Sri Lanka", 
                font=("Helvetica", 18), bg="#3498db", fg="white").pack()

    def prompt_admin_login(self):
        admin_id = simpledialog.askstring("Admin Login", "Enter Admin User Name :", parent=self.root, show='*')
        passsword = simpledialog.askstring("Admin Login", "Enter Admin Password  :", parent=self.root , show='*')
        if admin_id and passsword:
            if admin_id=='admin'and passsword=='admin':
        
                for widget in self.main_frame.winfo_children():
                    if widget != self.bg_label:  # Keep the background image
                        widget.destroy()
                AdminPanel(self.main_frame, self.show_main_menu)
            else:
                messagebox.showerror("Login Failed", "Invalid UserID or Password.")
  
    
    def prompt_user_login(self):
        user_id = simpledialog.askstring("User Login", "Enter your Member ID (e.g., 101):", parent=self.root, show='*')
        contact = simpledialog.askstring("User Login", "Enter your Contact Number (10 digits):", parent=self.root, show='*')

        if user_id and contact:
            if self.validate_user(user_id.strip(), contact.strip()):
                for widget in self.main_frame.winfo_children():
                    if widget != getattr(self, 'bg_label', None):
                        widget.destroy()
                UserPanel(self.main_frame, self.show_main_menu, member_id=user_id.strip())
            else:
                messagebox.showerror("Login Failed", "Invalid Member ID or Contact Number.")


    def validate_user(self, member_id, contact):
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM members WHERE member_id = %s AND contact = %s", (member_id, contact))
            return cursor.fetchone() is not None
        except Exception as e:
            messagebox.showerror("Database Error", f"Error: {e}")
            return False
        finally:
            if 'conn' in locals() and conn.is_connected():
                conn.close()
    
if __name__ == "__main__":
    root = tk.Tk()
    app = LibrarySystemApp(root)
    root.mainloop()
