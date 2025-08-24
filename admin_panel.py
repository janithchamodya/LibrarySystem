
import tkinter as tk
from tkinter import ttk, messagebox
from prediction_model import predict_holding_days
from adminRole.returns import Returns

from adminRole.lending import lending as Lending
from adminRole.book_management import BookManagement
from adminRole.ReturnReport  import ReturnReport 
from adminRole.MemberManagement  import MemberManagement


class AdminPanel:
    def __init__(self, parent, go_back_callback):
        """
        Initialize the Admin Panel with main window settings
        parent: The parent window/tkinter root
        go_back_callback: Function to return to main menu
        """
        self.parent = parent
        self.go_back_callback = go_back_callback
        self.parent.configure(bg="#ffffff")  # Set main background color to white

        # Font configurations for different UI elements
        self.title_font = ("Arial", 18, "bold")    # Large bold for titles
        self.button_font = ("Arial", 12, "bold")   # Medium bold for buttons
        self.label_font = ("Arial", 11)            # Regular for labels

        # Header frame (blue bar at top)
        header_frame = tk.Frame(parent, bg="#3498db", height=60)  # Blue header, 60px tall
        header_frame.pack(fill="x", pady=(0, 20))  # Fill horizontally with 20px bottom padding

        # Header label (centered in header frame)
        tk.Label(header_frame, text="Library Administration System", 
                font=self.title_font, bg="#3498db", fg="white").pack(pady=15)  # White text, 15px padding

        # Main content frame (white background)
        self.content_frame = tk.Frame(parent, bg="#ffffff")
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=10)  # 30px side padding, 10px top/bottom

        self.show_admin_main_menu()

    def clear_frame(self):
        """Clear all widgets from the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_admin_main_menu(self):
        """Display the main admin menu with navigation buttons"""
        self.clear_frame()

        # Button container frame (white background)
        button_frame = tk.Frame(self.content_frame, bg="#ffffff")
        button_frame.pack(fill="x", pady=50,padx=100)  # Fill width with 10px padding

        # List of buttons with their text and corresponding commands
        buttons = [
            ("Book Management", self.book_management),
            ("Membership Management", self.membership_management),
            ("Lending", self.lending),
            ("Returns", self.returns),
           
            ("Reporting", self.reporting),
            ("Back to Main Menu", self.go_back_callback)
        ]

        # Create each button with consistent styling
        for text, command in buttons:
            btn = tk.Button(
                button_frame, 
                text=text, 
                font=self.button_font, 
                bg="#033974",  # Dark blue background
                fg="white",    # White text
                bd=0,           # No border
                padx=15,        # 15px horizontal padding
                pady=10,        # 10px vertical padding
                activebackground="#FFFFFF",  # White when clicked
                activeforeground="white",    # White text when clicked
                cursor="hand2",  # Hand cursor on hover
                command=command,
                width=30         # Fixed width of 30 characters
            )
            btn.pack(pady=15, ipadx=5)  # 15px vertical padding, 5px internal padding

    # Simple menu functions that show info messages
    def book_management(self):
        self.clear_frame()
        BookManagement(
            parent=self.content_frame,
            go_back_callback=self.show_admin_main_menu
        )

    def membership_management(self):
        self.clear_frame()
        MemberManagement(
            parent=self.content_frame,
            go_back_callback=self.show_admin_main_menu
        )
        
    def returns(self):
        returns_ui = Returns(
        parent=self.parent,
        content_frame=self.content_frame,
        title_font=self.title_font,
        label_font=self.label_font,
        button_font=self.button_font,
        go_back_callback=self.show_admin_main_menu
    )
        returns_ui.returns()
        

    def reporting(self):
        report_ui = ReturnReport(
            parent=self.parent,
            content_frame=self.content_frame,
            title_font=self.title_font,
            label_font=self.label_font,
            button_font=self.button_font,
            go_back_callback=self.show_admin_main_menu
        )
        report_ui.show_report()

    def lending(self):
        lending_ui = Lending(
            parent=self.parent,
            content_frame=self.content_frame,
            title_font=self.title_font,
            label_font=self.label_font,
            button_font=self.button_font,
            go_back_callback=self.show_admin_main_menu   # Pass callback here
        )
        lending_ui.lending()
        
        

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminPanel(root, lambda: None)
    root.mainloop()