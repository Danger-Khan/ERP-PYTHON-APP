import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from excel_manager import ExcelManager, clean_val

# Color Palette Tokens
BG_BODY = "#F5F5F7"
HEADER_BG = "#FFFFFF"
SIDEBAR_BG = "#FFFFFF"
CARD_BG = "#FFFFFF"
BORDER_COLOR = "#E5E5EA"

TEXT_MAIN = "#1D1D1F"
TEXT_MUTED = "#86868B"

PRIMARY = "#007AFF"
SUCCESS = "#34C759"
WARNING = "#FF9500"
DANGER = "#FF3B30"

FONT_FAMILY = "SF Pro Text" if sys.platform == "darwin" else "Segoe UI"

TRANSLATIONS = {
    "en": {
        "nav_dash": "📊 Dashboard", "nav_cust": "👤 Customers", "nav_emp": "📋 Staff & Tasks", "nav_admin": "⚙️ Diagnostics & Settings",
        "dash_title": "Shop Overview & Performance", "dash_sub": "Live execution analytics & active customer order ledger.",
        "work_done": "WORK DONE", "in_prog": "IN PROGRESS", "work_rem": "WORK REMAINING", "active_ledger": "Active Orders Ledger",
        "cust_title": "Customer Hub", "cust_sub": "Manage customer directory, tailor measurements, and place orders.",
        "btn_add_cust": "➕ Add Customer", "btn_add_order": "🛍️ Place Order",
        "emp_title": "Employee & Task Hub", "emp_sub": "Staff allocations, duty status tracking, and work assignments.",
        "btn_add_emp": "➕ Add Staff Member", "btn_assign_task": "📋 Assign Task",
        "admin_title": "Diagnostics & System Settings", "admin_sub": "System localization, garment types, employee job roles, and file checks.",
        "tbl_ord_id": "ORDER #", "tbl_cust": "CUSTOMER", "tbl_garment": "GARMENT", "tbl_status": "STATUS", "tbl_tailor": "ASSIGNED TAILOR",
    },
    "ur": {
        "nav_dash": "📊 ڈیش بورڈ", "nav_cust": "👤 گاہک (کسٹمرز)", "nav_emp": "📋 عملہ اور کام", "nav_admin": "⚙️ ترتیبات (سیٹنگز)",
        "dash_title": "دوکان کی کارکردگی اور خلاصہ", "dash_sub": "لائیو آرڈرز اور دکان کا ریکارڈ",
        "work_done": "مکمل شدہ کام", "in_prog": "جاری کام", "work_rem": "بقایا کام", "active_ledger": "فعال آرڈرز کی فہرست",
        "cust_title": "کسٹمر سینٹر", "cust_sub": "گاہکوں کا اندراج، ناپ اور آرڈر تیار کریں۔",
        "btn_add_cust": "➕ نیا گاہک شامل کریں", "btn_add_order": "🛍️ نیا آرڈر دیں",
        "emp_title": "عملہ اور ٹاسک مینیجر", "emp_sub": "کاریگروں کی حاضری اور کام کی تقسیم۔",
        "btn_add_emp": "➕ نیا کاریگر شامل کریں", "btn_assign_task": "📋 کام سونپیں",
        "admin_title": "سسٹم کی ترتیبات", "admin_sub": "زبان، کپڑوں کی اقسام، اور ملازمت کے عہدے۔",
        "tbl_ord_id": "آرڈر نمبر", "tbl_cust": "گاہک", "tbl_garment": "کپڑے کی قسم", "tbl_status": "حالت (سٹیٹس)", "tbl_tailor": "نامزد کاریگر",
    }
}

class CircularDonutChart(tk.Canvas):
    def __init__(self, parent, size=75, ring_color=PRIMARY, bg_color="#E5E5EA", stroke_width=8, **kwargs):
        super().__init__(parent, width=size, height=size, bg=CARD_BG, highlightthickness=0, **kwargs)
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
        if self.percentage > 0:
            extent = -(self.percentage / 100.0) * 360
            self.create_arc(x0, y0, x1, y1, start=90, extent=extent, style=tk.ARC, outline=self.ring_color, width=self.stroke_width)

    def set_percentage(self, pct):
        self.percentage = max(0, min(100, pct))
        self.draw_chart()


class AtelierERPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jhagra Textile & Clothing — Atelier Ledger")
        self.geometry("1280x800")
        self.configure(bg=BG_BODY)
        self.current_lang = "en"

        self.excel_mgr = ExcelManager()

        self.cust_headers = ["id", "name", "phone", "length", "chest", "waist", "shoulder", "collar", "arm_length"]
        self.emp_headers = ["id", "name", "phone", "role", "status", "current_task"]
        self.ord_headers = ["id", "customer", "garment", "status", "tailor"]

        self.default_garments = ["Shalwar Kameez", "Waistcoat", "2-Piece Suit", "Kurta", "Sherwani"]
        self.default_roles = ["Master Cutter", "Stitching Specialist", "Press & Finishing"]

        self.reload_all_data()

        self.apply_theme_styles()
        self.create_header()
        self.create_layout()
        self.show_section("dashboard")
        self.update_graphics_and_stats()
        self.update_clock()
        self.monitor_excel_files()

    def reload_all_data(self):
        self.customers = self.excel_mgr.read_records("customers.xlsx", self.cust_headers)
        self.employees = self.excel_mgr.read_records("employees.xlsx", self.emp_headers)
        self.orders = self.excel_mgr.read_records("orders.xlsx", self.ord_headers)
        self.garment_types = self.excel_mgr.load_settings_list("garment_type", self.default_garments)
        self.employee_roles = self.excel_mgr.load_settings_list("employee_role", self.default_roles)

    def monitor_excel_files(self):
        for fname in ["customers.xlsx", "employees.xlsx", "orders.xlsx", "settings.xlsx"]:
            if self.excel_mgr.is_file_modified(fname):
                self.reload_all_data()
                self.update_graphics_and_stats()
                self.refresh_settings_ui()
                break
        self.after(2000, self.monitor_excel_files)

    def apply_theme_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", background="#FFFFFF", foreground=TEXT_MAIN, fieldbackground="#FFFFFF", rowheight=34, font=(FONT_FAMILY, 10), borderwidth=0)
        self.style.configure("Treeview.Heading", background="#F5F5F7", foreground=TEXT_MUTED, font=(FONT_FAMILY, 9, "bold"), borderwidth=0)
        self.style.map("Treeview", background=[('selected', '#EBF5FF')], foreground=[('selected', PRIMARY)])

    def create_header(self):
        header = tk.Frame(self, bg=HEADER_BG, height=56, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)

        logo_box = tk.Frame(header, bg=HEADER_BG)
        logo_box.pack(side=tk.LEFT, padx=20)

        badge = tk.Label(logo_box, text="JTC", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), padx=8, pady=2)
        badge.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_shop_name = tk.Label(logo_box, text="Jhagra Textile & Clothing", bg=HEADER_BG, fg=TEXT_MAIN, font=(FONT_FAMILY, 11, "bold"))
        self.lbl_shop_name.pack(side=tk.LEFT)

        self.lbl_clock = tk.Label(header, text="", bg=HEADER_BG, fg=TEXT_MUTED, font=(FONT_FAMILY, 10))
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

    def create_layout(self):
        body_container = tk.Frame(self, bg=BG_BODY)
        body_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        sidebar = tk.Frame(body_container, bg=SIDEBAR_BG, width=220, highlightbackground=BORDER_COLOR, highlightthickness=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
        sidebar.pack_propagate(False)

        self.nav_buttons = {}
        nav_keys = [("dashboard", "nav_dash"), ("customer", "nav_cust"), ("employee", "nav_emp"), ("admin", "nav_admin")]

        for key, lang_key in nav_keys:
            btn = tk.Button(sidebar, text=TRANSLATIONS[self.current_lang][lang_key], anchor="w", font=(FONT_FAMILY, 10, "bold"),
                            bg=SIDEBAR_BG, fg=TEXT_MUTED, activebackground="#EBF5FF", activeforeground=PRIMARY,
                            bd=0, padx=16, pady=12, cursor="hand2", command=lambda k=key: self.show_section(k))
            btn.pack(fill=tk.X, pady=2, padx=6)
            self.nav_buttons[key] = (btn, lang_key)

        self.main_content = tk.Frame(body_container, bg=BG_BODY)
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.sections = {}
        self.build_dashboard_section()
        self.build_customer_section()
        self.build_employee_section()
        self.build_admin_section()

    def show_section(self, section_key):
        for key, frame in self.sections.items():
            frame.pack_forget()
            btn, _ = self.nav_buttons[key]
            btn.configure(bg=SIDEBAR_BG, fg=TEXT_MUTED)

        self.sections[section_key].pack(fill=tk.BOTH, expand=True)
        active_btn, _ = self.nav_buttons[section_key]
        active_btn.configure(bg=PRIMARY, fg="white")

    # ------------------------------------------
    # DASHBOARD SECTION
    # ------------------------------------------
    def build_dashboard_section(self):
        sec = tk.Frame(self.main_content, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.sections["dashboard"] = sec

        hdr = tk.Frame(sec, bg=CARD_BG)
        hdr.pack(fill=tk.X, padx=24, pady=(20, 10))
        self.lbl_dash_title = tk.Label(hdr, text=TRANSLATIONS["en"]["dash_title"], font=(FONT_FAMILY, 16, "bold"), bg=CARD_BG, fg=TEXT_MAIN)
        self.lbl_dash_title.pack(anchor="w")
        self.lbl_dash_sub = tk.Label(hdr, text=TRANSLATIONS["en"]["dash_sub"], font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_MUTED)
        self.lbl_dash_sub.pack(anchor="w")

        graphics_frame = tk.Frame(sec, bg=CARD_BG)
        graphics_frame.pack(fill=tk.X, padx=24, pady=10)

        card1 = tk.Frame(graphics_frame, bg="#FAFAFC", highlightbackground=BORDER_COLOR, highlightthickness=1, padx=16, pady=12)
        card1.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
        info1 = tk.Frame(card1, bg="#FAFAFC")
        info1.pack(side=tk.LEFT)
        self.lbl_done_title = tk.Label(info1, text=TRANSLATIONS["en"]["work_done"], font=(FONT_FAMILY, 8, "bold"), bg="#FAFAFC", fg=TEXT_MUTED)
        self.lbl_done_title.pack(anchor="w")
        self.lbl_done_pct = tk.Label(info1, text="0%", font=(FONT_FAMILY, 20, "bold"), bg="#FAFAFC", fg=TEXT_MAIN)
        self.lbl_done_pct.pack(anchor="w")
        self.lbl_done_sub = tk.Label(info1, text="0 orders ready", font=(FONT_FAMILY, 9), bg="#FAFAFC", fg=TEXT_MUTED)
        self.lbl_done_sub.pack(anchor="w")
        self.chart_done = CircularDonutChart(card1, size=70, ring_color=SUCCESS)
        self.chart_done.pack(side=tk.RIGHT)

        card2 = tk.Frame(graphics_frame, bg="#FAFAFC", highlightbackground=BORDER_COLOR, highlightthickness=1, padx=16, pady=12)
        card2.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        info2 = tk.Frame(card2, bg="#FAFAFC")
        info2.pack(side=tk.LEFT)
        self.lbl_prog_title = tk.Label(info2, text=TRANSLATIONS["en"]["in_prog"], font=(FONT_FAMILY, 8, "bold"), bg="#FAFAFC", fg=TEXT_MUTED)
        self.lbl_prog_title.pack(anchor="w")
        self.lbl_prog_pct = tk.Label(info2, text="0%", font=(FONT_FAMILY, 20, "bold"), bg="#FAFAFC", fg=TEXT_MAIN)
        self.lbl_prog_pct.pack(anchor="w")
        self.lbl_prog_sub = tk.Label(info2, text="0 active on bench", font=(FONT_FAMILY, 9), bg="#FAFAFC", fg=TEXT_MUTED)
        self.lbl_prog_sub.pack(anchor="w")
        self.chart_prog = CircularDonutChart(card2, size=70, ring_color=WARNING)
        self.chart_prog.pack(side=tk.RIGHT)

        card3 = tk.Frame(graphics_frame, bg="#FAFAFC", highlightbackground=BORDER_COLOR, highlightthickness=1, padx=16, pady=12)
        card3.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(8, 0))
        info3 = tk.Frame(card3, bg="#FAFAFC")
        info3.pack(side=tk.LEFT)
        self.lbl_rem_title = tk.Label(info3, text=TRANSLATIONS["en"]["work_rem"], font=(FONT_FAMILY, 8, "bold"), bg="#FAFAFC", fg=TEXT_MUTED)
        self.lbl_rem_title.pack(anchor="w")
        self.lbl_rem_pct = tk.Label(info3, text="0%", font=(FONT_FAMILY, 20, "bold"), bg="#FAFAFC", fg=TEXT_MAIN)
        self.lbl_rem_pct.pack(anchor="w")
        self.lbl_rem_sub = tk.Label(info3, text="0 orders pending", font=(FONT_FAMILY, 9), bg="#FAFAFC", fg=TEXT_MUTED)
        self.lbl_rem_sub.pack(anchor="w")
        self.chart_rem = CircularDonutChart(card3, size=70, ring_color=DANGER)
        self.chart_rem.pack(side=tk.RIGHT)

        self.lbl_ledger_head = tk.Label(sec, text=TRANSLATIONS["en"]["active_ledger"], font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_MAIN)
        self.lbl_ledger_head.pack(anchor="w", padx=24, pady=(16, 8))

        table_frame = tk.Frame(sec, bg=CARD_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        cols = ("id", "customer", "garment", "status", "tailor")
        self.tree_orders = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree_orders.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------
    # CUSTOMER SECTION
    # ------------------------------------------
    def build_customer_section(self):
        sec = tk.Frame(self.main_content, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.sections["customer"] = sec

        hdr = tk.Frame(sec, bg=CARD_BG)
        hdr.pack(fill=tk.X, padx=24, pady=(20, 10))

        titles = tk.Frame(hdr, bg=CARD_BG)
        titles.pack(side=tk.LEFT)
        self.lbl_cust_title = tk.Label(titles, text=TRANSLATIONS["en"]["cust_title"], font=(FONT_FAMILY, 16, "bold"), bg=CARD_BG, fg=TEXT_MAIN)
        self.lbl_cust_title.pack(anchor="w")
        self.lbl_cust_sub = tk.Label(titles, text=TRANSLATIONS["en"]["cust_sub"], font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_MUTED)
        self.lbl_cust_sub.pack(anchor="w")

        actions = tk.Frame(hdr, bg=CARD_BG)
        actions.pack(side=tk.RIGHT)

        self.btn_order_modal = tk.Button(actions, text=TRANSLATIONS["en"]["btn_add_order"], bg=SUCCESS, fg="white", font=(FONT_FAMILY, 9, "bold"),
                                         bd=0, padx=12, pady=6, cursor="hand2", command=self.open_add_order_modal)
        self.btn_order_modal.pack(side=tk.RIGHT, padx=4)

        self.btn_cust_modal = tk.Button(actions, text=TRANSLATIONS["en"]["btn_add_cust"], bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"),
                                        bd=0, padx=12, pady=6, cursor="hand2", command=self.open_add_customer_modal)
        self.btn_cust_modal.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(sec, bg=CARD_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        cols = ("id", "name", "phone", "length", "chest", "waist", "shoulder", "collar", "arm_length")
        self.tree_customers = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree_customers.heading(c, text=c.upper().replace('_', ' '))
            self.tree_customers.column(c, width=110)
        self.tree_customers.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------
    # EMPLOYEE SECTION
    # ------------------------------------------
    def build_employee_section(self):
        sec = tk.Frame(self.main_content, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.sections["employee"] = sec

        hdr = tk.Frame(sec, bg=CARD_BG)
        hdr.pack(fill=tk.X, padx=24, pady=(20, 10))

        titles = tk.Frame(hdr, bg=CARD_BG)
        titles.pack(side=tk.LEFT)
        self.lbl_emp_title = tk.Label(titles, text=TRANSLATIONS["en"]["emp_title"], font=(FONT_FAMILY, 16, "bold"), bg=CARD_BG, fg=TEXT_MAIN)
        self.lbl_emp_title.pack(anchor="w")
        self.lbl_emp_sub = tk.Label(titles, text=TRANSLATIONS["en"]["emp_sub"], font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_MUTED)
        self.lbl_emp_sub.pack(anchor="w")

        actions = tk.Frame(hdr, bg=CARD_BG)
        actions.pack(side=tk.RIGHT)

        self.btn_task_modal = tk.Button(actions, text=TRANSLATIONS["en"]["btn_assign_task"], bg=WARNING, fg="white", font=(FONT_FAMILY, 9, "bold"),
                                        bd=0, padx=12, pady=6, cursor="hand2", command=self.open_assign_task_modal)
        self.btn_task_modal.pack(side=tk.RIGHT, padx=4)

        self.btn_emp_modal = tk.Button(actions, text=TRANSLATIONS["en"]["btn_add_emp"], bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"),
                                       bd=0, padx=12, pady=6, cursor="hand2", command=self.open_add_employee_modal)
        self.btn_emp_modal.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(sec, bg=CARD_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        cols = ("id", "name", "phone", "role", "status", "current_task")
        self.tree_employees = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree_employees.heading(c, text=c.upper().replace('_', ' '))
            self.tree_employees.column(c, width=120)
        self.tree_employees.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------
    # DIAGNOSTICS & SETTINGS SECTION
    # ------------------------------------------
    def build_admin_section(self):
        sec = tk.Frame(self.main_content, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.sections["admin"] = sec

        hdr = tk.Frame(sec, bg=CARD_BG)
        hdr.pack(fill=tk.X, padx=24, pady=(20, 10))
        self.lbl_admin_title = tk.Label(hdr, text=TRANSLATIONS["en"]["admin_title"], font=(FONT_FAMILY, 16, "bold"), bg=CARD_BG, fg=TEXT_MAIN)
        self.lbl_admin_title.pack(anchor="w")
        self.lbl_admin_sub = tk.Label(hdr, text=TRANSLATIONS["en"]["admin_sub"], font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_MUTED)
        self.lbl_admin_sub.pack(anchor="w")

        cards_frame = tk.Frame(sec, bg=CARD_BG)
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=10)

        # Card 1: General & Language Settings
        c1 = tk.Frame(cards_frame, bg="#FAFAFC", highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=14)
        c1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        
        tk.Label(c1, text="🛠️ System & Localization", font=(FONT_FAMILY, 10, "bold"), bg="#FAFAFC", fg=TEXT_MAIN).pack(anchor="w", pady=(0, 8))
        
        tk.Label(c1, text="Atelier / Shop Name", font=(FONT_FAMILY, 8, "bold"), bg="#FAFAFC", fg=TEXT_MUTED).pack(anchor="w")
        self.ent_shop_name = tk.Entry(c1, font=(FONT_FAMILY, 9))
        self.ent_shop_name.insert(0, "Jhagra Textile & Clothing")
        self.ent_shop_name.pack(fill=tk.X, pady=(2, 8))

        tk.Label(c1, text="System Language (زبان)", font=(FONT_FAMILY, 8, "bold"), bg="#FAFAFC", fg=TEXT_MUTED).pack(anchor="w")
        self.cbo_lang = ttk.Combobox(c1, values=["English (en)", "Urdu (اردو)"], state="readonly", font=(FONT_FAMILY, 9))
        self.cbo_lang.current(0)
        self.cbo_lang.pack(fill=tk.X, pady=(2, 12))
        self.cbo_lang.bind("<<ComboboxSelected>>", self.on_language_change)

        # Card 2: Custom Types & Roles Manager
        c2 = tk.Frame(cards_frame, bg="#FAFAFC", highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=14)
        c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        tk.Label(c2, text="🏷️ Custom Order & Staff Types", font=(FONT_FAMILY, 10, "bold"), bg="#FAFAFC", fg=TEXT_MAIN).pack(anchor="w", pady=(0, 8))

        g_box = tk.LabelFrame(c2, text=" Stitching / Garment Types ", bg="#FAFAFC", font=(FONT_FAMILY, 8, "bold"), fg=PRIMARY)
        g_box.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.lst_garments = tk.Listbox(g_box, height=3, font=(FONT_FAMILY, 8))
        self.lst_garments.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        g_btns = tk.Frame(g_box, bg="#FAFAFC")
        g_btns.pack(side=tk.RIGHT, fill=tk.Y, padx=4, pady=4)
        self.ent_new_garment = tk.Entry(g_btns, width=12, font=(FONT_FAMILY, 8))
        self.ent_new_garment.pack(pady=1)
        tk.Button(g_btns, text="➕ Add", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 7, "bold"), bd=0, padx=4, command=self.add_garment_type).pack(fill=tk.X, pady=1)
        tk.Button(g_btns, text="🗑️ Del", bg=DANGER, fg="white", font=(FONT_FAMILY, 7, "bold"), bd=0, padx=4, command=self.remove_garment_type).pack(fill=tk.X, pady=1)

        r_box = tk.LabelFrame(c2, text=" Employee Job Roles ", bg="#FAFAFC", font=(FONT_FAMILY, 8, "bold"), fg=PRIMARY)
        r_box.pack(fill=tk.BOTH, expand=True)
        self.lst_roles = tk.Listbox(r_box, height=3, font=(FONT_FAMILY, 8))
        self.lst_roles.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        r_btns = tk.Frame(r_box, bg="#FAFAFC")
        r_btns.pack(side=tk.RIGHT, fill=tk.Y, padx=4, pady=4)
        self.ent_new_role = tk.Entry(r_btns, width=12, font=(FONT_FAMILY, 8))
        self.ent_new_role.pack(pady=1)
        tk.Button(r_btns, text="➕ Add", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 7, "bold"), bd=0, padx=4, command=self.add_employee_role).pack(fill=tk.X, pady=1)
        tk.Button(r_btns, text="🗑️ Del", bg=DANGER, fg="white", font=(FONT_FAMILY, 7, "bold"), bd=0, padx=4, command=self.remove_employee_role).pack(fill=tk.X, pady=1)

        # Card 3: EXCEL DATA READER & MANUAL SYNC
        c3 = tk.Frame(cards_frame, bg="#FAFAFC", highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=14)
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(c3, text="📊 Excel Reader & Inspector", font=(FONT_FAMILY, 10, "bold"), bg="#FAFAFC", fg=TEXT_MAIN).pack(anchor="w", pady=(0, 8))
        
        tk.Label(c3, text="Select File to Read Raw Data:", font=(FONT_FAMILY, 8, "bold"), bg="#FAFAFC", fg=TEXT_MUTED).pack(anchor="w")
        self.cbo_excel_file = ttk.Combobox(c3, values=["customers.xlsx", "employees.xlsx", "orders.xlsx", "settings.xlsx"], state="readonly", font=(FONT_FAMILY, 9))
        self.cbo_excel_file.current(0)
        self.cbo_excel_file.pack(fill=tk.X, pady=(2, 10))

        tk.Button(c3, text="📖 Read & Inspect Selected File", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, pady=6, cursor="hand2", command=self.open_excel_inspector_modal).pack(fill=tk.X, pady=(0, 8))
        tk.Button(c3, text="🔄 Force Reload All Excel Data", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, pady=6, cursor="hand2", command=self.manual_reload_excel_data).pack(fill=tk.X)

        self.refresh_settings_ui()

    def open_excel_inspector_modal(self):
        filename = self.cbo_excel_file.get()
        headers, rows = self.excel_mgr.read_raw_matrix(filename)

        dlg = tk.Toplevel(self)
        dlg.title(f"Excel Inspector — {filename}")
        dlg.geometry("700x450")
        dlg.configure(bg=CARD_BG)
        dlg.grab_set()

        hdr_frame = tk.Frame(dlg, bg=CARD_BG, padx=16, pady=12)
        hdr_frame.pack(fill=tk.X)
        tk.Label(hdr_frame, text=f"Raw Excel Contents: {filename}", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_MAIN).pack(anchor="w")
        tk.Label(hdr_frame, text=f"Total Records Found: {len(rows)} | Section Header Columns: {len(headers)}", font=(FONT_FAMILY, 9), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")

        tbl_frame = tk.Frame(dlg, bg=CARD_BG, padx=16, pady=(0, 16))
        tbl_frame.pack(fill=tk.BOTH, expand=True)

        if headers:
            tree = ttk.Treeview(tbl_frame, columns=headers, show="headings")
            for h in headers:
                tree.heading(h, text=h.upper())
                tree.column(h, width=100)
            
            for r in rows:
                tree.insert("", tk.END, values=r)
            
            vsb = ttk.Scrollbar(tbl_frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(tbl_frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)
            tree.pack(fill=tk.BOTH, expand=True)
        else:
            tk.Label(tbl_frame, text="This Excel file is empty or missing headers.", font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_MUTED).pack(pady=40)

    def manual_reload_excel_data(self):
        try:
            self.reload_all_data()
            self.update_graphics_and_stats()
            self.refresh_settings_ui()
            messagebox.showinfo("Excel Reader", "All Excel files re-read & synchronized successfully!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_settings_ui(self):
        self.lst_garments.delete(0, tk.END)
        for g in self.garment_types:
            self.lst_garments.insert(tk.END, g)

        self.lst_roles.delete(0, tk.END)
        for r in self.employee_roles:
            self.lst_roles.insert(tk.END, r)

    def add_garment_type(self):
        val = self.ent_new_garment.get().strip()
        if val and val not in self.garment_types:
            self.garment_types.append(val)
            try:
                self.excel_mgr.save_settings_list("garment_type", self.garment_types)
                self.ent_new_garment.delete(0, tk.END)
                self.refresh_settings_ui()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def remove_garment_type(self):
        sel = self.lst_garments.curselection()
        if sel:
            idx = sel[0]
            val = self.lst_garments.get(idx)
            self.garment_types.remove(val)
            try:
                self.excel_mgr.save_settings_list("garment_type", self.garment_types)
                self.refresh_settings_ui()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def add_employee_role(self):
        val = self.ent_new_role.get().strip()
        if val and val not in self.employee_roles:
            self.employee_roles.append(val)
            try:
                self.excel_mgr.save_settings_list("employee_role", self.employee_roles)
                self.ent_new_role.delete(0, tk.END)
                self.refresh_settings_ui()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def remove_employee_role(self):
        sel = self.lst_roles.curselection()
        if sel:
            idx = sel[0]
            val = self.lst_roles.get(idx)
            self.employee_roles.remove(val)
            try:
                self.excel_mgr.save_settings_list("employee_role", self.employee_roles)
                self.refresh_settings_ui()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ------------------------------------------
    # MODAL DIALOG POPUPS (WITH ERROR CATCHING)
    # ------------------------------------------
    def open_add_customer_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add New Customer Record")
        dlg.geometry("420x540")
        dlg.configure(bg=CARD_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Register Customer & Measurements", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_MAIN).pack(pady=12)

        fields = [("Full Name", "name"), ("Phone Number", "phone"), ("Length (Inches)", "length"),
                  ("Chest", "chest"), ("Waist", "waist"), ("Shoulder", "shoulder"), ("Collar", "collar"), ("Arm Length", "arm_length")]
        entries = {}

        for lbl, key in fields:
            f = tk.Frame(dlg, bg=CARD_BG)
            f.pack(fill=tk.X, padx=20, pady=3)
            tk.Label(f, text=lbl, font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
            e = tk.Entry(f, font=(FONT_FAMILY, 10))
            e.pack(fill=tk.X)
            entries[key] = e

        def save():
            name = entries["name"].get().strip()
            phone = entries["phone"].get().strip()
            if not name or not phone:
                messagebox.showerror("Error", "Name and Phone are required!", parent=dlg)
                return
            new_id = f"C-{len(self.customers) + 101}"
            row = [new_id, name, phone] + [entries[k].get().strip() or "0" for k in ["length", "chest", "waist", "shoulder", "collar", "arm_length"]]
            
            try:
                self.excel_mgr.append_record("customers.xlsx", self.cust_headers, row)
                self.reload_all_data()
                self.update_graphics_and_stats()
                dlg.destroy()
                messagebox.showinfo("Success", f"Customer '{name}' saved to Excel!")
            except Exception as e:
                messagebox.showerror("Save Failed", str(e), parent=dlg)

        tk.Button(dlg, text="Save Customer", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=16)

    def open_add_order_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Create New Garment Order")
        dlg.geometry("420x400")
        dlg.configure(bg=CARD_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Place Order", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_MAIN).pack(pady=12)

        selected_cust_str = ""
        sel = self.tree_customers.selection()
        if sel:
            item = self.tree_customers.item(sel[0])
            vals = item["values"]
            if vals and len(vals) > 1:
                selected_cust_str = f"{vals[0]} - {vals[1]}"

        tk.Label(dlg, text="Select Customer", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        cust_options = [f"{c['id']} - {c['name']}" for c in self.customers if c.get("name")]
        cbo_cust = ttk.Combobox(dlg, values=cust_options, state="readonly")
        if selected_cust_str in cust_options:
            cbo_cust.set(selected_cust_str)
        elif cust_options:
            cbo_cust.current(0)
        cbo_cust.pack(fill=tk.X, padx=20, pady=(2, 10))

        tk.Label(dlg, text="Garment Type (Stitching)", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        cbo_garm = ttk.Combobox(dlg, values=self.garment_types, state="readonly")
        if self.garment_types:
            cbo_garm.current(0)
        cbo_garm.pack(fill=tk.X, padx=20, pady=(2, 10))

        tk.Label(dlg, text="Assign Tailor / Staff", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        emp_options = [f"{e['name']} ({e.get('role', '')})" for e in self.employees if e.get("name")]
        cbo_tailor = ttk.Combobox(dlg, values=emp_options, state="readonly")
        if emp_options:
            cbo_tailor.current(0)
        cbo_tailor.pack(fill=tk.X, padx=20, pady=(2, 10))

        def save():
            cust_val = cbo_cust.get()
            tailor_val = cbo_tailor.get()
            garm_val = cbo_garm.get()
            if not cust_val or not tailor_val or not garm_val:
                messagebox.showerror("Error", "Please fill in all selection fields!", parent=dlg)
                return

            cust_name_only = cust_val.split(" - ")[-1]
            tailor_name_only = tailor_val.split(" (")[0]
            ord_id = f"ORD-{len(self.orders) + 101}"

            row = [ord_id, cust_name_only, garm_val, "In Progress", tailor_name_only]
            try:
                self.excel_mgr.append_record("orders.xlsx", self.ord_headers, row)
                self.reload_all_data()
                self.update_graphics_and_stats()
                dlg.destroy()
                messagebox.showinfo("Success", f"Order {ord_id} created for {cust_name_only}!")
            except Exception as e:
                messagebox.showerror("Save Failed", str(e), parent=dlg)

        tk.Button(dlg, text="Confirm & Place Order", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=16)

    def open_add_employee_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add Staff Member")
        dlg.geometry("380x360")
        dlg.configure(bg=CARD_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Register Employee", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_MAIN).pack(pady=12)

        tk.Label(dlg, text="Full Name", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        e_name = tk.Entry(dlg, font=(FONT_FAMILY, 10))
        e_name.pack(fill=tk.X, padx=20, pady=(2, 8))

        tk.Label(dlg, text="Phone Number", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        e_phone = tk.Entry(dlg, font=(FONT_FAMILY, 10))
        e_phone.pack(fill=tk.X, padx=20, pady=(2, 8))

        tk.Label(dlg, text="Job Role / Specialization", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        cbo_role = ttk.Combobox(dlg, values=self.employee_roles, state="readonly")
        if self.employee_roles:
            cbo_role.current(0)
        cbo_role.pack(fill=tk.X, padx=20, pady=(2, 8))

        def save():
            name = e_name.get().strip()
            phone = e_phone.get().strip()
            role = cbo_role.get()
            if not name:
                messagebox.showerror("Error", "Staff Name is required!", parent=dlg)
                return
            emp_id = f"E-{len(self.employees) + 1:02d}"
            row = [emp_id, name, phone, role, "On Duty", "None"]
            
            try:
                self.excel_mgr.append_record("employees.xlsx", self.emp_headers, row)
                self.reload_all_data()
                self.update_graphics_and_stats()
                dlg.destroy()
                messagebox.showinfo("Success", f"Employee '{name}' registered successfully!")
            except Exception as e:
                messagebox.showerror("Save Failed", str(e), parent=dlg)

        tk.Button(dlg, text="Save Employee", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=16)

    def open_assign_task_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Assign Task")
        dlg.geometry("400x320")
        dlg.configure(bg=CARD_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Assign Work Task", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_MAIN).pack(pady=12)

        tk.Label(dlg, text="Select Staff Member", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        emp_names = [e["name"] for e in self.employees if e.get("name")]
        cbo_emp = ttk.Combobox(dlg, values=emp_names, state="readonly")
        if emp_names:
            cbo_emp.current(0)
        cbo_emp.pack(fill=tk.X, padx=20, pady=(2, 10))

        tk.Label(dlg, text="Task Description", font=(FONT_FAMILY, 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", padx=20)
        e_task = tk.Entry(dlg, font=(FONT_FAMILY, 10))
        e_task.pack(fill=tk.X, padx=20, pady=(2, 10))

        def save():
            emp_name = cbo_emp.get()
            task_desc = e_task.get().strip()
            if not emp_name or not task_desc:
                messagebox.showerror("Error", "Employee and Task details required!", parent=dlg)
                return

            rows_to_write = []
            for e in self.employees:
                task = task_desc if e["name"] == emp_name else e.get("current_task", "")
                rows_to_write.append([e.get("id", ""), e.get("name", ""), e.get("phone", ""), e.get("role", ""), e.get("status", ""), task])

            try:
                self.excel_mgr.write_all_records("employees.xlsx", self.emp_headers, rows_to_write)
                self.reload_all_data()
                self.update_graphics_and_stats()
                dlg.destroy()
                messagebox.showinfo("Success", f"Task assigned to {emp_name}!")
            except Exception as e:
                messagebox.showerror("Save Failed", str(e), parent=dlg)

        tk.Button(dlg, text="Assign Task", bg=WARNING, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=16)

    # ------------------------------------------
    # LANGUAGE ENGINE & DYNAMIC REFRESH
    # ------------------------------------------
    def on_language_change(self, event):
        sel = self.cbo_lang.get()
        self.current_lang = "ur" if "Urdu" in sel else "en"
        self.apply_language_pack()

    def apply_language_pack(self):
        t = TRANSLATIONS[self.current_lang]
        for key, (btn, lang_key) in self.nav_buttons.items():
            btn.configure(text=t[lang_key])

        self.lbl_dash_title.configure(text=t["dash_title"])
        self.lbl_dash_sub.configure(text=t["dash_sub"])
        self.lbl_done_title.configure(text=t["work_done"])
        self.lbl_prog_title.configure(text=t["in_prog"])
        self.lbl_rem_title.configure(text=t["work_rem"])
        self.lbl_ledger_head.configure(text=t["active_ledger"])

        self.lbl_cust_title.configure(text=t["cust_title"])
        self.lbl_cust_sub.configure(text=t["cust_sub"])
        self.btn_order_modal.configure(text=t["btn_add_order"])
        self.btn_cust_modal.configure(text=t["btn_add_cust"])

        self.lbl_emp_title.configure(text=t["emp_title"])
        self.lbl_emp_sub.configure(text=t["emp_sub"])
        self.btn_task_modal.configure(text=t["btn_assign_task"])
        self.btn_emp_modal.configure(text=t["btn_add_emp"])

        self.lbl_admin_title.configure(text=t["admin_title"])
        self.lbl_admin_sub.configure(text=t["admin_sub"])

        self.tree_orders.heading("id", text=t["tbl_ord_id"])
        self.tree_orders.heading("customer", text=t["tbl_cust"])
        self.tree_orders.heading("garment", text=t["tbl_garment"])
        self.tree_orders.heading("status", text=t["tbl_status"])
        self.tree_orders.heading("tailor", text=t["tbl_tailor"])

    def update_graphics_and_stats(self):
        total = len(self.orders)
        ready = len([o for o in self.orders if clean_val(o.get("status")).lower() == "ready"])
        prog = len([o for o in self.orders if clean_val(o.get("status")).lower() == "in progress"])
        rem = total - ready

        done_pct = int((ready / total) * 100) if total > 0 else 0
        prog_pct = int((prog / total) * 100) if total > 0 else 0
        rem_pct = int((rem / total) * 100) if total > 0 else 0

        self.chart_done.set_percentage(done_pct)
        self.chart_prog.set_percentage(prog_pct)
        self.chart_rem.set_percentage(rem_pct)

        self.lbl_done_pct.configure(text=f"{done_pct}%")
        self.lbl_done_sub.configure(text=f"{ready} of {total} ready")
        self.lbl_prog_pct.configure(text=f"{prog_pct}%")
        self.lbl_prog_sub.configure(text=f"{prog} active")
        self.lbl_rem_pct.configure(text=f"{rem_pct}%")
        self.lbl_rem_sub.configure(text=f"{rem} pending")

        self.tree_orders.delete(*self.tree_orders.get_children())
        for o in self.orders:
            if o.get("id"):
                self.tree_orders.insert("", tk.END, values=(
                    clean_val(o.get("id")), clean_val(o.get("customer")), clean_val(o.get("garment")),
                    clean_val(o.get("status")), clean_val(o.get("tailor"))
                ))

        self.tree_customers.delete(*self.tree_customers.get_children())
        for c in self.customers:
            if c.get("id"):
                self.tree_customers.insert("", tk.END, values=(
                    clean_val(c.get("id")), clean_val(c.get("name")), clean_val(c.get("phone")),
                    clean_val(c.get("length")), clean_val(c.get("chest")), clean_val(c.get("waist")),
                    clean_val(c.get("shoulder")), clean_val(c.get("collar")), clean_val(c.get("arm_length"))
                ))

        self.tree_employees.delete(*self.tree_employees.get_children())
        for e in self.employees:
            if e.get("id"):
                self.tree_employees.insert("", tk.END, values=(
                    clean_val(e.get("id")), clean_val(e.get("name")), clean_val(e.get("phone")),
                    clean_val(e.get("role")), clean_val(e.get("status")), clean_val(e.get("current_task"))
                ))

    def update_clock(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.configure(text=now_str)
        self.after(1000, self.update_clock)


if __name__ == "__main__":
    app = AtelierERPApp()
    app.mainloop()