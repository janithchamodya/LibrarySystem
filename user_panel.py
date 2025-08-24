import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import webbrowser
from tkinter.font import Font
import time
from database import Database  
from userRole.UserProfile  import UserProfile
from userRole.Book_Recommandation import BookRecommendation
from userRole.Top10_Books  import Top10_Books
class UserPanel:
    def __init__(self, parent, go_back_callback, member_id):
        self.parent = parent
        self.go_back_callback = go_back_callback
        self.member_id = member_id
        self.db = Database()

        self.member_name = self.get_member_name()  # ✅ Must be initialized BEFORE setup_ui
        self.setup_ui()

    def get_member_name(self):
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM members WHERE member_id = %s", (self.member_id,))
            result = cursor.fetchone()
            return result[0] if result else "Reader"
        except Exception as e:
            print(f"[ERROR] Failed to fetch member name: {e}")
            return "Reader"
        finally:
            if 'conn' in locals():
                conn.close()
    
    def setup_ui(self):
        # Configure main window
        self.parent.configure(bg="#f5f7fa")
        
        # Fonts
        self.title_font = ("Segoe UI", 22, "bold")
        self.button_font = ("Segoe UI", 12)
        self.card_title_font = ("Segoe UI", 14, "bold")
        self.card_text_font = ("Segoe UI", 11)
        
        # Create main container
        self.main_frame = tk.Frame(self.parent, bg="#f5f7fa")
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Header with gradient
        self.header = tk.Canvas(self.main_frame, bg="#2ecc71", height=80, highlightthickness=0)
        self.header.pack(fill="x")
        self.create_gradient(self.header, "#2ecc71", "#27ae60", width=800, height=80)
        
        # Header content
        self.header_content = tk.Frame(self.header, bg='#2ecc71')
        self.header.create_window(0, 0, window=self.header_content, anchor="nw", width=800)
        
        # Dashboard title
        self.dashboard_title = tk.Label(self.header_content, 
                                      text="My Library Dashboard", 
                                      font=self.title_font,
                                      bg='#2ecc71', fg="white")
        self.dashboard_title.pack(side="left", padx=30, pady=20)
        
        
        # User info (right side of header)
        self.user_info_frame = tk.Frame(self.header_content, bg='#2ecc71')
        self.user_info_frame.pack(side="right", padx=30, pady=20)
        
        self.user_icon = tk.Label(self.user_info_frame, text="👤", 
                                 font=("Segoe UI", 14), bg='#2ecc71', fg="white")
        self.user_icon.pack(side="left", padx=(0, 10))
        
        self.user_name = tk.Label(self.user_info_frame, 
                          text=f"Welcome, {self.member_name}", 
                          font=("Segoe UI", 12), 
                          bg='#2ecc71', fg="white")

        
        self.user_name.pack(side="left")
        
        
        
        # Main content area
        self.content_frame = tk.Frame(self.main_frame, bg="#f5f7fa")
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
    

        # Display dashboard
        self.display_user_dashboard()
        
        # # Add footer
        # self.create_footer()

    def create_gradient(self, canvas, color1, color2, width=800, height=80):
        """Create a gradient background"""
        for i in range(height):
            r = int((int(color1[1:3], 16) * (height - i) + int(color2[1:3], 16) * i) / height)
            g = int((int(color1[3:5], 16) * (height - i) + int(color2[3:5], 16) * i) / height)
            b = int((int(color1[5:7], 16) * (height - i) + int(color2[5:7], 16) * i) / height)
            color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            canvas.create_line(0, i, width, i, fill=color)

    def display_user_dashboard(self):
        # Clear existing widgets
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        back_btn = tk.Button(self.content_frame, text="⬅ Back", font=("Arial", 12, "bold"),
                             bg="#033974", fg="white", bd=0, padx=20, pady=10,
                             activebackground="#1e8449", activeforeground="white",
                             cursor="hand2", command=self.go_back_callback)
        back_btn.pack(side="bottom", padx=0, pady=0)

        # Create cards container
        cards_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        cards_container.pack(fill="both", expand=True)
        # Card 1: Profile
        self.create_card(
            parent=cards_container,
            title="My Profile",
            description="User Profile",
            icon="🪪",
            color="#2ecc71",
            command=self.view_profile
        )
       
        self.create_card(
            parent=cards_container,
            title="Book Recommendation",
            description="predict the books for users",
            icon="📕",
            color="#2ecc71",
            command=self.view_book_recommandation 
            )
        
      
        self.create_card(
            parent=cards_container,
            title="Top 10 Books",
            description="predict the top 10 books for users",
            icon="📚",
            color="#2ecc71",
            command=self.view_top10_books 
        )
        
       

    def create_card(self, parent, title, description, icon, color, command):
        """Create a modern card component"""
        card = tk.Frame(parent, 
                       bg="white", 
                       bd=0, 
                       highlightthickness=0,
                       relief="ridge",
                       padx=0, pady=0)
        card.pack(fill="x", pady=10, ipady=0)
        
       
        
        # Card content
        content_frame = tk.Frame(card, bg="white", padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Icon
        icon_label = tk.Label(content_frame, 
                            text=icon, 
                            font=("Segoe UI", 24), 
                            bg="white", 
                            fg=color)
        icon_label.pack(side="left", padx=(0, 20))
        
        # Text content
        text_frame = tk.Frame(content_frame, bg="white")
        text_frame.pack(side="left", fill="both", expand=True)
        
        tk.Label(text_frame, 
                text=title, 
                font=self.card_title_font, 
                bg="white", 
                fg="#2c3e50", 
                anchor="w").pack(fill="x")
        
        tk.Label(text_frame, 
                text=description, 
                font=self.card_text_font, 
                bg="white", 
                fg="#7f8c8d", 
                anchor="w").pack(fill="x", pady=(5, 0))
        
        # Action button
        action_btn = tk.Button(content_frame, 
                              text="View →", 
                              font=("Segoe UI", 11, "bold"), 
                              bg=color, 
                              fg="white", 
                              bd=0, 
                              padx=20, 
                              pady=5,
                              activebackground=color,
                              activeforeground="white",
                              cursor="hand2",
                              command=command)
        action_btn.pack(side="right")
        
        # Add subtle shadow effect
        self.create_shadow(card)

    def create_shadow(self, widget):
        """Create a subtle shadow effect for cards"""
        shadow = tk.Frame(widget.master, bg="#d6dbdf", height=2)
        shadow.pack(fill="x", padx=5)
        shadow.lower(widget)

    def on_enter(self, e, widget, color):
        """Card hover effect"""
        widget.config(bg=self.lighten_color(color, 0.9))
        for child in widget.winfo_children():
            if isinstance(child, tk.Frame):
                child.config(bg=self.lighten_color(color, 0.9))
                for subchild in child.winfo_children():
                    if subchild.cget("bg") == "white":
                        subchild.config(bg=self.lighten_color(color, 0.9))

    def on_leave(self, e, widget):
        """Card leave effect"""
        widget.config(bg="white")
        for child in widget.winfo_children():
            if isinstance(child, tk.Frame):
                child.config(bg="white")
                for subchild in child.winfo_children():
                    if subchild.cget("bg") != "white":
                        subchild.config(bg="white")

    def lighten_color(self, hex_color, factor=0.1):
        """Lighten a hex color by a given factor"""
        rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        lightened = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return f'#{lightened[0]:02x}{lightened[1]:02x}{lightened[2]:02x}'

    def view_profile(self):
        profile_ui = UserProfile(
        parent=self.parent,
        content_frame=self.content_frame,
        title_font=self.title_font,
        label_font=self.card_text_font,
        button_font=self.button_font,
        go_back_callback=self.display_user_dashboard
    )   
        member_id = getattr(self, "member_id", None)
        if not member_id:
            messagebox.showerror("Error", "Member ID is missing. Please log in again.")
            return
        profile_ui.show_profile(self.member_id)
        
    def view_book_recommandation(self):
        user_book_recommand = BookRecommendation(
        parent=self.parent,
        content_frame=self.content_frame,
        title_font=self.title_font,
        label_font=self.card_text_font,
        button_font=self.button_font,
       
        go_back_callback=self.display_user_dashboard 
    )
        member_id = getattr(self, "member_id", None)
        if not member_id:
            messagebox.showerror("Error", "Member ID is missing. Please log in again.")
            return
   
        user_book_recommand.book_predictions(self.member_id)   
        
        
 
    def view_top10_books(self):
        top10_books_for_users = Top10_Books(
        parent=self.parent,
        content_frame=self.content_frame,
        title_font=self.title_font,
        label_font=self.card_text_font,
        button_font=self.button_font,
        go_back_callback=self.display_user_dashboard  # <-- corrected name
    )
        member_id = getattr(self, "member_id", None)
        if not member_id:
            messagebox.showerror("Error", "Member ID is missing. Please log in again.")
            return
        top10_books_for_users.show_top10(self.member_id)     
    
    def show_feature_dialog(self, title, message):
        """Show a more professional feature dialog"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.configure(bg="white")
        
        # Center the dialog
        self.center_window(dialog)
        
        # Add icon
        icon_label = tk.Label(dialog, 
                            text="ℹ️", 
                            font=("Segoe UI", 24), 
                            bg="white", 
                            fg="#3498db")
        icon_label.pack(pady=(20, 10))
        
        # Add title
        title_label = tk.Label(dialog, 
                             text=title, 
                             font=("Segoe UI", 16, "bold"), 
                             bg="white", 
                             fg="#2c3e50")
        title_label.pack()
        
        # Add message
        message_label = tk.Label(dialog, 
                               text=message + "\n\nThis feature is coming soon!", 
                               font=("Segoe UI", 11), 
                               bg="white", 
                               fg="#7f8c8d",
                               wraplength=350)
        message_label.pack(pady=10)
        
        # Add OK button
        ok_btn = tk.Button(dialog, 
                          text="OK", 
                          font=("Segoe UI", 11), 
                          bg="#3498db", 
                          fg="white", 
                          bd=0, 
                          padx=20,
                          command=dialog.destroy)
        ok_btn.pack(pady=10)

    def center_window(self, window):
        """Center a window on screen"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')