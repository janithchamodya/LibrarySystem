# top10books.py
import os
import tempfile
from io import BytesIO

from tkinter import simpledialog
import pandas as pd
import numpy as np
import requests
from PIL import Image, ImageTk

import tkinter as tk
from tkinter import ttk, messagebox
from database import Database

class Top10_Books:
 
    def __init__(self, parent, content_frame, title_font, label_font, button_font, go_back_callback):
        self.parent = parent
        self.content_frame = content_frame
        self.title_font = title_font
        self.label_font = label_font
        self.button_font = button_font
        self.db = Database()
        self.go_back_callback = go_back_callback

        # Keep PhotoImage references alive
        self._thumb_refs = {}

        # ---- Resolve folders robustly ----
        self.base_dir = os.path.dirname(os.path.abspath(__file__))      # ...\LibrarySystem\userRole
        parent_dir    = os.path.dirname(self.base_dir)                   # ...\LibrarySystem
        cwd_dir       = os.getcwd()

        # Model folder detection
        model_candidates = [
            os.path.join(self.base_dir, "model"),
            os.path.join(parent_dir, "model"),
            os.path.join(cwd_dir,   "model"),
        ]
        self.model_dir = next((p for p in model_candidates if os.path.isdir(p)), None)
        if not self.model_dir:
            self.model_dir = os.path.join(parent_dir, "model")  # best guess

        # Optional database folder (for Books.csv fallback)
        db_candidates = [
            os.path.join(parent_dir, "database"),
            os.path.join(self.base_dir, "database"),
            os.path.join(cwd_dir, "database"),
        ]
        self.database_dir = next((p for p in db_candidates if os.path.isdir(p)), None)

        # Files map
        self.files = {
            "popular": os.path.join(self.model_dir, "popular.parquet"),
            "books":   os.path.join(self.model_dir, "books.parquet"),   # optional
        }

        # Image cache
        self._cache_dir = os.path.join(tempfile.gettempdir(), "book_top10_cache_tk")
        os.makedirs(self._cache_dir, exist_ok=True)

        # Data placeholders
        self.POPULAR = None    # DataFrame
        self.BOOKS   = None    # DataFrame (optional)
        self.TOP10   = None    # DataFrame of 10 rows with needed columns

        # UI containers
        self.canvas = None
        self.cards_frame = None
        self.cards_frame_id = None
        self.scroll = None
        self.info_label = None

    # ---------- Public entry ----------
    def show_top10(self,member_id):
        self.current_user_id = str(member_id) if member_id is not None else None
        # Clear and prep parent content frame
        for w in self.content_frame.winfo_children():
            w.destroy()
        self.content_frame.pack_forget()
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=30)

        # Outer frame
        outer = tk.Frame(self.content_frame, bg="#e6f2ff", bd=2, relief="groove")
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer, text="🏆 Top 10 Books", font=self.title_font,
            bg="#e6f2ff", fg="#033974"
        ).pack(pady=(20, 10))

        # Load artifacts
        try:
            self._load_artifacts()
        except Exception as e:
            messagebox.showerror("Data Load Error", f"Failed to load Top 10 data:\n{e}")
            return

        # Info label (optional status)
        self.info_label = tk.Label(outer, text="", font=self.label_font, bg="#e6f2ff", fg="#2c3e50")
        self.info_label.pack(anchor="w", padx=10)

        # Scrollable area for cards
        wrap = tk.Frame(outer, bg="#e6f2ff")
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(wrap, bg="#e6f2ff", highlightthickness=0)
        self.scroll = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.cards_frame = tk.Frame(self.canvas, bg="#e6f2ff")

        self.cards_frame_id = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        # 4 equal-width columns
        for col in range(4):
            self.cards_frame.grid_columnconfigure(col, weight=1, uniform="cards")

        self.cards_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Render the top 10 as cards
        recs = self._top10_records()
        self._show_cards(recs)

        # Back button
        bottom = tk.Frame(outer, bg="#e6f2ff")
        bottom.pack(fill="x", pady=(0, 20))
        tk.Button(
            bottom, text="⬅ Back",
            command=self.go_back_callback,
            font=self.button_font,
            bg="#033974", fg="white", bd=0, padx=20, pady=8,
            activebackground="#7f8c8d", activeforeground="white", cursor="hand2"
        ).pack(side="right")

    # ---------- Data loading ----------
    def _load_artifacts(self):
        # Check popular
        if not os.path.exists(self.files["popular"]):
            raise FileNotFoundError(f"Missing file: {self.files['popular']}")

        # Read parquet (requires pyarrow installed)
        try:
            self.POPULAR = pd.read_parquet(self.files["popular"])
        except ImportError as e:
            raise ImportError("Parquet engine missing. Install with:\n  pip install pyarrow") from e
        except Exception as e:
            raise RuntimeError(f"Error reading popular.parquet: {e}") from e

        # If available, load books.parquet for image backfill
        if os.path.exists(self.files["books"]):
            try:
                self.BOOKS = pd.read_parquet(self.files["books"])
            except Exception:
                self.BOOKS = None
        else:
            self.BOOKS = None

        # Try Books.csv to backfill covers (optional)
        if self.BOOKS is None and self.database_dir:
            csv_path = os.path.join(self.database_dir, "Books.csv")
            if os.path.exists(csv_path):
                try:
                    df_csv = pd.read_csv(csv_path)
                    # Keep relevant columns only
                    keep = [c for c in ["Book-Title", "Book-Author", "Image-URL-M", "ISBN"] if c in df_csv.columns]
                    if keep:
                        self.BOOKS = df_csv[keep].drop_duplicates("Book-Title")
                except Exception:
                    self.BOOKS = None

        # Build TOP10 with the needed columns
        needed_cols = ["Book-Title", "Book-Author", "num_ratings", "avg_rating"]
        for c in needed_cols:
            if c not in self.POPULAR.columns:
                raise ValueError(f"'popular.parquet' must include column: {c}")

        top = self.POPULAR.head(10).copy()

        # Make sure there's an Image-URL-M
        if "Image-URL-M" not in top.columns or top["Image-URL-M"].isna().all():
            # Try to merge/bring images from BOOKS if available
            if self.BOOKS is not None and "Image-URL-M" in self.BOOKS.columns:
                top = (
                    top.merge(
                        self.BOOKS[["Book-Title", "Image-URL-M"]],
                        on="Book-Title",
                        how="left",
                        suffixes=("", "_src")
                    )
                )
                if "Image-URL-M_src" in top.columns:
                    # prefer the merged one if present
                    if "Image-URL-M" in top.columns:
                        top["Image-URL-M"] = top["Image-URL-M_src"].fillna(top["Image-URL-M"])
                    else:
                        top["Image-URL-M"] = top["Image-URL-M_src"]
                    top.drop(columns=[c for c in top.columns if c.endswith("_src")], inplace=True)
            else:
                # Create a blank image column so UI doesn't break
                top["Image-URL-M"] = np.nan

        self.TOP10 = top

    # ---------- Build card data ----------
    def _top10_records(self):
        recs = []
        for _, r in self.TOP10.iterrows():
            recs.append({
                "title":  str(r.get("Book-Title", "")),
                "author": str(r.get("Book-Author", "")),
                "image":  str(r.get("Image-URL-M", "")) if not pd.isna(r.get("Image-URL-M", np.nan)) else "",
                "votes":  str(r.get("num_ratings", "")),
                "rating": str(r.get("avg_rating", "")),
            })
        return recs

    
    
    def _show_cards(self, recs):
        # Clear old
        for w in self.cards_frame.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

        if not recs:
            tk.Label(
                self.cards_frame, text="No books to show.",
                bg="#e6f2ff", font=self.label_font, fg="#2c3e50"
            ).grid(row=0, column=0, padx=8, pady=8, sticky="w")
            return

        COLS   = 4
        CARD_W = 240
        CARD_H = 360

        for i, rec in enumerate(recs):
            r = i // COLS
            c = i % COLS

            # Card (fixed size)
            card = tk.Frame(self.cards_frame, bg="#ffffff", bd=1, relief="solid",
                            width=CARD_W, height=CARD_H, cursor="hand2")
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)

            inner = tk.Frame(card, bg="#ffffff")
            inner.pack(fill="both", expand=True, padx=10, pady=10)

            # Image
            img = self._fetch_image(rec.get("image"), size=(140, 180))
            tk_img = ImageTk.PhotoImage(img)
            self._thumb_refs[str(i)] = tk_img

            img_lbl = tk.Label(inner, image=tk_img, bg="#ffffff")
            img_lbl.image = tk_img
            img_lbl.pack(pady=(2, 6))

            # Title / Author / Stats — keep references to the widgets
            title_lbl = tk.Label(
                inner, text=rec.get("title", ""), bg="#ffffff",
                font=("Segoe UI", 10, "bold"), wraplength=CARD_W - 20, justify="left"
            )
            title_lbl.pack(anchor="w")

            author_lbl = tk.Label(
                inner, text=rec.get("author", ""), bg="#ffffff",
                font=("Segoe UI", 9), fg="#555", wraplength=CARD_W - 20, justify="left"
            )
            author_lbl.pack(anchor="w", pady=(2, 6))

            stats = f"Votes: {rec.get('votes','-')}   Rating: {rec.get('rating','-')}"
            stats_lbl = tk.Label(inner, text=stats, bg="#ffffff",
                                font=("Segoe UI", 9), fg="#333")
            stats_lbl.pack(anchor="w")

            # Hover + click
            def on_enter(_e, w=card): w.configure(bg="#f5f7ff")
            def on_leave(_e, w=card): w.configure(bg="#ffffff")
            def on_click(_e, r=rec): self._on_card_click(r)

            for w in (card, inner, img_lbl, title_lbl, author_lbl, stats_lbl):
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                w.bind("<Button-1>", on_click)

    # ---------- Canvas helpers ----------
    def _on_canvas_configure(self, event):
        # Make inner frame the same width so cards stretch nicely
        self.canvas.itemconfig(self.cards_frame_id, width=event.width)


    def _placeholder(self, size):
        # light gray fallback
        from PIL import Image
        return Image.new("RGB", size, color=(240, 240, 240))


    def _fetch_image(self, url: str, size=(140, 180)):
        from PIL import Image
        import os
        from io import BytesIO
        import requests

        # 1) Validate URL value
        if not url or not isinstance(url, str):
            return self._placeholder(size)
        url = url.strip()
        if not url or url.lower() in {"nan", "none", "null"}:
            return self._placeholder(size)

        # 2) If it's a local path (absolute)
        if os.path.isabs(url) and os.path.exists(url):
            try:
                return Image.open(url).convert("RGB").resize(size, Image.LANCZOS)
            except Exception:
                return self._placeholder(size)

        # 3) If it's a relative path, try relative to a few roots
        rel_candidates = [
            os.path.join(self.base_dir, url),
            os.path.join(os.path.dirname(self.base_dir), url),   # project root
            os.path.join(os.getcwd(), url),
        ]
        for p in rel_candidates:
            if os.path.exists(p):
                try:
                    return Image.open(p).convert("RGB").resize(size, Image.LANCZOS)
                except Exception:
                    break  # fall through to HTTP attempt

        # 4) Otherwise assume it's HTTP(S)
        #    – Some old datasets have http://…; switch to https where possible
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]

        # Use a browser-like UA; Amazon often 403s default Python UA
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        if "amazon" in url:
            headers["Referer"] = "https://www.amazon.com/"

        # Simple disk cache
        safe = "".join(ch if ch.isalnum() else "_" for ch in url)[:200]
        cache_path = os.path.join(self._cache_dir, safe)

        try:
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    data = f.read()
            else:
                r = requests.get(url, headers=headers, timeout=10)
                r.raise_for_status()
                data = r.content
                with open(cache_path, "wb") as f:
                    f.write(data)

            img = Image.open(BytesIO(data)).convert("RGB")
            return img.resize(size, Image.LANCZOS)
        except Exception:
            return self._placeholder(size)


    def _on_card_click(self, rec: dict):
            """When a card is clicked, confirm + save to DB."""
            user_id = getattr(self, "current_user_id", None)
            if not user_id:
                # Fallback prompt—shouldn’t happen if you passed member_id
                user_id = simpledialog.askstring("User", "Enter your User ID:")
                if not user_id:
                    return

            ok = messagebox.askyesno(
                "Lend Book",
                f"Do you want to lend this book?\n\n"
                f"Title : {rec.get('title','')}\n"
                f"Author: {rec.get('author','')}"
            )
            if not ok:
                return

        
            try:
                rows = self._insert_loan_mysql(user_id, rec)
                self.parent.after(0, messagebox.showinfo, "Success",
                                f"Lending recorded. Rows affected: {rows}")
            except Exception as e:
                # This ensures the exception text is preserved when the lambda runs later
                self.parent.after(0, messagebox.showerror, "Error", f"Failed to save:\n{e}")


    def _insert_loan_mysql(self, member_id: str, rec: dict) -> int:
        
            if not member_id:
                raise ValueError("member_id is empty")
            title = (rec or {}).get("title", "").strip()
            author = (rec or {}).get("author", "").strip()
            image  = (rec or {}).get("image", "").strip()
            if not title:
                raise ValueError("book record is empty or missing title")

            conn = self.db.connect()
            try:
                conn.ping(reconnect=True)
                with conn.cursor(dictionary=True) as cur:
                
                    cur.execute(
                        """
                        SELECT book_id
                        FROM library_db.books
                        WHERE book_name = %s AND author = %s
                        """,
                        (title, author)
                    )
                    rows = cur.fetchall()

                    if not rows:
                        cur.execute(
                            """
                            SELECT book_id
                            FROM library_db.books
                            WHERE LOWER(book_name) = LOWER(%s) AND LOWER(author) = LOWER(%s)
                            """,
                            (title, author)
                        )
                        rows = cur.fetchall()

                    if not rows:
                        
                        raise ValueError(f"Book not found in 'books' table for title='{title}', author='{author}'")

                    if len(rows) > 1:
                        
                        pass

                    book_id = rows[0]["book_id"]

                
                    cur.execute(
                        """
                        INSERT INTO library_db.user_notifications
                            (user_id, book_id, book_title, book_author, image_url, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (str(member_id), book_id, title[:255], author[:255], image[:500])
                    )
                    affected = cur.rowcount

                conn.commit()
                return affected

            except Exception as e:
                print("[DB ERROR]", repr(e))
                conn.rollback()
                raise
            finally:
                conn.close()

        

        