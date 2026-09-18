import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from excel_manager import ExcelManager, clean_val
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import gc
import weakref

try:
    from services import order_card_service as card_svc
    from views.order_card_view import OrderCardView
    from lang import LANGUAGE_OPTIONS, ORDER_CARD_TRANSLATIONS, TRANSLATIONS
    from utils.finance_db import FinanceDB
    from utils.app_state import AppStateCache
except ImportError:
    from app.services import order_card_service as card_svc
    from app.views.order_card_view import OrderCardView
    from app.lang import LANGUAGE_OPTIONS, ORDER_CARD_TRANSLATIONS, TRANSLATIONS
    from app.utils.finance_db import FinanceDB
    from app.utils.app_state import AppStateCache

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A5
    REPORTLAB_INSTALLED = True
except ImportError:
    REPORTLAB_INSTALLED = False

# --- Theme Configuration ---
# Soft-glass palette: frosted-tint surfaces + low-contrast borders + a thin
# light-catching "glass_highlight" strip along each card's top edge (see
# AtelierERPApp._glass_card). Tkinter has no real background blur/alpha, so
# this is an approximated glass look via color choices only — text_main /
# text_muted stay unchanged everywhere so legibility is never traded away.
# (Reverted 2026-09-18: a monochrome black/white retune was tried per a
# reference design the user shared, but the user clarified they meant to
# reference that design's column/block LAYOUT, not its colors — the
# original soft-glass coloring was good and is restored here.)
THEMES = {
    "light": {
        "bg_body": "#EEF2FA", "bg_header": "#FBFCFF", "bg_sidebar": "#FBFCFF",
        "bg_card": "#FAFBFF", "border": "#DDE4F2", "text_main": "#1D1D1F",
        "text_muted": "#86868B", "bg_chart": "#F5F8FF", "glass_highlight": "#FFFFFF"
    },
    "dark": {
        "bg_body": "#14151F", "bg_header": "#1C1E2A", "bg_sidebar": "#1C1E2A",
        "bg_card": "#20222E", "border": "#33364A", "text_main": "#F5F5F7",
        "text_muted": "#A1A1A6", "bg_chart": "#262838", "glass_highlight": "#4A4D66"
    }
}

PRIMARY = "#007AFF"
SUCCESS = "#34C759"
WARNING = "#FF9500"
DANGER = "#FF3B30"
FONT_FAMILY = "SF Pro Text" if sys.platform == "darwin" else "Segoe UI"

# Brand accent trio (blue / white / red) — a thin tri-color strip drawn
# along the very top of the window (see _create_accent_strip) as a small
# signature touch on top of the soft-glass palette. Hardcoded independently
# of PRIMARY/DANGER (even though they currently match) so this strip stays
# literally blue/white/red no matter how those two get retuned later.
ACCENT_BLUE = "#007AFF"
ACCENT_WHITE = "#FFFFFF"
ACCENT_RED = "#FF3B30"


class CircularDonutChart(tk.Canvas):
    __slots__ = ('size', 'ring_color', 'bg_color', 'stroke_width', 'percentage')
    
    def __init__(self, parent, size=75, ring_color=PRIMARY, bg_color="#E5E5EA", stroke_width=8, theme_colors=None, **kwargs):
        bg = theme_colors["bg_chart"] if theme_colors else "#FAFAFC"
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, **kwargs)
        self.size = size
        self.ring_color = ring_color
        self.bg_color = bg_color
        self.stroke_width = stroke_width
        self.percentage = 0
        self.draw_chart()

    def draw_chart(self):
        self.delete("all")
        margin = self.stroke_width / 2 + 2
        x0, y0 = margin, margin
        x1, y1 = self.size - margin, self.size - margin

        self.create_oval(x0, y0, x1, y1, outline=self.bg_color, width=self.stroke_width)

        if self.percentage >= 100:
            self.create_oval(x0, y0, x1, y1, outline=self.ring_color, width=self.stroke_width)
        elif self.percentage > 0:
            extent = -(self.percentage / 100.0) * 360
            self.create_arc(x0, y0, x1, y1, start=90, extent=extent, style=tk.ARC, outline=self.ring_color, width=self.stroke_width)

    def set_percentage(self, pct):
        self.percentage = max(0, min(100, pct))
        self.draw_chart()


class AtelierERPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jhagra Textile & Clothing — Atelier Ledger")
        self.minsize(1100, 700)

        if os.path.exists("icon.ico"):
            self.iconbitmap("icon.ico")

        self.excel_mgr = ExcelManager()
        # Finance ledger (SQLite): mirrors paid/remaining/debt per order,
        # recomputed from orders.xlsx on every reload_all_data(). Lazily
        # (re)created against whichever data dir self.excel_mgr currently
        # points to — see _finance_db_for_current_data().
        self.finance_db = None
        self._finance_db_dir = None

        # Settings/session cache (theme, language, last open section, window
        # geometry) so closing and reopening the app picks up where the user
        # left off, instead of always resetting to English/Light/Dashboard.
        # Lazily (re)bound to self.excel_mgr's current data dir — same
        # pattern as _finance_db_for_current_data() — so tests that swap
        # excel_mgr to a throwaway temp dir never touch the real app/data
        # cache file.
        self.app_state = None
        self._app_state_dir = None
        saved_state = self._app_state_for_current_data().load()
        self.current_theme = saved_state["theme"] if saved_state["theme"] in THEMES else "light"
        valid_langs = [code for code, _ in LANGUAGE_OPTIONS]
        self.current_lang = saved_state["lang"] if saved_state["lang"] in valid_langs else "en"
        self.current_section = saved_state["last_section"]
        try:
            self.geometry(saved_state["geometry"])
        except tk.TclError:
            self.geometry("1350x850")

        # Destructive operations are available only after an administrator login.
        self.current_user_role = "Viewer"
        self.colors = THEMES[self.current_theme]

        # --- HEADERS MATCHING PHYSICAL FORM ---
        # Legacy columns first; order-card columns appended LAST so existing
        # .xlsx rows keep positional compatibility (no data shifting on read).
        self.cust_headers = card_svc.CUST_HEADERS
        self.emp_headers = ["id", "name", "phone", "role", "status", "current_task"]
        self.ord_headers = card_svc.ORD_HEADERS  # expected order columns (includes 'customer_id')

        self.default_garments = ["Shalwar Kameez", "Waistcoat", "2-Piece Suit"]
        self.default_roles = ["Master Cutter", "Stitching Specialist"]

        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
        self.withdraw()
        self.show_login_screen()

    def on_app_close(self):
        """Saves the session cache one last time (in case the 5s
        auto-refresh loop hasn't caught the latest tweak yet) before the
        window actually closes."""
        try:
            self._app_state_for_current_data().save(
                theme=self.current_theme, lang=self.current_lang,
                last_section=getattr(self, "current_section", "dashboard"),
                geometry=self.geometry(),
            )
        except Exception:
            pass
        self.destroy()

    # ==========================================
    # ID HELPERS
    # ==========================================
    def _next_id(self, prefix, records, start=101):
        """Generate the next sequential ID for a record set (e.g. C-102)."""
        nums = []
        for r in records:
            rid = clean_val(r.get("id"))
            if rid.startswith(prefix + "-"):
                try:
                    nums.append(int(rid.split("-", 1)[1]))
                except (ValueError, IndexError):
                    pass
        return f"{prefix}-{max(nums) + 1 if nums else start}"

    # ==========================================
    # AUTHENTICATION
    # ==========================================
    def show_login_screen(self):
        self.login_dlg = tk.Toplevel(self)
        self.login_dlg.title("System Authentication")
        self.login_dlg.geometry("400x250")
        self.login_dlg.configure(bg=self.colors["bg_card"])
        self.login_dlg.protocol("WM_DELETE_WINDOW", self.destroy)
        self.login_dlg.resizable(False, False)

        tk.Label(self.login_dlg, text="🔒 JTC Secure Login", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=(30, 10))
        tk.Label(self.login_dlg, text="Please enter your administrator password:", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack()

        self.ent_pwd = tk.Entry(self.login_dlg, show="*", font=(FONT_FAMILY, 12), justify="center",
                                bg=self.colors["bg_body"], fg=self.colors["text_main"],
                                insertbackground=self.colors["text_main"], relief="flat",
                                highlightthickness=1, highlightbackground=self.colors["border"])
        self.ent_pwd.pack(pady=15, padx=50, fill=tk.X)
        self.ent_pwd.bind("<Return>", lambda e: self.authenticate())

        tk.Button(self.login_dlg, text="🔐 Login to Dashboard", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, cursor="hand2", command=self.authenticate).pack(fill=tk.X, padx=50)

    def authenticate(self):
        pwd = self.ent_pwd.get()
        if pwd == "admin123":
            self.current_user_role = "Administrator"
            self.login_dlg.destroy()
            self.initialize_application()
        else:
            messagebox.showerror("Access Denied", "Incorrect password.", parent=self.login_dlg)
            self.ent_pwd.delete(0, tk.END)

    # ==========================================
    # APP LIFECYCLE / REFRESH
    # ==========================================
    def initialize_application(self):
        self.deiconify()
        self.reload_all_data()
        self.build_ui_layout()
        self.update_clock()
        self.auto_refresh_loop()

    def _finance_db_for_current_data(self):
        """Returns a FinanceDB pointed at self.excel_mgr's current data dir,
        recreating it if the data dir changed (e.g. tests swap excel_mgr to
        a throwaway temp dir) so finance.db always lives next to whichever
        orders.xlsx is actually active."""
        data_dir = getattr(self.excel_mgr, "data_dir", None) or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        if self.finance_db is None or self._finance_db_dir != data_dir:
            self.finance_db = FinanceDB(data_dir)
            self._finance_db_dir = data_dir
        return self.finance_db

    def _app_state_for_current_data(self):
        """Same lazy-rebind pattern as _finance_db_for_current_data(), for
        the settings/session cache."""
        data_dir = getattr(self.excel_mgr, "data_dir", None) or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        if self.app_state is None or self._app_state_dir != data_dir:
            self.app_state = AppStateCache(data_dir)
            self._app_state_dir = data_dir
        return self.app_state

    def reload_all_data(self):
        """Load all data in parallel for better performance."""
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all loading tasks in parallel
            cust_future = executor.submit(self.excel_mgr.read_records, "customers.xlsx", self.cust_headers)
            emp_future = executor.submit(self.excel_mgr.read_records, "employees.xlsx", self.emp_headers)
            ord_future = executor.submit(self.excel_mgr.read_records, "orders.xlsx", self.ord_headers)
            
            # Collect results as they complete
            for future in as_completed([cust_future, emp_future, ord_future]):
                try:
                    future.result()
                except Exception as e:
                    pass
        
        # Assign results (they complete quickly)
        self.customers = cust_future.result() if cust_future.done() else []
        self.employees = emp_future.result() if emp_future.done() else []
        self.orders = ord_future.result() if ord_future.done() else []
        self.garment_types = self.excel_mgr.load_settings_list("garment_type", self.default_garments)
        self.employee_roles = self.excel_mgr.load_settings_list("employee_role", self.default_roles)
        
        # Normalize orders: ensure orders reference customers by id (customer_id) not by name
        cust_name_to_id = {clean_val(c.get('name')): clean_val(c.get('id')) for c in self.customers if c.get('id')}
        changed = False
        for o in self.orders:
            # If older files stored 'customer' as a name in the second column, map it to id
            cid = clean_val(o.get('customer_id') or '')
            if not cid:
                candidate = clean_val(o.get('customer') or '')
                # If candidate looks like an id (C-...) accept it; else try to map name -> id
                if candidate.startswith('C-'):
                    o['customer_id'] = candidate
                    changed = True
                elif candidate and candidate in cust_name_to_id:
                    o['customer_id'] = cust_name_to_id[candidate]
                    changed = True
                else:
                    # leave empty or store raw value — UI will show the raw name if mapping isn't possible
                    o['customer_id'] = candidate

        # Persist migration of orders.xlsx when we successfully mapped names -> ids
        if changed:
            try:
                rows = [[clean_val(o.get(h)) for h in self.ord_headers] for o in self.orders]
                self.excel_mgr.write_all_records('orders.xlsx', self.ord_headers, rows)
            except Exception:
                # Non-fatal — continue running with in-memory normalization
                pass

        # Recompute the finance ledger (paid/remaining/debt) from the orders
        # we just loaded. Non-fatal on failure (e.g. finance.db briefly
        # locked) — the rest of the app must keep working either way.
        try:
            self._finance_db_for_current_data().sync(self.orders, self.customers)
        except Exception as e:
            print(f"[FinanceDB] sync failed: {e}")

        # Clear memory cache periodically
        gc.collect()

    def auto_refresh_loop(self):
        self.reload_all_data()
        if hasattr(self, "tree_orders") and self.tree_orders.winfo_exists():
            self.update_graphics_and_stats()
        self.after(5000, self.auto_refresh_loop)

    # ==========================================
    # THEME / LAYOUT
    # ==========================================
    def change_theme(self, event=None):
        sel = self.cbo_theme.get()
        self.current_theme = "dark" if "Dark" in sel else "light"
        self.colors = THEMES[self.current_theme]
        self._app_state_for_current_data().save(theme=self.current_theme)
        self.header_frame.destroy()
        self.body_container.destroy()
        self.build_ui_layout()

    def build_ui_layout(self):
        self.configure(bg=self.colors["bg_body"])
        self._create_accent_strip()
        self.apply_ttk_styles()
        self.create_header()
        self.create_layout()
        # Reopen on whichever section was active before (theme rebuild,
        # or the section the user was on when they last closed the app) —
        # falls back to "dashboard" the first time the app ever runs.
        self.show_section(self.current_section if self.current_section in
                          ("dashboard", "customer", "order_card", "employee", "finance", "admin")
                          else "dashboard")
        self.update_graphics_and_stats()

    def _create_accent_strip(self):
        """Thin blue / white / red tri-color strip along the very top edge
        of the window — a small brand signature above the header bar.
        Purely decorative chrome; rebuilt on every theme switch since the
        whole window is rebuilt then too."""
        if hasattr(self, "_accent_strip") and self._accent_strip.winfo_exists():
            self._accent_strip.destroy()
        self._accent_strip = tk.Frame(self, height=4, bg=ACCENT_WHITE)
        self._accent_strip.pack(side=tk.TOP, fill=tk.X)
        for color in (ACCENT_BLUE, ACCENT_WHITE, ACCENT_RED):
            tk.Frame(self._accent_strip, bg=color, height=4).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def apply_ttk_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", background=self.colors["bg_card"], foreground=self.colors["text_main"], fieldbackground=self.colors["bg_card"], rowheight=34, font=(FONT_FAMILY, 9), borderwidth=0)
        self.style.configure("Treeview.Heading", background=self.colors["bg_body"], foreground=self.colors["text_muted"], font=(FONT_FAMILY, 8, "bold"), borderwidth=0)
        self.style.map("Treeview", background=[('selected', PRIMARY)], foreground=[('selected', 'white')])
        self.style.configure("TCombobox", font=(FONT_FAMILY, 9),
                             fieldbackground=self.colors["bg_card"], background=self.colors["bg_card"],
                             foreground=self.colors["text_main"], arrowcolor=self.colors["text_main"])
        self.style.map("TCombobox",
                       fieldbackground=[('readonly', self.colors["bg_card"])],
                       foreground=[('readonly', self.colors["text_main"])])
        self.option_add('*TCombobox*Listbox.background', self.colors["bg_card"])
        self.option_add('*TCombobox*Listbox.foreground', self.colors["text_main"])
        self.option_add('*TCombobox*Listbox.selectBackground', PRIMARY)
        self.option_add('*TCombobox*Listbox.selectForeground', "white")

    def create_header(self):
        self.header_frame = tk.Frame(self, bg=self.colors["bg_header"], height=56, highlightbackground=self.colors["border"], highlightthickness=1)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.pack_propagate(False)

        logo_box = tk.Frame(self.header_frame, bg=self.colors["bg_header"])
        logo_box.pack(side=tk.LEFT, padx=20)
        tk.Label(logo_box, text="JTC", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), padx=8, pady=2).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(logo_box, text="JHAGRA CREATION & FABRICS", bg=self.colors["bg_header"], fg=self.colors["text_main"], font=(FONT_FAMILY, 11, "bold")).pack(side=tk.LEFT)
        self.lbl_clock = tk.Label(self.header_frame, text="", bg=self.colors["bg_header"], fg=self.colors["text_muted"], font=(FONT_FAMILY, 10))
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

    def create_layout(self):
        self.body_container = tk.Frame(self, bg=self.colors["bg_body"])
        self.body_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        sidebar = tk.Frame(self.body_container, bg=self.colors["bg_sidebar"], width=220, highlightbackground=self.colors["border"], highlightthickness=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
        sidebar.pack_propagate(False)

        self.nav_buttons = {}
        nav_keys = [("dashboard", "nav_dash"), ("customer", "nav_cust"),
                    ("order_card", "nav_order_card"),
                    ("employee", "nav_emp"), ("finance", "nav_finance"),
                    ("admin", "nav_admin")]

        for key, lang_key in nav_keys:
            btn = tk.Button(sidebar, text=TRANSLATIONS[self.current_lang][lang_key], anchor="w", font=(FONT_FAMILY, 10, "bold"),
                            bg=self.colors["bg_sidebar"], fg=self.colors["text_muted"], activebackground=PRIMARY, activeforeground="white",
                            bd=0, padx=16, pady=12, cursor="hand2", command=lambda k=key: self.show_section(k))
            btn.pack(fill=tk.X, pady=2, padx=6)
            self.nav_buttons[key] = (btn, lang_key)
            # Hover feedback: lightly tint the button while the mouse is
            # over it, but only when it isn't the active section already
            # (the active one stays solid PRIMARY, handled by show_section).
            def _on_enter(e, b=btn, k=key):
                if self.current_section != k:
                    b.configure(bg=self.colors["bg_chart"])
            def _on_leave(e, b=btn, k=key):
                if self.current_section != k:
                    b.configure(bg=self.colors["bg_sidebar"])
            btn.bind("<Enter>", _on_enter)
            btn.bind("<Leave>", _on_leave)

        self.main_content = tk.Frame(self.body_container, bg=self.colors["bg_body"])
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.sections = {}
        self.build_dashboard_section()
        self.build_customer_section()
        self.build_order_card_section()
        self.build_employee_section()
        self.build_finance_section()
        self.build_admin_section()

    def show_section(self, section_key):
        for key, frame in self.sections.items():
            frame.pack_forget()
            btn, _ = self.nav_buttons[key]
            btn.configure(bg=self.colors["bg_sidebar"], fg=self.colors["text_muted"])
        self.sections[section_key].pack(fill=tk.BOTH, expand=True)
        active_btn, _ = self.nav_buttons[section_key]
        active_btn.configure(bg=PRIMARY, fg="white")
        self.current_section = section_key
        self._app_state_for_current_data().save(last_section=section_key)

    def _glass_card(self, parent, pack_opts, bg_key="bg_chart", padx=14, pady=14):
        """Soft-glass card: a frosted-tint shell with a soft border and a
        thin light-catching strip along its top edge, wrapping an inner
        frame that holds the actual padding/content.

        Returns the INNER frame — callers use it exactly like a plain
        tk.Frame from here on (add labels/widgets, .pack() them, etc.);
        only the frame's own creation + placement into `parent` are handled
        here, so nothing about existing card content changes shape.
        """
        shell = tk.Frame(parent, bg=self.colors[bg_key],
                         highlightbackground=self.colors["border"], highlightthickness=1)
        shell.pack(**pack_opts)
        tk.Frame(shell, bg=self.colors["glass_highlight"], height=2).pack(side=tk.TOP, fill=tk.X)
        inner = tk.Frame(shell, bg=self.colors[bg_key], padx=padx, pady=pady)
        inner.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        return inner

    # ==========================================
    # DASHBOARD SECTION
    # ==========================================
    def build_dashboard_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["dashboard"] = sec

        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_dash_title = tk.Label(hdr, text="Dashboard", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_dash_title.pack(anchor="w")
        self.lbl_dash_sub = tk.Label(hdr, text="Live overview of tailoring work", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_dash_sub.pack(anchor="w")

        graphics_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        graphics_frame.pack(fill=tk.X, padx=24, pady=10)

        c1 = self._glass_card(graphics_frame, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8)), padx=16, pady=12)
        i1 = tk.Frame(c1, bg=self.colors["bg_chart"]); i1.pack(side=tk.LEFT)
        self.lbl_done_title = tk.Label(i1, text="WORK DONE", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_done_title.pack(anchor="w")
        self.lbl_done_pct = tk.Label(i1, text="0%", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=SUCCESS); self.lbl_done_pct.pack(anchor="w")
        self.chart_done = CircularDonutChart(c1, size=70, ring_color=SUCCESS, bg_color=self.colors["border"], theme_colors=self.colors); self.chart_done.pack(side=tk.RIGHT)

        c2 = self._glass_card(graphics_frame, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=4), padx=16, pady=12)
        i2 = tk.Frame(c2, bg=self.colors["bg_chart"]); i2.pack(side=tk.LEFT)
        self.lbl_prog_title = tk.Label(i2, text="IN PROGRESS", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_prog_title.pack(anchor="w")
        self.lbl_prog_pct = tk.Label(i2, text="0%", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=WARNING); self.lbl_prog_pct.pack(anchor="w")
        self.chart_prog = CircularDonutChart(c2, size=70, ring_color=WARNING, bg_color=self.colors["border"], theme_colors=self.colors); self.chart_prog.pack(side=tk.RIGHT)

        c3 = self._glass_card(graphics_frame, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=(8, 0)), padx=16, pady=12)
        i3 = tk.Frame(c3, bg=self.colors["bg_chart"]); i3.pack(side=tk.LEFT)
        self.lbl_rem_title = tk.Label(i3, text="REMAINING", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_rem_title.pack(anchor="w")
        self.lbl_rem_pct = tk.Label(i3, text="0%", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=DANGER); self.lbl_rem_pct.pack(anchor="w")
        self.chart_rem = CircularDonutChart(c3, size=70, ring_color=DANGER, bg_color=self.colors["border"], theme_colors=self.colors); self.chart_rem.pack(side=tk.RIGHT)

        # --- Finance snapshot row: mirrors the Finance section's totals so
        # the money picture is visible without leaving the Dashboard. Values
        # (and the donut percentages, each share-of-grand-total) are
        # populated by refresh_finance_ui() from FinanceDB (SQL), not
        # computed here — same paired-donut layout as the order stats above.
        finance_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        finance_frame.pack(fill=tk.X, padx=24, pady=(0, 6))

        fc1 = self._glass_card(finance_frame, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8)), padx=16, pady=12)
        fi1 = tk.Frame(fc1, bg=self.colors["bg_chart"]); fi1.pack(side=tk.LEFT)
        self.lbl_fin_paid_title = tk.Label(fi1, text="TOTAL PAID", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_fin_paid_title.pack(anchor="w")
        self.lbl_fin_paid_val = tk.Label(fi1, text="PKR 0.00", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_chart"], fg=SUCCESS); self.lbl_fin_paid_val.pack(anchor="w")
        self.chart_fin_paid = CircularDonutChart(fc1, size=70, ring_color=SUCCESS, bg_color=self.colors["border"], theme_colors=self.colors); self.chart_fin_paid.pack(side=tk.RIGHT)

        fc2 = self._glass_card(finance_frame, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=4), padx=16, pady=12)
        fi2 = tk.Frame(fc2, bg=self.colors["bg_chart"]); fi2.pack(side=tk.LEFT)
        self.lbl_fin_remaining_title = tk.Label(fi2, text="TOTAL REMAINING", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_fin_remaining_title.pack(anchor="w")
        self.lbl_fin_remaining_val = tk.Label(fi2, text="PKR 0.00", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_chart"], fg=WARNING); self.lbl_fin_remaining_val.pack(anchor="w")
        self.chart_fin_remaining = CircularDonutChart(fc2, size=70, ring_color=WARNING, bg_color=self.colors["border"], theme_colors=self.colors); self.chart_fin_remaining.pack(side=tk.RIGHT)

        fc3 = self._glass_card(finance_frame, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=(8, 0)), padx=16, pady=12)
        fi3 = tk.Frame(fc3, bg=self.colors["bg_chart"]); fi3.pack(side=tk.LEFT)
        self.lbl_fin_debt_title = tk.Label(fi3, text="TOTAL DEBT", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_fin_debt_title.pack(anchor="w")
        self.lbl_fin_debt_val = tk.Label(fi3, text="PKR 0.00", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_chart"], fg=DANGER); self.lbl_fin_debt_val.pack(anchor="w")
        self.chart_fin_debt = CircularDonutChart(fc3, size=70, ring_color=DANGER, bg_color=self.colors["border"], theme_colors=self.colors); self.chart_fin_debt.pack(side=tk.RIGHT)

        tbl_bar = tk.Frame(sec, bg=self.colors["bg_card"])
        tbl_bar.pack(fill=tk.X, padx=24, pady=(16, 8))
        self.lbl_ledger_head = tk.Label(tbl_bar, text="Active Orders Ledger", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_ledger_head.pack(side=tk.LEFT)

        tk.Button(tbl_bar, text="✔ Mark Ready", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=lambda: self.quick_change_order_status("Ready")).pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        self.tree_orders = ttk.Treeview(table_frame, columns=self.ord_headers, show="headings")
        for c in self.ord_headers:
            # Display friendly header for customer_id column
            if c == 'customer_id':
                header_text = TRANSLATIONS[self.current_lang].get('tbl_cust', 'Customer').upper()
            else:
                header_text = c.upper().replace("_", " ")
            self.tree_orders.heading(c, text=header_text)
            self.tree_orders.column(c, width=90)
        self.tree_orders.pack(fill=tk.BOTH, expand=True)

        self.tree_orders.tag_configure("status_ready", foreground="#1B5E20" if self.current_theme == "light" else "#81C784")
        self.tree_orders.tag_configure("status_prog", foreground="#E65100" if self.current_theme == "light" else "#FFB74D")
        self.tree_orders.tag_configure("status_pending", foreground="#B71C1C" if self.current_theme == "light" else "#E57373")

        self.tree_orders.bind("<Button-3>", self.show_order_context_menu)

    def show_order_context_menu(self, event):
        row_id = self.tree_orders.identify_row(event.y)
        if row_id:
            self.tree_orders.selection_set(row_id)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="✔ Mark Ready", command=lambda: self.quick_change_order_status("Ready"))
            menu.add_command(label="⏳ Mark In Progress", command=lambda: self.quick_change_order_status("In Progress"))
            menu.add_separator()
            menu.add_command(label="📄 Print Order PDF", command=self.generate_order_pdf)
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def quick_change_order_status(self, new_status):
        sel = self.tree_orders.selection()
        if not sel:
            return
        ord_id = str(self.tree_orders.item(sel[0])["values"][0])
        rows_to_write = []
        for o in self.orders:
            curr_id = clean_val(o.get("id"))
            status = new_status if curr_id == ord_id else clean_val(o.get("status"))
            # Schema-aware rewrite: preserves every column (legacy + order-card).
            r = [clean_val(o.get(h)) for h in self.ord_headers]
            r[self.ord_headers.index("id")] = curr_id
            r[self.ord_headers.index("status")] = status
            rows_to_write.append(r)
        try:
            self.excel_mgr.write_all_records("orders.xlsx", self.ord_headers, rows_to_write)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))
            return
        self.reload_all_data()
        self.update_graphics_and_stats()

    # ==========================================
    # CUSTOMER SECTION
    # ==========================================
    def build_customer_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["customer"] = sec
        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_cust_title = tk.Label(hdr, text="Customer Hub", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_cust_title.pack(side=tk.LEFT)
        self.lbl_cust_sub = tk.Label(hdr, text="Manage customer profiles & measurements", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_cust_sub.pack(side=tk.LEFT, padx=12, pady=(6, 0))

        self.btn_cust_modal = tk.Button(hdr, text="➕ Add Customer", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.open_add_customer_modal)
        self.btn_cust_modal.pack(side=tk.RIGHT, padx=4)
        self.btn_new_card = tk.Button(hdr, text="🖨️ New Order Card", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=lambda: self.show_section("order_card"))
        self.btn_new_card.pack(side=tk.RIGHT, padx=4)
        self.btn_cust_receipt = tk.Button(hdr, text=TRANSLATIONS[self.current_lang].get("cust_btn_receipt", "🧾 Print Latest Receipt"), bg=WARNING, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.print_selected_customer_receipt)
        self.btn_cust_receipt.pack(side=tk.RIGHT, padx=4)
        self.btn_cust_edit = tk.Button(hdr, text=TRANSLATIONS[self.current_lang].get("cust_btn_edit", "✏️ Edit"), bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.edit_selected_customer)
        self.btn_cust_edit.pack(side=tk.RIGHT, padx=4)
        self.btn_cust_delete = tk.Button(hdr, text=TRANSLATIONS[self.current_lang].get("cust_btn_delete", "🗑️ Delete"), bg=DANGER, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.delete_selected_customer)
        self.btn_cust_delete.pack(side=tk.RIGHT, padx=4)

        # ADD SEARCH BAR FOR CUSTOMER FILTERING
        search_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        search_frame.pack(fill=tk.X, padx=24, pady=(12, 8))
        tk.Label(search_frame, text="🔍 Search:", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(side=tk.LEFT, padx=(0, 8))
        self.ent_cust_search = tk.Entry(search_frame, font=(FONT_FAMILY, 10), width=30,
                                        bg=self.colors["bg_body"], fg=self.colors["text_main"],
                                        insertbackground=self.colors["text_main"], relief="flat",
                                        highlightthickness=1, highlightbackground=self.colors["border"])
        self.ent_cust_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.ent_cust_search.bind("<KeyRelease>", self.filter_customers)
        tk.Button(search_frame, text="✖ Clear", bg=self.colors["bg_chart"], fg=self.colors["text_main"], font=(FONT_FAMILY, 9),
                 bd=0, padx=8, pady=4, cursor="hand2",
                 highlightbackground=self.colors["border"], highlightthickness=1,
                 command=self.clear_customer_search).pack(side=tk.LEFT)

        table_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        self.tree_customers = ttk.Treeview(table_frame, columns=self.cust_headers, show="headings")
        for c in self.cust_headers:
            self.tree_customers.heading(c, text=c.upper())
            self.tree_customers.column(c, width=75)
        self.tree_customers.pack(fill=tk.BOTH, expand=True)
        
        # Store original customer data for filtering
        self._customer_filter_data = []

    # ==========================================
    # ORDER CARD SECTION  (digital JTQ paper slip)
    # ==========================================
    def build_order_card_section(self):
        """Mounts the reusable OrderCardView into the main content area."""
        sec = tk.Frame(self.main_content, bg=self.colors["bg_body"])
        self.sections["order_card"] = sec
        self.order_card = OrderCardView(sec, self, self.colors, FONT_FAMILY,
                                        PRIMARY, SUCCESS, WARNING, DANGER)
        self.order_card.pack(fill=tk.BOTH, expand=True)

    # ==========================================
    # EMPLOYEE SECTION
    # ==========================================
    def build_employee_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["employee"] = sec
        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_emp_title = tk.Label(hdr, text="Staff & Tailors", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_emp_title.pack(side=tk.LEFT)
        self.lbl_emp_sub = tk.Label(hdr, text="Manage staff, roles and daily tasks", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_emp_sub.pack(side=tk.LEFT, padx=12, pady=(6, 0))

        self.btn_task_modal = tk.Button(hdr, text="🛠️ Assign Task", bg=WARNING, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.open_assign_task_modal)
        self.btn_task_modal.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_modal = tk.Button(hdr, text="➕ Add Staff", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.open_add_employee_modal)
        self.btn_emp_modal.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_print = tk.Button(hdr, text="🧾 Print Task Slip", bg=WARNING, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.print_selected_employee_task)
        self.btn_emp_print.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_edit = tk.Button(hdr, text="✏️ Edit", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.edit_selected_employee)
        self.btn_emp_edit.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_delete = tk.Button(hdr, text="🗑️ Delete", bg=DANGER, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.delete_selected_employee)
        self.btn_emp_delete.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)
        self.tree_employees = ttk.Treeview(table_frame, columns=self.emp_headers, show="headings")
        for c in self.emp_headers:
            self.tree_employees.heading(c, text=c.upper())
            self.tree_employees.column(c, width=120)
        self.tree_employees.pack(fill=tk.BOTH, expand=True)

    # ==========================================
    # FINANCE SECTION
    # ==========================================
    def build_finance_section(self):
        """Paid / remaining / debt, sourced entirely from FinanceDB (SQL) —
        see refresh_finance_ui() for how the numbers get in here. Includes
        a small tab bar (All / Done / Due / Add Payment) above the ledger."""
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["finance"] = sec
        self.finance_tab = getattr(self, "finance_tab", "all")

        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_fin_title = tk.Label(hdr, text="Finance", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_fin_title.pack(anchor="w")
        self.lbl_fin_sub = tk.Label(hdr, text="Paid, remaining and debt across all orders", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_fin_sub.pack(anchor="w")

        cards_row = tk.Frame(sec, bg=self.colors["bg_card"])
        cards_row.pack(fill=tk.X, padx=24, pady=10)

        c1 = self._glass_card(cards_row, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8)), padx=16, pady=14)
        self.lbl_fin_card_paid_title = tk.Label(c1, text="TOTAL PAID", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_fin_card_paid_title.pack(anchor="w")
        self.lbl_fin_card_paid_val = tk.Label(c1, text="PKR 0.00", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=SUCCESS); self.lbl_fin_card_paid_val.pack(anchor="w")

        c2 = self._glass_card(cards_row, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=4), padx=16, pady=14)
        self.lbl_fin_card_remaining_title = tk.Label(c2, text="TOTAL REMAINING", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_fin_card_remaining_title.pack(anchor="w")
        self.lbl_fin_card_remaining_val = tk.Label(c2, text="PKR 0.00", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=WARNING); self.lbl_fin_card_remaining_val.pack(anchor="w")

        c3 = self._glass_card(cards_row, dict(side=tk.LEFT, expand=True, fill=tk.X, padx=(8, 0)), padx=16, pady=14)
        self.lbl_fin_card_debt_title = tk.Label(c3, text="TOTAL DEBT (delivered, unpaid)", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_fin_card_debt_title.pack(anchor="w")
        self.lbl_fin_card_debt_val = tk.Label(c3, text="PKR 0.00", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=DANGER); self.lbl_fin_card_debt_val.pack(anchor="w")

        # --- Tab bar: All / Done / Due / Add Payment ---
        tab_bar = tk.Frame(sec, bg=self.colors["bg_card"])
        tab_bar.pack(fill=tk.X, padx=24, pady=(6, 8))
        self.fin_tab_buttons = {}
        tab_specs = [("all", "fin_tab_all", "📋"), ("done", "fin_tab_done", "✅"),
                     ("due", "fin_tab_due", "⚠️"), ("add", "fin_tab_add", "➕")]
        for key, lang_key, icon in tab_specs:
            b = tk.Button(tab_bar, text=f"{icon} {TRANSLATIONS[self.current_lang][lang_key]}",
                         font=(FONT_FAMILY, 9, "bold"), bd=0, padx=14, pady=6, cursor="hand2",
                         command=lambda k=key: self.set_finance_tab(k))
            b.pack(side=tk.LEFT, padx=(0, 6))
            self.fin_tab_buttons[key] = (b, lang_key, icon)

        # --- Ledger table (All / Done / Due) ---
        self.fin_ledger_container = tk.Frame(sec, bg=self.colors["bg_card"])

        tbl_bar = tk.Frame(self.fin_ledger_container, bg=self.colors["bg_card"])
        tbl_bar.pack(fill=tk.X, pady=(8, 8))
        self.lbl_fin_tbl_head = tk.Label(tbl_bar, text="Order Finance Ledger", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_fin_tbl_head.pack(side=tk.LEFT)

        table_frame = tk.Frame(self.fin_ledger_container, bg=self.colors["bg_card"])
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.fin_columns = ("order_id", "customer_name", "garment", "total", "paid", "remaining", "debt", "status", "delivery_status")
        self.tree_finance = ttk.Treeview(table_frame, columns=self.fin_columns, show="headings")
        for c in self.fin_columns:
            self.tree_finance.heading(c, text=c.replace("_", " ").upper())
            self.tree_finance.column(c, width=100)
        self.tree_finance.pack(fill=tk.BOTH, expand=True)

        self.tree_finance.tag_configure("has_debt", foreground="#B71C1C" if self.current_theme == "light" else "#E57373")
        self.tree_finance.tag_configure("has_remaining", foreground="#E65100" if self.current_theme == "light" else "#FFB74D")

        # --- Add Payment form ---
        self.fin_add_container = tk.Frame(sec, bg=self.colors["bg_card"])
        add_card = self._glass_card(self.fin_add_container, dict(fill=tk.X), padx=20, pady=18, bg_key="bg_card")
        self.lbl_fin_add_heading = tk.Label(add_card, text="➕ Record a Payment", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_fin_add_heading.pack(anchor="w", pady=(0, 12))

        self.lbl_fin_add_order = tk.Label(add_card, text="Order with a due balance:", font=(FONT_FAMILY, 9, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_fin_add_order.pack(anchor="w")
        self.cbo_fin_pay_order = ttk.Combobox(add_card, state="readonly", font=(FONT_FAMILY, 10))
        self.cbo_fin_pay_order.pack(fill=tk.X, pady=(4, 12))

        self.lbl_fin_add_amount = tk.Label(add_card, text="Payment Amount (PKR):", font=(FONT_FAMILY, 9, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_fin_add_amount.pack(anchor="w")
        self.ent_fin_pay_amount = tk.Entry(add_card, font=(FONT_FAMILY, 11),
                                           bg=self.colors["bg_body"], fg=self.colors["text_main"],
                                           insertbackground=self.colors["text_main"], relief="flat",
                                           highlightthickness=1, highlightbackground=self.colors["border"])
        self.ent_fin_pay_amount.pack(fill=tk.X, pady=(4, 14))

        self.btn_fin_pay_submit = tk.Button(add_card, text="💾 Record Payment", bg=SUCCESS, fg="white",
                                            font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, cursor="hand2",
                                            command=self.record_finance_payment)
        self.btn_fin_pay_submit.pack(fill=tk.X)

        self.set_finance_tab(self.finance_tab)

    def set_finance_tab(self, tab_key):
        """Switches the Finance view between the All/Done/Due ledger and the
        Add Payment form, restyling the tab buttons to show which is active."""
        self.finance_tab = tab_key
        for key, (b, lang_key, icon) in self.fin_tab_buttons.items():
            active = key == tab_key
            b.configure(bg=PRIMARY if active else self.colors["bg_chart"],
                       fg="white" if active else self.colors["text_main"])
        if tab_key == "add":
            self.fin_ledger_container.pack_forget()
            self._refresh_finance_payment_picker()
            self.fin_add_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))
        else:
            self.fin_add_container.pack_forget()
            self.fin_ledger_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))
            self.refresh_finance_ui()

    def _refresh_finance_payment_picker(self):
        """Fills the Add Payment order picker with only orders that still
        carry a due balance (remaining or debt > 0)."""
        if not (hasattr(self, "cbo_fin_pay_order") and self.cbo_fin_pay_order.winfo_exists()):
            return
        try:
            due_rows = [r for r in self._finance_db_for_current_data().get_rows()
                       if (r.get("remaining") or 0) > 0 or (r.get("debt") or 0) > 0]
        except Exception:
            due_rows = []
        options = [f"{r['order_id']} - {r['customer_name']} (Due PKR {(r.get('remaining') or 0) + (r.get('debt') or 0):,.2f})"
                  for r in due_rows]
        self.cbo_fin_pay_order.configure(values=options)
        if options:
            self.cbo_fin_pay_order.current(0)
        else:
            self.cbo_fin_pay_order.set("")

    def record_finance_payment(self):
        """Applies a manual payment to the selected order's `advance` field
        (capped at the order's total), writes it back to orders.xlsx with
        the same schema-aware rewrite pattern used elsewhere, then reloads
        so the Finance/Dashboard figures and the order card reflect it."""
        selection = self.cbo_fin_pay_order.get().strip()
        if not selection:
            messagebox.showwarning("No Order Selected", "Pick an order with a due balance first.")
            return
        order_id = selection.split(" - ", 1)[0].strip()
        try:
            amount = float(self.ent_fin_pay_amount.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Amount", "Enter a valid numeric payment amount.")
            return
        if amount <= 0:
            messagebox.showerror("Invalid Amount", "Payment amount must be greater than zero.")
            return

        order = next((o for o in self.orders if clean_val(o.get("id")) == order_id), None)
        if not order:
            messagebox.showerror("Not Found", f"Order {order_id} could not be found.")
            return

        total = card_svc.clean_num(order.get("total"))
        old_advance = card_svc.clean_num(order.get("advance"))
        new_advance = min(total, round(old_advance + amount, 2))
        new_remaining = card_svc.compute_remaining(total, new_advance)

        rows_to_write = []
        for o in self.orders:
            curr_id = clean_val(o.get("id"))
            r = [clean_val(o.get(h)) for h in self.ord_headers]
            if curr_id == order_id:
                r[self.ord_headers.index("advance")] = f"{new_advance:.2f}"
                r[self.ord_headers.index("remaining")] = f"{new_remaining:.2f}"
            rows_to_write.append(r)
        try:
            self.excel_mgr.write_all_records("orders.xlsx", self.ord_headers, rows_to_write)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))
            return

        self.reload_all_data()
        self.update_graphics_and_stats()
        self.ent_fin_pay_amount.delete(0, tk.END)
        self._refresh_finance_payment_picker()
        messagebox.showinfo("Payment Recorded", f"Recorded PKR {amount:,.2f} against {order_id}.")

    def refresh_finance_ui(self):
        """Pulls paid/remaining/debt back out via SQL (FinanceDB) and paints
        both the Dashboard's finance snapshot row and the Finance section's
        summary cards + per-order table (filtered by the active Done/Due/All
        tab). Safe to call before the Finance section exists (auto_refresh_
        loop can fire before build_ui_layout)."""
        try:
            fdb = self._finance_db_for_current_data()
            totals = fdb.get_totals()
        except Exception as e:
            print(f"[FinanceDB] refresh failed: {e}")
            return

        def fmt(v):
            return f"PKR {v:,.2f}"

        # Each donut shows that bucket's share of the shop's total order
        # value (paid + remaining + debt) — same "percent of the whole"
        # reading as the WORK DONE / IN PROGRESS / REMAINING donuts above.
        grand_total = totals["paid"] + totals["remaining"] + totals["debt"]
        paid_pct = int(round((totals["paid"] / grand_total) * 100)) if grand_total > 0 else 0
        remaining_pct = int(round((totals["remaining"] / grand_total) * 100)) if grand_total > 0 else 0
        debt_pct = int(round((totals["debt"] / grand_total) * 100)) if grand_total > 0 else 0

        if hasattr(self, "lbl_fin_paid_val") and self.lbl_fin_paid_val.winfo_exists():
            self.lbl_fin_paid_val.configure(text=fmt(totals["paid"]))
            self.lbl_fin_remaining_val.configure(text=fmt(totals["remaining"]))
            self.lbl_fin_debt_val.configure(text=fmt(totals["debt"]))
            self.chart_fin_paid.set_percentage(paid_pct)
            self.chart_fin_remaining.set_percentage(remaining_pct)
            self.chart_fin_debt.set_percentage(debt_pct)

        if not (hasattr(self, "tree_finance") and self.tree_finance.winfo_exists()):
            return

        self.lbl_fin_card_paid_val.configure(text=fmt(totals["paid"]))
        self.lbl_fin_card_remaining_val.configure(text=fmt(totals["remaining"]))
        self.lbl_fin_card_debt_val.configure(text=fmt(totals["debt"]))

        rows = fdb.get_rows()
        tab = getattr(self, "finance_tab", "all")
        if tab == "done":
            rows = [r for r in rows if (r.get("remaining") or 0) <= 0 and (r.get("debt") or 0) <= 0 and (r.get("total") or 0) > 0]
        elif tab == "due":
            rows = [r for r in rows if (r.get("remaining") or 0) > 0 or (r.get("debt") or 0) > 0]

        self.tree_finance.delete(*self.tree_finance.get_children())
        for row in rows:
            debt = row.get("debt") or 0
            remaining = row.get("remaining") or 0
            tag = "has_debt" if debt > 0 else "has_remaining" if remaining > 0 else ""
            values = [
                row.get("order_id", ""), row.get("customer_name", ""), row.get("garment", ""),
                f"{row.get('total', 0):.2f}", f"{row.get('paid', 0):.2f}",
                f"{remaining:.2f}", f"{debt:.2f}",
                row.get("status", ""), row.get("delivery_status", ""),
            ]
            self.tree_finance.insert("", tk.END, values=values, tags=(tag,) if tag else ())

    # ==========================================
    # ADMIN / SETTINGS SECTION
    # ==========================================
    def build_admin_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["admin"] = sec
        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_admin_title = tk.Label(hdr, text="Settings", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_admin_title.pack(anchor="w")
        self.lbl_admin_sub = tk.Label(hdr, text="Theme, language, garments & employee roles", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_admin_sub.pack(anchor="w")

        cards_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=10)

        # Row 1: Theme + Language
        row1 = tk.Frame(cards_frame, bg=self.colors["bg_card"])
        row1.pack(fill=tk.X, pady=(0, 10))

        c_theme = self._glass_card(row1, dict(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6)))
        self.lbl_theme_label = tk.Label(c_theme, text="🛠️ System Theme", font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"])
        self.lbl_theme_label.pack(anchor="w", pady=(0, 8))
        self.cbo_theme = ttk.Combobox(c_theme, values=["Light Mode ☀️", "Dark Mode 🌙"], state="readonly")
        self.cbo_theme.current(0 if self.current_theme == "light" else 1)
        self.cbo_theme.pack(fill=tk.X, pady=(2, 4))
        self.cbo_theme.bind("<<ComboboxSelected>>", self.change_theme)

        c_lang = self._glass_card(row1, dict(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0)))
        self.lbl_language_label = tk.Label(c_lang, text="🌐 Language / زبان", font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"])
        self.lbl_language_label.pack(anchor="w", pady=(0, 8))
        self.cbo_lang = ttk.Combobox(c_lang, values=[label for _, label in LANGUAGE_OPTIONS], state="readonly")
        if self.current_lang in [code for code, _ in LANGUAGE_OPTIONS]:
            self.cbo_lang.current([code for code, _ in LANGUAGE_OPTIONS].index(self.current_lang))
        else:
            self.cbo_lang.current(0)
        self.cbo_lang.pack(fill=tk.X, pady=(2, 4))
        self.cbo_lang.bind("<<ComboboxSelected>>", self.on_language_change)

        # Row 2: Garment types + Employee roles
        row2 = tk.Frame(cards_frame, bg=self.colors["bg_card"])
        row2.pack(fill=tk.BOTH, expand=True)

        c_garments = self._glass_card(row2, dict(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6)))
        self.lbl_admin_card_garments = tk.Label(c_garments, text=TRANSLATIONS[self.current_lang].get("admin_card_garments", "🧵 Garment Types"), font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"])
        self.lbl_admin_card_garments.pack(anchor="w", pady=(0, 8))

        list_wrap_g = tk.Frame(c_garments, bg=self.colors["bg_chart"])
        list_wrap_g.pack(fill=tk.BOTH, expand=True)
        self.lst_garments = tk.Listbox(list_wrap_g, bg=self.colors["bg_card"], fg=self.colors["text_main"], selectbackground=PRIMARY, selectforeground="white", highlightthickness=1, highlightbackground=self.colors["border"], font=(FONT_FAMILY, 9))
        sb_g = ttk.Scrollbar(list_wrap_g, orient=tk.VERTICAL, command=self.lst_garments.yview)
        self.lst_garments.configure(yscrollcommand=sb_g.set)
        self.lst_garments.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_g.pack(side=tk.RIGHT, fill=tk.Y)

        ent_row_g = tk.Frame(c_garments, bg=self.colors["bg_chart"])
        ent_row_g.pack(fill=tk.X, pady=(8, 0))
        self.ent_new_garment = tk.Entry(ent_row_g, font=(FONT_FAMILY, 9),
                                        bg=self.colors["bg_body"], fg=self.colors["text_main"],
                                        insertbackground=self.colors["text_main"], relief="flat",
                                        highlightthickness=1, highlightbackground=self.colors["border"])
        self.ent_new_garment.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.btn_add_garment = tk.Button(ent_row_g, text=TRANSLATIONS[self.current_lang].get("btn_item_add", "➕ Add"), bg=PRIMARY, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.add_garment_type)
        self.btn_add_garment.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_remove_garment = tk.Button(ent_row_g, text=TRANSLATIONS[self.current_lang].get("btn_item_remove", "✖ Remove"), bg=DANGER, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.remove_garment_type)
        self.btn_remove_garment.pack(side=tk.LEFT)

        c_roles = self._glass_card(row2, dict(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0)))
        self.lbl_admin_card_roles = tk.Label(c_roles, text=TRANSLATIONS[self.current_lang].get("admin_card_roles", "👔 Employee Roles"), font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"])
        self.lbl_admin_card_roles.pack(anchor="w", pady=(0, 8))

        list_wrap_r = tk.Frame(c_roles, bg=self.colors["bg_chart"])
        list_wrap_r.pack(fill=tk.BOTH, expand=True)
        self.lst_roles = tk.Listbox(list_wrap_r, bg=self.colors["bg_card"], fg=self.colors["text_main"], selectbackground=PRIMARY, selectforeground="white", highlightthickness=1, highlightbackground=self.colors["border"], font=(FONT_FAMILY, 9))
        sb_r = ttk.Scrollbar(list_wrap_r, orient=tk.VERTICAL, command=self.lst_roles.yview)
        self.lst_roles.configure(yscrollcommand=sb_r.set)
        self.lst_roles.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_r.pack(side=tk.RIGHT, fill=tk.Y)

        ent_row_r = tk.Frame(c_roles, bg=self.colors["bg_chart"])
        ent_row_r.pack(fill=tk.X, pady=(8, 0))
        self.ent_new_role = tk.Entry(ent_row_r, font=(FONT_FAMILY, 9),
                                     bg=self.colors["bg_body"], fg=self.colors["text_main"],
                                     insertbackground=self.colors["text_main"], relief="flat",
                                     highlightthickness=1, highlightbackground=self.colors["border"])
        self.ent_new_role.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.btn_add_role = tk.Button(ent_row_r, text=TRANSLATIONS[self.current_lang].get("btn_item_add", "➕ Add"), bg=PRIMARY, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.add_employee_role)
        self.btn_add_role.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_remove_role = tk.Button(ent_row_r, text=TRANSLATIONS[self.current_lang].get("btn_item_remove", "✖ Remove"), bg=DANGER, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.remove_employee_role)
        self.btn_remove_role.pack(side=tk.LEFT)

        self.refresh_settings_ui()

    def refresh_settings_ui(self):
        self.lst_garments.delete(0, tk.END)
        for g in self.garment_types:
            self.lst_garments.insert(tk.END, g)
        self.lst_roles.delete(0, tk.END)
        for r in self.employee_roles:
            self.lst_roles.insert(tk.END, r)

    # --- Garment type management ---
    def add_garment_type(self):
        val = self.ent_new_garment.get().strip()
        if not val:
            return
        if val in self.garment_types:
            messagebox.showinfo("Already Exists", "This garment type is already in the list.")
            return
        self.garment_types.append(val)
        try:
            self.excel_mgr.save_settings_list("garment_type", self.garment_types)
            self.ent_new_garment.delete(0, tk.END)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_garment_type(self):
        sel = self.lst_garments.curselection()
        if not sel:
            return
        val = self.lst_garments.get(sel[0])
        self.garment_types.remove(val)
        try:
            self.excel_mgr.save_settings_list("garment_type", self.garment_types)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # --- Employee role management ---
    def add_employee_role(self):
        val = self.ent_new_role.get().strip()
        if not val:
            return
        if val in self.employee_roles:
            messagebox.showinfo("Already Exists", "This role is already in the list.")
            return
        self.employee_roles.append(val)
        try:
            self.excel_mgr.save_settings_list("employee_role", self.employee_roles)
            self.ent_new_role.delete(0, tk.END)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_employee_role(self):
        sel = self.lst_roles.curselection()
        if not sel:
            return
        val = self.lst_roles.get(sel[0])
        self.employee_roles.remove(val)
        try:
            self.excel_mgr.save_settings_list("employee_role", self.employee_roles)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ==========================================
    # MODALS MATCHING PHYSICAL RECEIPT FORM
    # ==========================================
    def open_add_customer_modal(self):
        # Merge with English so a partial language pack never KeyErrors —
        # same pattern as apply_language_pack(). Built once per open, since
        # this dialog (unlike the persistent Order Card screen) is created
        # fresh every time and doesn't need to react to a later language
        # switch while it's open.
        t = {**TRANSLATIONS["en"], **TRANSLATIONS.get(self.current_lang, {})}

        dlg = tk.Toplevel(self)
        dlg.title(t["nc_title"])
        dlg.geometry("500x590")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text=t["nc_heading"], font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=12)

        info_frame = tk.Frame(dlg, bg=self.colors["bg_card"])
        info_frame.pack(fill=tk.X, padx=20)
        tk.Label(info_frame, text=t["nc_name"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=0, column=0, sticky="w")
        e_name = tk.Entry(info_frame, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                          insertbackground=self.colors["text_main"], relief="flat",
                          highlightthickness=1, highlightbackground=self.colors["border"])
        e_name.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Label(info_frame, text=t["nc_phone"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=1, column=0, sticky="w")
        e_phone = tk.Entry(info_frame, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                           insertbackground=self.colors["text_main"], relief="flat",
                           highlightthickness=1, highlightbackground=self.colors["border"])
        e_phone.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        tk.Label(info_frame, text=t["nc_address"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=2, column=0, sticky="w")
        e_address = tk.Entry(info_frame, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                             insertbackground=self.colors["text_main"], relief="flat",
                             highlightthickness=1, highlightbackground=self.colors["border"])
        e_address.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        info_frame.columnconfigure(1, weight=1)

        measure_frame = tk.LabelFrame(dlg, text=t["nc_measurements_frame"], bg=self.colors["bg_card"], fg=PRIMARY, font=(FONT_FAMILY, 9, "bold"))
        measure_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # (translation key, customers.xlsx column) — order matches the
        # physical paper slip's layout, unchanged from before.
        fields = [
            ("meas_lambai", "length"), ("meas_sleeve", "sleeve"), ("meas_shoulder", "shoulder"),
            ("meas_collar", "collar"), ("meas_chest", "chest"), ("meas_waist", "waist"),
            ("meas_daman", "daman"), ("meas_shalwar_length", "shalwar_len"), ("meas_paancha", "paancha"),
        ]
        entries = {}
        for idx, (lbl_key, key) in enumerate(fields):
            r = idx // 2
            c = (idx % 2) * 2
            tk.Label(measure_frame, text=t[lbl_key], bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8)).grid(row=r, column=c, padx=5, pady=5, sticky="e")
            ent = tk.Entry(measure_frame, width=10, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                           insertbackground=self.colors["text_main"], relief="flat",
                           highlightthickness=1, highlightbackground=self.colors["border"])
            ent.grid(row=r, column=c + 1, padx=5, pady=5, sticky="w")
            entries[key] = ent

        def save():
            if not e_name.get():
                messagebox.showerror("Error", "Name required!")
                return
            c_id = self._next_id("C", self.customers, 101)
            created_date = datetime.now().strftime("%Y-%m-%d")
            row = ([c_id, e_name.get(), e_phone.get()]
                   + [entries[k].get() or "0" for k in [f[1] for f in fields]]
                   + [e_address.get().strip(), created_date])
            try:
                self.excel_mgr.append_record("customers.xlsx", self.cust_headers, row)
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text=t["nc_save"], bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=10)

    def open_add_order_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Create Style Order")
        dlg.geometry("520x660")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text="Garment Style Configuration", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=10)

        f1 = tk.Frame(dlg, bg=self.colors["bg_card"])
        f1.pack(fill=tk.X, padx=20)
        cbo_cust = ttk.Combobox(f1, values=[f"{c['id']} - {c['name']}" for c in self.customers if c.get("name")], state="readonly")
        if cbo_cust["values"]:
            cbo_cust.current(0)
        tk.Label(f1, text="Customer:", bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w"); cbo_cust.pack(fill=tk.X, pady=(0, 5))

        cbo_garment = ttk.Combobox(f1, values=self.garment_types, state="readonly")
        if cbo_garment["values"]:
            cbo_garment.current(0)
        tk.Label(f1, text="Garment:", bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w"); cbo_garment.pack(fill=tk.X, pady=(0, 5))

        cbo_tailor = ttk.Combobox(f1, values=[e["name"] for e in self.employees if e.get("name")], state="readonly")
        if cbo_tailor["values"]:
            cbo_tailor.current(0)
        tk.Label(f1, text="Assign Tailor:", bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w"); cbo_tailor.pack(fill=tk.X, pady=(0, 5))

        style_frame = tk.LabelFrame(dlg, text=" Visual Form Styles (as per JTQ slip) ", bg=self.colors["bg_card"], fg=PRIMARY, font=(FONT_FAMILY, 9, "bold"))
        style_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Exact groups from the physical JTQ slip
        style_options = {
            "Button Style": ["Baz Button (باز بٹن)", "Karh Button (کڑ بٹن)"],
            "Collar Type": ["Half Ban", "Cut Ban", "Normal Ban", "Collar (کالر)"],
            "Cuff Type": ["Round Cuff (گول کف)", "Square Cuff (چورس کف)", "Round Sleeve Cut (گول بازو)", "Round Sleeve"],
            "Pocket Type": ["Side Pocket (سائن با کٹ)", "Round Pocket (گول جیب)", "Shalwar Pocket (شلوار جیب)", "Simple Patti (سادہ پٹی)", "Patti (پٹی)"],
            "Daman Type": ["Square Daman (چورس واشن)", "Round Daman (گول واشن)"],
            "Stitching": ["1. Single Stitch", "2. Double Stitch", "3. Choka Stitch", "4. Triple Stitch"]
        }

        combos = {}
        rows = list(style_options.items())

        # Left column: button/placket styles (باز بٹن / کڑ بٹن)
        label, opts = rows[0]
        tk.Label(style_frame, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8, "bold")).grid(row=0, column=0, padx=8, pady=8, sticky="e")
        cb = ttk.Combobox(style_frame, values=opts, state="readonly", width=26)
        cb.current(0)
        cb.grid(row=0, column=1, padx=8, pady=8, sticky="w")
        combos[label] = cb

        # Center column: Collar, Cuff, Pocket, Daman
        for r, (label, opts) in enumerate(rows[1:5], start=0):
            tk.Label(style_frame, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8, "bold")).grid(row=r, column=2, padx=8, pady=8, sticky="e")
            cb = ttk.Combobox(style_frame, values=opts, state="readonly", width=26)
            cb.current(0)
            cb.grid(row=r, column=3, padx=8, pady=8, sticky="w")
            combos[label] = cb

        # Bottom of the center column: Stitching (the 4 numbered options on the slip)
        label, opts = rows[5]
        tk.Label(style_frame, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8, "bold")).grid(row=5, column=2, padx=8, pady=8, sticky="e")
        cb = ttk.Combobox(style_frame, values=opts, state="readonly", width=26)
        cb.current(0)
        cb.grid(row=5, column=3, padx=8, pady=8, sticky="w")
        combos[label] = cb

        style_frame.columnconfigure(1, weight=1)
        style_frame.columnconfigure(3, weight=1)

        def save():
            if not cbo_cust.get() or not cbo_tailor.get():
                messagebox.showerror("Error", "Customer & Tailor needed!")
                return
            c_id = cbo_cust.get().split(" - ")[0]
            c_name = cbo_cust.get().split(" - ")[-1]
            o_id = self._next_id("ORD", self.orders, 101)

            row = [
                o_id, c_id, cbo_garment.get() or "Shalwar Kameez", "In Progress", cbo_tailor.get(),
                combos["Collar Type"].get(), combos["Cuff Type"].get(),
                combos["Pocket Type"].get(), combos["Daman Type"].get(), combos["Stitching"].get(),
                combos["Button Style"].get()
            ]
            try:
                self.excel_mgr.append_record("orders.xlsx", self.ord_headers, row)
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text="✅ Place Order", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=10)

    def open_add_employee_modal(self):
        t = {**TRANSLATIONS["en"], **TRANSLATIONS.get(self.current_lang, {})}

        dlg = tk.Toplevel(self)
        dlg.title(t["emp_modal_title"])
        dlg.geometry("400x260")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text=t["emp_modal_heading"], font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=(14, 10))

        f = tk.Frame(dlg, bg=self.colors["bg_card"])
        f.pack(fill=tk.X, padx=24)
        tk.Label(f, text=t["emp_lbl_full_name"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=0, column=0, sticky="w", pady=4)
        e_name = tk.Entry(f, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                          insertbackground=self.colors["text_main"], relief="flat",
                          highlightthickness=1, highlightbackground=self.colors["border"])
        e_name.grid(row=0, column=1, padx=8, pady=4, sticky="ew")
        tk.Label(f, text=t["emp_lbl_phone"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=1, column=0, sticky="w", pady=4)
        e_phone = tk.Entry(f, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                           insertbackground=self.colors["text_main"], relief="flat",
                           highlightthickness=1, highlightbackground=self.colors["border"])
        e_phone.grid(row=1, column=1, padx=8, pady=4, sticky="ew")
        tk.Label(f, text=t["emp_lbl_role"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=2, column=0, sticky="w", pady=4)
        cbo_role = ttk.Combobox(f, values=self.employee_roles, state="readonly")
        if cbo_role["values"]:
            cbo_role.current(0)
        cbo_role.grid(row=2, column=1, padx=8, pady=4, sticky="ew")
        f.columnconfigure(1, weight=1)

        def save():
            if not e_name.get():
                messagebox.showerror("Error", "Name required!")
                return
            e_id = self._next_id("E", self.employees, 1)
            row = [e_id, e_name.get(), e_phone.get(), cbo_role.get() or "Tailor", "On Duty", "None"]
            try:
                self.excel_mgr.append_record("employees.xlsx", self.emp_headers, row)
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text=t["emp_btn_save_staff"], bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=24, pady=(14, 10))

    def open_assign_task_modal(self):
        """Assign an existing order (picked by customer name) to a staff
        member. Selecting an order shows its details read-only, mirroring
        the order card's customer auto-fill. Confirming links both ways —
        the order's Tailor field AND the employee's Current Task — so the
        Dashboard's Active Orders Ledger (which reads Tailor live) and the
        Employee table both reflect the assignment immediately."""
        t = {**TRANSLATIONS["en"], **TRANSLATIONS.get(self.current_lang, {})}

        dlg = tk.Toplevel(self)
        dlg.title(t["task_modal_title"])
        dlg.geometry("440x480")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text=t["task_modal_heading"], font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=(14, 10))

        f = tk.Frame(dlg, bg=self.colors["bg_card"])
        f.pack(fill=tk.BOTH, expand=True, padx=24)

        tk.Label(f, text=t["task_lbl_staff_member"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(0, 2))
        cbo_emp = ttk.Combobox(f, values=[f"{e['id']} - {e['name']}" for e in self.employees if e.get("name")], state="readonly")
        if cbo_emp["values"]:
            cbo_emp.current(0)
        cbo_emp.pack(fill=tk.X, pady=(0, 8))
        if not cbo_emp["values"]:
            tk.Label(f, text=t["task_lbl_no_staff"], bg=self.colors["bg_card"], fg=DANGER, font=(FONT_FAMILY, 8)).pack(anchor="w")

        # --- Order picker: open orders (not yet Delivered), labeled by
        # customer name — not a raw order id, so a tailor can find "who".
        cust_by_id = {clean_val(c.get("id")): clean_val(c.get("name")) for c in self.customers}
        open_orders = {clean_val(o.get("id")): o for o in self.orders
                       if clean_val(o.get("id")) and clean_val(o.get("status")) != "Delivered"}
        order_labels = {}
        for oid, o in open_orders.items():
            cust_name = cust_by_id.get(clean_val(o.get("customer_id"))) or "Walk-in"
            order_labels[f"{oid} — {cust_name} ({clean_val(o.get('garment'))})"] = oid

        tk.Label(f, text=t["task_lbl_order"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(6, 2))
        cbo_order = ttk.Combobox(f, values=list(order_labels.keys()), state="readonly")
        cbo_order.pack(fill=tk.X, pady=(0, 8))
        if not order_labels:
            tk.Label(f, text=t["task_lbl_no_orders"], bg=self.colors["bg_card"], fg=DANGER, font=(FONT_FAMILY, 8)).pack(anchor="w")

        # Read-only order-details block, filled in once an order is picked.
        details = self._glass_card(f, dict(fill=tk.X, pady=(0, 8)), padx=10, pady=8)
        detail_specs = [
            ("garment", "task_details_garment"), ("status", "task_details_status"),
            ("order_date", "task_details_order_date"), ("delivery_date", "task_details_delivery_date"),
            ("tailor", "task_details_tailor"),
            ("total", "task_details_total"), ("advance", "task_details_advance"), ("remaining", "task_details_remaining"),
        ]
        detail_vals = {}
        for field, label_key in detail_specs:
            row = tk.Frame(details, bg=self.colors["bg_chart"])
            row.pack(fill=tk.X)
            tk.Label(row, text=t[label_key] + ":", width=16, anchor="w", font=(FONT_FAMILY, 8),
                    bg=self.colors["bg_chart"], fg=self.colors["text_muted"]).pack(side=tk.LEFT)
            val_lbl = tk.Label(row, text="—", anchor="w", font=(FONT_FAMILY, 8, "bold"),
                               bg=self.colors["bg_chart"], fg=self.colors["text_main"])
            val_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            detail_vals[field] = val_lbl

        tk.Label(f, text=t["task_lbl_task_note"], font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(4, 2))
        e_task = tk.Entry(f, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                          insertbackground=self.colors["text_main"], relief="flat",
                          highlightthickness=1, highlightbackground=self.colors["border"])
        e_task.pack(fill=tk.X, pady=(0, 10))

        def on_order_selected(event=None):
            oid = order_labels.get(cbo_order.get())
            order = open_orders.get(oid)
            if not order:
                return
            for field, lbl in detail_vals.items():
                lbl.configure(text=clean_val(order.get(field)) or "—")
            cust_name = cust_by_id.get(clean_val(order.get("customer_id"))) or "Walk-in"
            e_task.delete(0, tk.END)
            e_task.insert(0, f"{clean_val(order.get('garment'))} for {cust_name} ({oid})")

        cbo_order.bind("<<ComboboxSelected>>", on_order_selected)

        def save():
            if not cbo_emp.get() or not cbo_order.get():
                messagebox.showerror("Error", "Select a staff member and an order!")
                return
            emp_id = cbo_emp.get().split(" - ")[0]
            emp_name = next((e.get("name") for e in self.employees if clean_val(e.get("id")) == emp_id), "")
            oid = order_labels[cbo_order.get()]
            task_text = e_task.get().strip() or cbo_order.get()

            self._assign_order_tailor(oid, emp_name)
            self.update_employee_task(emp_id, task_text)
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text=t["task_btn_assign"], bg=WARNING, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=24, pady=(0, 14))

    def update_employee_task(self, emp_id, task_text):
        rows_to_write = []
        for e in self.employees:
            curr_id = clean_val(e.get("id"))
            is_target = curr_id == emp_id
            status = "On Task" if is_target else clean_val(e.get("status"))
            current_task = task_text if is_target else clean_val(e.get("current_task"))
            rows_to_write.append([curr_id, clean_val(e.get("name")), clean_val(e.get("phone")),
                                  clean_val(e.get("role")), status, current_task])
        try:
            self.excel_mgr.write_all_records("employees.xlsx", self.emp_headers, rows_to_write)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _assign_order_tailor(self, order_id, tailor_name):
        """Sets one order's Tailor field. Schema-aware rewrite (same pattern
        as quick_change_order_status) preserves every column, legacy +
        order-card. The Dashboard's Active Orders Ledger reads self.orders
        live, so it reflects this the moment reload_all_data() runs."""
        rows_to_write = []
        for o in self.orders:
            curr_id = clean_val(o.get("id"))
            tailor = tailor_name if curr_id == order_id else clean_val(o.get("tailor"))
            r = [clean_val(o.get(h)) for h in self.ord_headers]
            r[self.ord_headers.index("id")] = curr_id
            r[self.ord_headers.index("tailor")] = tailor
            rows_to_write.append(r)
        try:
            self.excel_mgr.write_all_records("orders.xlsx", self.ord_headers, rows_to_write)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    # ==========================================
    # RESTRICTED CUSTOMER / EMPLOYEE ACTIONS
    # ==========================================
    def _require_admin(self):
        if self.current_user_role == "Administrator":
            return True
        messagebox.showerror("Restricted", "Only an Administrator may edit or delete records.")
        return False

    def _selected_record(self, tree, records):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Select a record", "Select a row first.")
            return None
        record_id = str(tree.item(selection[0])["values"][0])
        return next((r for r in records if clean_val(r.get("id")) == record_id), None)

    def _replace_records(self, filename, headers, records):
        self.excel_mgr.write_all_records(filename, headers,
                                         [[clean_val(record.get(h)) for h in headers] for record in records])
        self.reload_all_data()
        self.update_graphics_and_stats()

    def edit_selected_customer(self):
        if not self._require_admin():
            return
        customer = self._selected_record(self.tree_customers, self.customers)
        if not customer:
            return
        dlg = tk.Toplevel(self); dlg.title("Edit Customer"); dlg.geometry("400x260"); dlg.configure(bg=self.colors["bg_card"]); dlg.grab_set()
        fields = {}
        specs = (("name", "Name"), ("phone", "Phone"), ("address", "Address"))
        for row, (key, label) in enumerate(specs):
            tk.Label(dlg, text=label + ":", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).grid(row=row, column=0, padx=18, pady=10, sticky="w")
            entry = tk.Entry(dlg, width=35, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                             insertbackground=self.colors["text_main"], relief="flat",
                             highlightthickness=1, highlightbackground=self.colors["border"])
            entry.insert(0, clean_val(customer.get(key))); entry.grid(row=row, column=1, padx=8, pady=10); fields[key] = entry
        def save():
            if not fields["name"].get().strip():
                messagebox.showerror("Validation", "Customer name is required.", parent=dlg); return
            customer.update({key: entry.get().strip() for key, entry in fields.items()})
            self._replace_records("customers.xlsx", self.cust_headers, self.customers); dlg.destroy()
        tk.Button(dlg, text="💾 Save Changes", command=save, bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"),
                 bd=0, cursor="hand2").grid(row=len(specs), column=0, columnspan=2, sticky="ew", padx=20, pady=14)

    def delete_selected_customer(self):
        if not self._require_admin():
            return
        customer = self._selected_record(self.tree_customers, self.customers)
        if not customer:
            return
        customer_id = clean_val(customer.get("id"))
        if not messagebox.askyesno("Delete Customer", f"Delete {clean_val(customer.get('name'))}? Existing orders are kept for audit history."):
            return
        self._replace_records("customers.xlsx", self.cust_headers, [c for c in self.customers if clean_val(c.get("id")) != customer_id])

    def print_selected_customer_receipt(self):
        customer = self._selected_record(self.tree_customers, self.customers)
        if not customer:
            return
        customer_id = clean_val(customer.get("id"))
        # Find the most recent order for this customer by customer_id
        order = next((o for o in reversed(self.orders) if clean_val(o.get("customer_id")) == customer_id), None)
        if not order:
            messagebox.showinfo("No Receipt", "This customer has no order to print yet.")
            return
        self.generate_order_pdf(clean_val(order.get("id")))

    def filter_customers(self, event=None):
        """Filter customer tree by search query (name, phone, id)."""
        search_query = self.ent_cust_search.get().strip().lower()
        
        # Clear tree
        self.tree_customers.delete(*self.tree_customers.get_children())
        
        # Filter and display matching customers
        if not search_query:
            # Show all customers if search is empty
            for c in self.customers:
                if c.get("id"):
                    row_values = [clean_val(c.get(h, "")) for h in self.cust_headers]
                    self.tree_customers.insert("", tk.END, values=row_values)
        else:
            # Show only matching customers
            for c in self.customers:
                if c.get("id"):
                    name = clean_val(c.get("name", "")).lower()
                    phone = clean_val(c.get("phone", "")).lower()
                    cust_id = clean_val(c.get("id", "")).lower()
                    
                    if search_query in name or search_query in phone or search_query in cust_id:
                        row_values = [clean_val(c.get(h, "")) for h in self.cust_headers]
                        self.tree_customers.insert("", tk.END, values=row_values)

    def clear_customer_search(self):
        """Clear search field and show all customers."""
        self.ent_cust_search.delete(0, tk.END)
        self.filter_customers()

    def edit_selected_employee(self):
        if not self._require_admin():
            return
        employee = self._selected_record(self.tree_employees, self.employees)
        if not employee:
            return
        t = {**TRANSLATIONS["en"], **TRANSLATIONS.get(self.current_lang, {})}
        dlg = tk.Toplevel(self); dlg.title(t["emp_edit_title"]); dlg.geometry("410x330"); dlg.configure(bg=self.colors["bg_card"]); dlg.grab_set()
        fields = {}
        specs = (("name", "emp_edit_lbl_name"), ("phone", "emp_edit_lbl_phone"), ("role", "emp_edit_lbl_role"),
                 ("status", "emp_edit_lbl_status"), ("current_task", "emp_edit_lbl_task"))
        for row, (key, label_key) in enumerate(specs):
            tk.Label(dlg, text=t[label_key] + ":", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).grid(row=row, column=0, padx=18, pady=8, sticky="w")
            entry = tk.Entry(dlg, width=34, bg=self.colors["bg_body"], fg=self.colors["text_main"],
                             insertbackground=self.colors["text_main"], relief="flat",
                             highlightthickness=1, highlightbackground=self.colors["border"])
            entry.insert(0, clean_val(employee.get(key))); entry.grid(row=row, column=1, padx=8, pady=8); fields[key] = entry
        def save():
            if not fields["name"].get().strip():
                messagebox.showerror("Validation", "Employee name is required.", parent=dlg); return
            employee.update({key: entry.get().strip() for key, entry in fields.items()})
            self._replace_records("employees.xlsx", self.emp_headers, self.employees); dlg.destroy()
        tk.Button(dlg, text=t["btn_save_changes"], command=save, bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"),
                 bd=0, cursor="hand2").grid(row=len(specs), column=0, columnspan=2, sticky="ew", padx=20, pady=14)

    def delete_selected_employee(self):
        if not self._require_admin():
            return
        employee = self._selected_record(self.tree_employees, self.employees)
        if not employee:
            return
        employee_id = clean_val(employee.get("id"))
        if not messagebox.askyesno("Delete Employee", f"Delete {clean_val(employee.get('name'))}? This cannot be undone."):
            return
        self._replace_records("employees.xlsx", self.emp_headers, [e for e in self.employees if clean_val(e.get("id")) != employee_id])

    def print_selected_employee_task(self):
        employee = self._selected_record(self.tree_employees, self.employees)
        if not employee:
            return
        if not REPORTLAB_INSTALLED:
            messagebox.showerror("Missing Library", "Install reportlab to print task slips."); return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"Task_{clean_val(employee.get('id'))}.pdf", filetypes=[("PDF Files", "*.pdf")])
        if not path:
            return
        pdf = canvas.Canvas(path, pagesize=A5); width, height = A5
        pdf.setFont("Helvetica-Bold", 18); pdf.drawString(40, height - 55, "JTQ EMPLOYEE TASK SLIP")
        pdf.setFont("Helvetica", 12)
        for index, (label, key) in enumerate((("Employee", "name"), ("Role", "role"), ("Status", "status"), ("Task", "current_task"))):
            pdf.drawString(40, height - 105 - index * 30, f"{label}: {clean_val(employee.get(key))}")
        pdf.drawString(40, height - 250, f"Printed: {datetime.now().strftime('%Y-%m-%d %H:%M')}"); pdf.save()
        messagebox.showinfo("Task Slip Saved", f"Saved to:\n{path}")

    # ==========================================
    # PDF GENERATOR LOGIC
    # ==========================================
    def generate_order_pdf(self, order_id=None):
        if not REPORTLAB_INSTALLED:
            messagebox.showerror("Missing Library", "To print PDF files, open your terminal/command prompt and run:\n\npip install reportlab")
            return

        if order_id:
            ord_id = order_id
        else:
            sel = self.tree_orders.selection()
            if not sel:
                messagebox.showwarning("Select Order", "Select an order from the active ledger first!")
                return
            ord_id = str(self.tree_orders.item(sel[0])["values"][0])

        # Get Full Order Data
        order_data = next((o for o in self.orders if clean_val(o.get("id")) == ord_id), None)
        if not order_data:
            return

        # Get Full Customer Data (orders reference customers by id)
        cid = clean_val(order_data.get("customer_id") or "")
        cust_data = next((c for c in self.customers if clean_val(c.get("id")) == cid), {})
        cust_name = clean_val(cust_data.get('name', cid))

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"Receipt_{ord_id}.pdf", title="Save Order PDF as...", filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            return

        try:
            c = canvas.Canvas(file_path, pagesize=A5)
            width, height = A5

            # Header
            c.setFont("Helvetica-Bold", 18)
            c.drawString(40, height - 50, "JHAGRA CREATION & FABRICS")
            c.setFont("Helvetica", 10)
            c.drawString(40, height - 65, "The Name Of Quality - JTQ")

            c.line(40, height - 75, width - 40, height - 75)

            # Info
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, height - 100, f"No: {ord_id}")
            c.drawString(150, height - 100, f"Name: {cust_name}")
            c.drawString(40, height - 120, f"Contact: {clean_val(cust_data.get('phone', 'N/A'))}")
            c.drawString(40, height - 140, f"Date: {datetime.now().strftime('%Y-%m-%d')}")

            # 9 Measurements (right column of the physical slip)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, height - 170, "Measurements (Inches)")
            c.setFont("Helvetica", 11)

            meas_y = height - 190
            m_list = [
                ("Length (لبادی)", cust_data.get("length")), ("Sleeve (چستین)", cust_data.get("sleeve")),
                ("Shoulder (تیرہ)", cust_data.get("shoulder")), ("Collar (کالر)", cust_data.get("collar")),
                ("Chest (چھاتاں)", cust_data.get("chest")), ("Waist (کمر)", cust_data.get("waist")),
                ("Daman (واشن)", cust_data.get("daman")), ("Shalwar Length (شلوار لیبا)", cust_data.get("shalwar_len")),
                ("Paancha (بائی پا)", cust_data.get("paancha"))
            ]

            for name, val in m_list:
                c.drawString(50, meas_y, f"{name}:")
                c.drawString(150, meas_y, str(clean_val(val)))
                c.line(145, meas_y - 2, 250, meas_y - 2)
                meas_y -= 20

            # Style selections (center/left visual elements of the physical slip)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(280, height - 170, "Selected Styles")
            c.setFont("Helvetica", 11)

            style_y = height - 190
            s_list = [
                ("Button", order_data.get("button_style")),
                ("Collar", order_data.get("collar_style")),
                ("Cuffs", order_data.get("cuff_style")),
                ("Pocket", order_data.get("pocket_style")),
                ("Daman", order_data.get("daman_style")),
                ("Stitch", order_data.get("stitching"))
            ]

            for name, val in s_list:
                c.drawString(280, style_y, f"{name}:")
                c.drawString(330, style_y, str(clean_val(val)))
                style_y -= 25

            c.save()
            messagebox.showinfo("Success", f"PDF Form generated successfully at:\n{file_path}")

        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    # ==========================================
    # LIVE STATS / TABLES
    # ==========================================
    def update_graphics_and_stats(self):
        valid_orders = [o for o in self.orders if o.get("id")]
        total = len(valid_orders)

        ready = sum(1 for o in valid_orders if "ready" in clean_val(o.get("status")).lower())
        prog = sum(1 for o in valid_orders if "progress" in clean_val(o.get("status")).lower())
        rem = total - ready - prog

        done_pct = int((ready / total) * 100) if total > 0 else 0
        prog_pct = int((prog / total) * 100) if total > 0 else 0
        rem_pct = int((rem / total) * 100) if total > 0 else 0

        self.chart_done.set_percentage(done_pct)
        self.chart_prog.set_percentage(prog_pct)
        self.chart_rem.set_percentage(rem_pct)

        self.lbl_done_pct.configure(text=f"{done_pct}%")
        self.lbl_prog_pct.configure(text=f"{prog_pct}%")
        self.lbl_rem_pct.configure(text=f"{rem_pct}%")

        self.tree_orders.delete(*self.tree_orders.get_children())
        for o in valid_orders:
            st = clean_val(o.get("status")).lower()
            tag = "status_ready" if "ready" in st else "status_prog" if "progress" in st else "status_pending"
            # Insert values in the explicit column order to keep id at index 0 and preserve ordering
            row_values = []
            for h in self.ord_headers:
                if h == 'customer_id':
                    cid = clean_val(o.get('customer_id', ''))
                    # Display customer name when possible; fall back to id/raw value
                    name = next((clean_val(c.get('name')) for c in self.customers if clean_val(c.get('id')) == cid), cid)
                    row_values.append(name)
                else:
                    row_values.append(clean_val(o.get(h, "")))
            self.tree_orders.insert("", tk.END, values=row_values, tags=(tag,))

        self.tree_customers.delete(*self.tree_customers.get_children())
        for c in self.customers:
            if c.get("id"):
                # Ensure values are in the correct column order (FIX FOR ORDER PICKING ISSUE)
                row_values = [clean_val(c.get(h, "")) for h in self.cust_headers]
                self.tree_customers.insert("", tk.END, values=row_values)
        

        self.tree_employees.delete(*self.tree_employees.get_children())
        for e in self.employees:
            if e.get("id"):
                # Ensure values are in the correct column order
                row_values = [clean_val(e.get(h, "")) for h in self.emp_headers]
                self.tree_employees.insert("", tk.END, values=row_values)

        self.refresh_finance_ui()

    def update_clock(self):
        self.lbl_clock.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self.update_clock)

    # ==========================================
    # LANGUAGE ENGINE
    # ==========================================
    def on_language_change(self, event):
        selected_label = self.cbo_lang.get()
        label_to_code = {label: code for code, label in LANGUAGE_OPTIONS}
        self.current_lang = label_to_code.get(selected_label, self.current_lang)
        self._app_state_for_current_data().save(lang=self.current_lang)
        self.apply_language_pack()

    def apply_language_pack(self):
        # Some language packs are intentionally partial; preserve English labels
        # for any key that has not been translated yet.
        t = {**TRANSLATIONS["en"], **TRANSLATIONS.get(self.current_lang, {})}
        label_to_code = {label: code for code, label in LANGUAGE_OPTIONS}
        code_to_label = {code: label for code, label in LANGUAGE_OPTIONS}
        self.cbo_lang.set(code_to_label.get(self.current_lang, code_to_label[LANGUAGE_OPTIONS[0][0]]))

        for _, (btn, lang_key) in self.nav_buttons.items():
            btn.configure(text=t[lang_key])

        self.lbl_dash_title.configure(text=t["dash_title"])
        self.lbl_dash_sub.configure(text=t["dash_sub"])
        self.lbl_done_title.configure(text=t["work_done"])
        self.lbl_prog_title.configure(text=t["in_prog"])
        self.lbl_rem_title.configure(text=t["work_rem"])
        self.lbl_ledger_head.configure(text=t["active_ledger"])

        self.lbl_cust_title.configure(text=t["cust_title"])
        self.lbl_cust_sub.configure(text=t["cust_sub"])
        self.btn_cust_modal.configure(text=t["btn_add_cust"])
        self.btn_new_card.configure(text=t["btn_new_card"])
        self.btn_cust_receipt.configure(text=t.get("cust_btn_receipt", self.btn_cust_receipt.cget("text")))
        self.btn_cust_edit.configure(text=t.get("cust_btn_edit", self.btn_cust_edit.cget("text")))
        self.btn_cust_delete.configure(text=t.get("cust_btn_delete", self.btn_cust_delete.cget("text")))
        if hasattr(self, "order_card"):
            self.order_card.set_language(self.current_lang)

        self.lbl_emp_title.configure(text=t["emp_title"])
        self.lbl_emp_sub.configure(text=t["emp_sub"])
        self.btn_task_modal.configure(text=t["btn_assign_task"])
        self.btn_emp_modal.configure(text=t["btn_add_emp"])
        self.btn_emp_print.configure(text=t["emp_btn_print"])
        self.btn_emp_edit.configure(text=t["emp_btn_edit"])
        self.btn_emp_delete.configure(text=t["emp_btn_delete"])
        for col, key in (("id", "tbl_emp_id"), ("name", "tbl_emp_name"), ("phone", "tbl_emp_phone"),
                        ("role", "tbl_emp_role"), ("status", "tbl_emp_status"), ("current_task", "tbl_emp_task")):
            self.tree_employees.heading(col, text=t[key])

        self.lbl_fin_paid_title.configure(text=t["dash_fin_paid"])
        self.lbl_fin_remaining_title.configure(text=t["dash_fin_remaining"])
        self.lbl_fin_debt_title.configure(text=t["dash_fin_debt"])

        self.lbl_fin_title.configure(text=t["fin_title"])
        self.lbl_fin_sub.configure(text=t["fin_sub"])
        self.lbl_fin_card_paid_title.configure(text=t["fin_card_paid"])
        self.lbl_fin_card_remaining_title.configure(text=t["fin_card_remaining"])
        self.lbl_fin_card_debt_title.configure(text=t["fin_card_debt"])
        self.lbl_fin_tbl_head.configure(text=t["fin_tbl_head"])
        for col, key in (("order_id", "fin_tbl_order"), ("customer_name", "fin_tbl_customer"),
                        ("garment", "fin_tbl_garment"), ("total", "fin_tbl_total"),
                        ("paid", "fin_tbl_paid"), ("remaining", "fin_tbl_remaining"),
                        ("debt", "fin_tbl_debt"), ("status", "fin_tbl_status"),
                        ("delivery_status", "fin_tbl_delivery")):
            self.tree_finance.heading(col, text=t[key])
        for key, (b, lang_key, icon) in self.fin_tab_buttons.items():
            b.configure(text=f"{icon} {t[lang_key]}")
        self.lbl_fin_add_heading.configure(text=f"➕ {t['fin_add_heading']}")
        self.lbl_fin_add_order.configure(text=t["fin_add_order"])
        self.lbl_fin_add_amount.configure(text=t["fin_add_amount"])
        self.btn_fin_pay_submit.configure(text=f"💾 {t['fin_add_submit']}")

        self.lbl_admin_title.configure(text=t["admin_title"])
        self.lbl_admin_sub.configure(text=t["admin_sub"])
        self.lbl_theme_label.configure(text=t.get("theme_label", self.lbl_theme_label.cget("text")))
        self.lbl_language_label.configure(text=t.get("language_label", self.lbl_language_label.cget("text")))
        self.lbl_admin_card_garments.configure(text=t.get("admin_card_garments", self.lbl_admin_card_garments.cget("text")))
        self.lbl_admin_card_roles.configure(text=t.get("admin_card_roles", self.lbl_admin_card_roles.cget("text")))
        self.btn_add_garment.configure(text=t.get("btn_item_add", self.btn_add_garment.cget("text")))
        self.btn_remove_garment.configure(text=t.get("btn_item_remove", self.btn_remove_garment.cget("text")))
        self.btn_add_role.configure(text=t.get("btn_item_add", self.btn_add_role.cget("text")))
        self.btn_remove_role.configure(text=t.get("btn_item_remove", self.btn_remove_role.cget("text")))

        self.tree_orders.heading("id", text=t["tbl_ord_id"])
        # customer_id column displays a friendly 'Customer' label
        self.tree_orders.heading("customer_id", text=t["tbl_cust"])
        self.tree_orders.heading("garment", text=t["tbl_garment"])
        self.tree_orders.heading("status", text=t["tbl_status"])
        self.tree_orders.heading("tailor", text=t["tbl_tailor"])


if __name__ == "__main__":
    app = AtelierERPApp()
    app.mainloop()
