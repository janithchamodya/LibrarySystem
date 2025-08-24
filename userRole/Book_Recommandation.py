import os
import difflib
import threading
import tempfile
from io import BytesIO

import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageTk
import sqlite3
from tkinter import simpledialog
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from database import Database

class BookRecommendation:
    def __init__(self, parent, content_frame, title_font, label_font, button_font, go_back_callback):
        self.parent = parent
        self.content_frame = content_frame
        self.title_font = title_font
        self.label_font = label_font
        self.button_font = button_font
        self.go_back_callback = go_back_callback
        self.db = Database()
        self._thumb_refs = {}          # keep PhotoImage refs alive
        self._artifacts_loaded = False

        # --- Resolve paths robustly ---
        self.base_dir = os.path.dirname(os.path.abspath(__file__))      # ...\LibrarySystem\userRole
        parent_dir    = os.path.dirname(self.base_dir)                   # ...\LibrarySystem
        cwd_dir       = os.getcwd()

        model_candidates = [
            os.path.join(self.base_dir, "model"),
            os.path.join(parent_dir, "model"),
            os.path.join(cwd_dir,   "model"),
        ]
        self.model_dir = next((p for p in model_candidates if os.path.isdir(p)), None)
        if not self.model_dir:
            self.model_dir = os.path.join(parent_dir, "model")  # best guess

        db_candidates = [
            os.path.join(parent_dir, "database"),
            os.path.join(self.base_dir, "database"),
            os.path.join(cwd_dir, "database"),
        ]
        self.database_dir = next((p for p in db_candidates if os.path.isdir(p)), None)

        self.files = {
            "popular": os.path.join(self.model_dir, "popular.parquet"),
            "pt":      os.path.join(self.model_dir, "pt.parquet"),
            "books":   os.path.join(self.model_dir, "books.parquet"),
            "sims":    os.path.join(self.model_dir, "similarity_scores.npy"),
        }

        # Cache for cover images
        self._cache_dir = os.path.join(tempfile.gettempdir(), "book_reco_cache_tk")
        os.makedirs(self._cache_dir, exist_ok=True)

        # Placeholders set in _load_artifacts()
        self.POPULAR = None
        self.PT = None
        self.BOOKS = None
        self.SIMS = None
        self.TITLES = None
        self.TITLES_LOWER = None

    
    def book_predictions(self,member_id):
       
        self.current_user_id = str(member_id) if member_id is not None else None
        # Clear and prepare root content frame
        for w in self.content_frame.winfo_children():
            w.destroy()
        self.content_frame.pack_forget()
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=30)

        # Outer frame
        outer = tk.Frame(self.content_frame, bg="#e6f2ff", bd=2, relief="groove")
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer, text="📚 Book Recommendation", font=self.title_font,
            bg="#e6f2ff", fg="#033974"
        ).pack(pady=(20, 10))

        # Try load artifacts once
        if not self._artifacts_loaded:
            try:
                self._load_artifacts()
            except Exception as e:
                messagebox.showerror("Data Load Error", f"Failed to load artifacts:\n{e}")
                return

        # Main container: only recommender UI (no Top-50, no prediction)
        main = tk.Frame(outer, bg="#e6f2ff")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_recommend_ui(main)

        # Back button row
        bottom = tk.Frame(outer, bg="#e6f2ff")
        bottom.pack(fill="x", pady=(10, 20))
        tk.Button(
            bottom, text="⬅ Back",
            command=self.go_back_callback,
            font=self.button_font,
            bg="#033974", fg="white", bd=0, padx=20, pady=8,
            activebackground="#7f8c8d", activeforeground="white", cursor="hand2"
        ).pack(side="right")

    # ---------- Data loading ----------
    def _load_artifacts(self):
        # Ensure files exist
        missing = [k for k in ("popular", "pt", "books", "sims") if not os.path.exists(self.files[k])]
        if missing:
            lines = [f"- {k}: {self.files[k]}" for k in missing]
            raise FileNotFoundError("Missing data file(s):\n" + "\n".join(lines))

        # Parquet/NumPy
        try:
            self.POPULAR = pd.read_parquet(self.files["popular"])
            self.PT      = pd.read_parquet(self.files["pt"])
            self.BOOKS   = pd.read_parquet(self.files["books"])
            self.SIMS    = np.load(self.files["sims"])
        except ImportError as e:
            raise ImportError("Parquet engine missing. Install with:  pip install pyarrow") from e
        except Exception as e:
            raise RuntimeError(f"Error reading artifacts: {e}") from e

        # Optional: override/fill cover images from Books.csv
        try:
            if self.database_dir:
                csv_books = os.path.join(self.database_dir, "Books.csv")
                if os.path.exists(csv_books):
                    df_csv = pd.read_csv(csv_books)
                    # prefer medium, else large, else small
                    for col in ["Image-URL-M", "Image-URL-L", "Image-URL-S"]:
                        if col not in df_csv.columns:
                            df_csv[col] = ""
                    df_csv = df_csv[["Book-Title", "Image-URL-M", "Image-URL-L", "Image-URL-S"]].drop_duplicates("Book-Title")
                    self.BOOKS = (
                        self.BOOKS.drop_duplicates("Book-Title")
                        .merge(df_csv, on="Book-Title", how="left", suffixes=("", "_csv"))
                    )
                    # Choose best available url into a single column
                    def pick_url(row):
                        for col in ["Image-URL-M_csv", "Image-URL-M", "Image-URL-L_csv", "Image-URL-L", "Image-URL-S_csv", "Image-URL-S"]:
                            v = str(row.get(col, "") or "").strip()
                            if v:
                                return v
                        return ""
                    self.BOOKS["Image-URL-M"] = self.BOOKS.apply(pick_url, axis=1)
                    # Drop helper columns
                    dropcols = [c for c in self.BOOKS.columns if c.endswith("_csv")]
                    if dropcols:
                        self.BOOKS.drop(columns=dropcols, inplace=True)
        except Exception as e:
            print(f"⚠️ CSV image merge skipped: {e}")

        # Index helpers
        self.TITLES = pd.Index(self.PT.index)
        self.TITLES_LOWER = pd.Index([str(t).lower() for t in self.TITLES])

        self._artifacts_loaded = True

    # ---------- Recommend UI ----------
    def _build_recommend_ui(self, master):
        # Input row
        row = tk.Frame(master, bg="#e6f2ff")
        row.pack(fill="x", pady=(0, 5))
        tk.Label(row, text="Enter a book title:", font=self.label_font, bg="#e6f2ff").pack(side="left")
        self.entry = tk.Entry(row, width=80,
                                bg="#ecf0f1",        # Light gray background
                                fg="#2c3e50",        # Dark gray text
                                relief="flat",       # No border
                                highlightthickness=1, # 1px border when focused
                                highlightbackground="#bdc3c7",  # Light gray border
                                highlightcolor="#3498db",                                              
                                font=("Segoe UI", 12))
        self.entry.pack(side="left", padx=20 ,pady=20,ipady=5)
        tk.Button(row, text="Recommend", font=self.button_font, bg="#033974", fg="white", padx=20,pady=10,
                command=self._on_recommend_click).pack(side="left")

        # Info label
        self.info_label = tk.Label(master, text="", font=self.label_font, bg="#e6f2ff", fg="#2c3e50")
        self.info_label.pack(anchor="w", pady=(0, 10))

        # Scrollable area for recommendation “cards”
        wrap = tk.Frame(master, bg="#e6f2ff")
        wrap.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(wrap, bg="#e6f2ff", highlightthickness=0)
        self.scroll = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.cards_frame = tk.Frame(self.canvas, bg="#e6f2ff")

        self.cards_frame_id = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")

        # 4 equal columns for the card grid
        for col in range(4):
            self.cards_frame.grid_columnconfigure(col, weight=1, uniform="cols")

        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        # Keep scrollregion updated
        self.cards_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        # Make inner frame width match the visible canvas width
        self.canvas.itemconfig(self.cards_frame_id, width=event.width)

    def _on_recommend_click(self):
        title = (self.entry.get() or "").strip()
        if not title:
            messagebox.showinfo("Info", "Please type a book title.")
            return

        idx, matched = self._find_title_index(title)
        if idx is None:
            self.info_label.config(text=f"No match for “{title}”. Try another title.")
            self._clear_cards()
            return

        if matched and matched.lower() != title.lower():
            self.info_label.config(text=f"Showing recommendations for: {matched}")
        else:
            self.info_label.config(text="")

        def worker():
            recs = self._get_similar(idx, top_k=12)  # get more; grid will wrap 4/row
            self.parent.after(0, lambda: self._show_cards(recs))

        threading.Thread(target=worker, daemon=True).start()

    def _clear_cards(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

    def _show_cards(self, recs):
        self._clear_cards()
        if not recs:
            tk.Label(
                self.cards_frame, text="No similar books found.",
                bg="#e6f2ff", font=self.label_font, fg="#2c3e50"
            ).grid(row=0, column=0, padx=8, pady=8, sticky="w")
            return

        COLS   = 4
        CARD_W = 220
        CARD_H = 320

        for i, rec in enumerate(recs):
            r = i // COLS
            c = i % COLS

            card = tk.Frame(self.cards_frame, bg="#ffffff", bd=1, relief="solid",
                            width=CARD_W, height=CARD_H, cursor="hand2")
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)

            inner = tk.Frame(card, bg="#ffffff")
            inner.pack(fill="both", expand=True, padx=8, pady=8)

            img = self._fetch_image(rec.get("image"), size=(140, 180))
            tk_img = ImageTk.PhotoImage(img)
            self._thumb_refs[str(i)] = tk_img
            img_lbl = tk.Label(inner, image=tk_img, bg="#ffffff")
            img_lbl.image = tk_img
            img_lbl.pack(pady=(4, 6))

            title_lbl = tk.Label(
                inner, text=rec.get("title", ""), bg="#ffffff",
                font=("Segoe UI", 10, "bold"), wraplength=CARD_W - 20, justify="left"
            )
            title_lbl.pack(anchor="w")

            author_lbl = tk.Label(
                inner, text=rec.get("author", ""), bg="#ffffff",
                font=("Segoe UI", 9), fg="#555", wraplength=CARD_W - 20, justify="left"
            )
            author_lbl.pack(anchor="w", pady=(2, 0))

            # hover effect (optional)
            def on_enter(e, w=card): w.configure(bg="#f5f7ff")
            def on_leave(e, w=card): w.configure(bg="#ffffff")
            for w in (card, inner, img_lbl, title_lbl, author_lbl):
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                w.bind("<Button-1>", lambda _e, rec=rec: self._on_card_click(rec))

    # ---------- Helpers ----------
    def _fetch_image(self, url: str, size=(140, 180)) -> Image.Image:
        """Download image with browser-like headers; cache to temp; graceful fallback."""
        if not url or not isinstance(url, str) or not url.strip():
            return Image.new("RGB", size, color=(230, 230, 230))

        safe = "".join(ch if ch.isalnum() else "_" for ch in url)[:200]
        path = os.path.join(self._cache_dir, safe)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = f.read()
            else:
                # First try with plain headers
                r = requests.get(url, timeout=8, headers=headers, allow_redirects=True)
                if r.status_code == 403 and "amazon" in url.lower():
                    # Some CDNs (e.g., old Amazon image links) block default requests
                    headers2 = dict(headers)
                    headers2["Referer"] = "https://www.amazon.com/"
                    r = requests.get(url, timeout=8, headers=headers2, allow_redirects=True)
                r.raise_for_status()
                data = r.content
                with open(path, "wb") as f:
                    f.write(data)

            img = Image.open(BytesIO(data)).convert("RGB")
            return img.resize(size, Image.LANCZOS)
        except Exception:
            return Image.new("RGB", size, color=(230, 230, 230))

    def _find_title_index(self, user_input: str):
        if not user_input:
            return None, None
        u = user_input.strip().lower()

        # exact (case-insensitive)
        try:
            pos = self.TITLES_LOWER.get_loc(u)
            idx = pos if isinstance(pos, int) else pos[0]
            return idx, self.TITLES[idx]
        except KeyError:
            pass

        # substring
        mask = self.TITLES_LOWER.str.contains(u, na=False)
        candidates = self.TITLES[mask]
        if len(candidates) > 0:
            return self.TITLES.get_loc(candidates[0]), candidates[0]

        # fuzzy
        match = difflib.get_close_matches(user_input, self.TITLES.tolist(), n=1, cutoff=0.6)
        if match:
            return self.TITLES.get_loc(match[0]), match[0]
        return None, None

    def _get_similar(self, idx: int, top_k=4):
        sims = list(enumerate(self.SIMS[idx]))
        sims_sorted = sorted(sims, key=lambda x: x[1], reverse=True)[1:1 + top_k]
        recs = []
        for i, _score in sims_sorted:
            title = self.TITLES[i]
            temp = self.BOOKS[self.BOOKS['Book-Title'] == title].drop_duplicates('Book-Title')
            if temp.empty:
                continue
            row = temp.iloc[0]
            # prefer M, else L, else S
            img_url = ""
            for col in ["Image-URL-M", "Image-URL-L", "Image-URL-S"]:
                v = str(row.get(col, "") or "").strip()
                if v:
                    img_url = v
                    break
            recs.append({
                "title":  str(row.get('Book-Title', "")),
                "author": str(row.get('Book-Author', "")),
                "image":  img_url,
            })
        return recs


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

    